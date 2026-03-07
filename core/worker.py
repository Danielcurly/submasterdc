#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Background Task Worker
Responsible for processing video subtitle extraction and translation in the task queue
"""

import os
import time
import threading
import shutil
from pathlib import Path
from typing import Optional, List

from core.models import TaskStatus, TranslationTask
from core.config import ConfigManager, AppConfig
from database.connection import wait_for_database, get_db_connection
from database.task_dao import TaskDAO
from core.logger import app_logger, LOG_FILE
from database.media_dao import MediaDAO
from services.media_scanner import rescan_video_subtitles, scan_media_directory
from services.whisper_service import WhisperService
from services.watchdog_service import WatchdogService
from services.embedded_extractor import (
    get_audio_language_info,
    detect_embedded_languages,
    extract_single_subtitle,
    get_embedded_subtitles_info,
    LANGUAGE_MAP,
    TEXT_CODECS,
    get_video_fps
)
from services.subtitle_converter import SubtitleConverter, read_submasterdc_signature, _build_signature_meta
from services.translator import TranslationConfig, translate_srt_file
from utils.lang_detection import detect_language_from_subtitle
from utils.lang_utils import normalize_language_code
import json
import traceback

# Resolve application root directory (absolute) to avoid relative path issues
APP_ROOT = Path(__file__).resolve().parent.parent  # core/worker.py → /app

# Cache for cancellation checks to avoid excessive DB polling
from typing import Dict, Tuple
_CANCELLATION_CACHE: Dict[int, Tuple[bool, float]] = {}
_CANCELLATION_CACHE_TTL = 2.0  # seconds


class TaskWorker:
    """Task Processor"""
    
    def __init__(self):
        """Initialize task processor"""
        self.running = False
        self.config_manager = ConfigManager(get_db_connection)
        self.last_scan_times = {}
        self.task_event = threading.Event()
        self.watchdog = WatchdogService(self.config_manager)
        self.whisper_service: Optional[WhisperService] = None
    
    def _cleanup_startup(self):
        """Cleanup temporary files and logs on startup"""
        app_logger.info("[TaskWorker] Initializing startup cleanup...")
        
        # 0. Reset stuck tasks from previous crashed/stopped runs
        try:
            from database.task_dao import TaskDAO
            reset_count = TaskDAO.reset_stuck_processing_tasks()
            if reset_count > 0:
                app_logger.info(f"[TaskWorker] Reset {reset_count} stuck processing task(s) to pending state.")
        except Exception as e:
            app_logger.error(f"[TaskWorker] Failed to reset stuck tasks: {e}")
        
        # 1. Clean data/temp
        temp_dir = APP_ROOT / "data" / "temp"
        if temp_dir.exists():
            try:
                for item in temp_dir.iterdir():
                    try:
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
                    except Exception as e:
                        app_logger.warning(f"[TaskWorker] Warning: Failed to clean temp item {item}: {e}")
            except Exception as e:
                app_logger.error(f"[TaskWorker] Failed to access temp directory: {e}")
                
        # 2. Truncate debug log
        try:
            from core.logger import clear_logs as safe_clear_logs
            safe_clear_logs()
        except Exception as e:
            app_logger.error(f"[TaskWorker] Failed to truncate log file: {e}")
    
    def start(self):
        """Start processor (runs in a separate thread)"""
        if self.running:
            app_logger.warning("[TaskWorker] Already running")
            return
        
        # Wait for database to be ready
        if not wait_for_database():
            app_logger.error("[TaskWorker] Database not ready, worker stopped")
            return
        
        app_logger.info("[TaskWorker] Starting...")
        self._cleanup_startup()
        self.running = True
        
        # Start watchdog
        self.watchdog.start()
        
        # Start processing loop
        threading.Thread(target=self._worker_loop, name="SubtitleWorker", daemon=True).start()
    
    def stop(self):
        """Stop processor"""
        app_logger.info("[TaskWorker] Stopping...")
        self.running = False
        self.watchdog.stop()
    
    def _worker_loop(self):
        """Worker loop (continuously processes tasks)"""
        while self.running:
            try:
                # Load latest configuration
                config = self.config_manager.load()
                
                # Sync watchdog watchers
                self.watchdog.refresh_watchers()
                
                # Setup active scans lock if not present
                if not hasattr(self, 'active_scans'):
                    self.active_scans = set()
                
                # Check for periodic scans
                current_time = time.time()
                for lib in config.libraries:
                    if lib.scan_mode.value == 'periodic':
                        last_scan = self.last_scan_times.get(lib.id, 0)
                        interval_sec = lib.scan_interval_hours * 3600
                        # Auto-trigger scan if it's been longer than the interval, or on the first loop
                        if last_scan == 0 or (current_time - last_scan >= interval_sec):
                            if lib.path in self.active_scans:
                                app_logger.warning(f"[TaskWorker] Periodic scan for {lib.name} skipped: Previous scan still running")
                                continue
                                
                            app_logger.info(f"[TaskWorker] Starting background periodic scan for {lib.name} ({lib.path})")
                            self.active_scans.add(lib.path)
                            self.last_scan_times[lib.id] = current_time
                            
                            def safe_scan(path):
                                try:
                                    scan_media_directory(path)
                                except Exception as e:
                                    app_logger.error(f"[TaskWorker] Error during background scan of {path}: {e}")
                                finally:
                                    if path in self.active_scans:
                                        self.active_scans.remove(path)
                                        
                            threading.Thread(target=safe_scan, args=(lib.path,), daemon=True).start()
                            
                # Get pending task
                task = TaskDAO.get_pending_task()
                
                if task:
                    app_logger.info(f"[TaskWorker] Processing task {task.id}: {task.file_path}")
                    app_logger.debug(f"[TaskWorker] Task details: {task}")
                    self._process_task(task, config)
                else:
                    # Check for whisper model idle timeout if service exists
                    if self.whisper_service:
                        self.whisper_service.check_idle_timeout(600) # 10 minutes
                    
                    # Sleep when no tasks, wait up to 5s for an event trigger
                    self.task_event.wait(5.0)
                    self.task_event.clear()
            
            except Exception as e:
                app_logger.error(f"[TaskWorker] Error in worker loop: {e}")
                app_logger.debug(traceback.format_exc())
                time.sleep(10)

    def trigger(self):
        """Wake up the worker loop immediately"""
        self.task_event.set()

    def _is_cancelled(self, task_id: int) -> bool:
        """
        Check if a task is cancelled, using a short-lived cache to reduce DB load
        """
        now = time.time()
        cached = _CANCELLATION_CACHE.get(task_id)
        if cached and (now - cached[1] < _CANCELLATION_CACHE_TTL):
            return cached[0]
            
        curr = TaskDAO.get_task_by_id(task_id)
        res = curr is not None and curr.status == TaskStatus.CANCELLED
        _CANCELLATION_CACHE[task_id] = (res, now)
        return res
    
    def _process_update_style_task(self, task_id, target_path, config, log_msg, is_cancelled):
        from database.media_dao import MediaDAO
        from services.subtitle_converter import SubtitleConverter, read_submasterdc_signature, _build_signature_meta
        
        log_msg("Starting style update...", status=TaskStatus.PROCESSING, progress=0)
        
        if os.path.isdir(target_path):
            target_norm = os.path.normpath(target_path)
            media_to_update = MediaDAO.get_media_by_path_prefix(target_norm)
        else:
            m = MediaDAO.get_media_by_path(target_path)
            media_to_update = [m] if m else []
            
        total = len(media_to_update)
        updated_count = 0
        target_format = getattr(config.subtitle_style, 'target_format', 'ass')
        
        for idx, media in enumerate(media_to_update):
            if is_cancelled():
                log_msg("Style update cancelled", status=TaskStatus.CANCELLED)
                return
                
            progress = int((idx / total) * 100) if total > 0 else 0
            log_msg(f"Updating styles for {media.file_name}...", progress=progress)
            
            generated_subs = [s for s in media.subtitles if getattr(s, 'is_app_generated', False)]
            if not generated_subs:
                continue
                
            updated_any_sub = False
            new_sublist = []
            
            for sub in generated_subs:
                sub_file = Path(sub.path)
                if not sub_file.exists():
                    new_sublist.append(sub) 
                    continue
                    
                try:
                    # Read existing signature to detect bilingual files
                    sig = read_submasterdc_signature(str(sub_file))
                    is_bilingual_file = sig and sig.get('bilingual') == 'yes'
                    
                    if is_bilingual_file:
                        # Bilingual files need special handling — cannot use convert_file
                        # We need the source SRTs to regenerate. Check if they exist.
                        primary_lang = sig.get('primary', '')
                        secondary_lang = sig.get('secondary', '')
                        source_name = sig.get('source', '')
                        
                        # Build new signature meta preserving original info
                        new_sig = _build_signature_meta(
                            source_video=source_name,
                            bilingual=True,
                            primary_lang=primary_lang,
                            secondary_lang=secondary_lang
                        )
                        
                        # For bilingual ASS, we need to re-parse and re-generate with new style
                        # Since we can't split a bilingual file back into 2 SRTs easily,
                        # we re-read the ASS entries and regenerate with new style headers
                        new_sub_path = sub_file.with_suffix(f".{target_format}")
                        
                        if sub_file.suffix.lower() == '.ass' and target_format == 'ass':
                            # Re-read and rewrite ASS with new style but same dialogues
                            with open(str(sub_file), 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                            
                            # Parse dialogue lines from existing ASS
                            dialogues = [line for line in content.split('\n') if line.startswith('Dialogue:')]
                            # Remove old branding dialogue (Brand style)
                            dialogues = [d for d in dialogues if ',Brand,' not in d]
                            
                            p_size, s_size = SubtitleConverter.get_font_sizes(config.subtitle_style.font_size_step)
                            style = config.subtitle_style
                            
                            # Build sig comments
                            from services.subtitle_converter import SIGNATURE_TAG, SIGNATURE_BRAND, SIGNATURE_URL
                            sig_comments = f"; {SIGNATURE_TAG}"
                            if new_sig.get('source'):
                                sig_comments += f"\n; Source: {new_sig['source']}"
                            sig_comments += f"\n; Bilingual: yes | Primary: {primary_lang} | Secondary: {secondary_lang}"
                            sig_comments += f"\n; Generated: {new_sig['generated']}"
                            
                            header = f"""[Script Info]
{sig_comments}
Title: Bilingual Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 384
PlayResY: 288

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,{p_size},{style.primary_color},&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,1,2,5,5,5,134
Style: Eng,Microsoft YaHei,{s_size},{style.secondary_color},&H00000000,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,1,2,5,5,5,1
Style: Brand,Microsoft YaHei,8,&H44FFFFFF,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,2,5,5,5,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""
                            
                            # Find last dialogue time for branding
                            import re as _re
                            last_end_ms = 0
                            for d in dialogues:
                                parts = d.split(',', 9)
                                if len(parts) >= 3:
                                    try:
                                        end_str = parts[2].strip()
                                        # Parse ASS time H:MM:SS.cc
                                        h, m_s = end_str.split(':', 1)
                                        m_part, s_part = m_s.rsplit(':', 1)
                                        s, cs = s_part.split('.')
                                        ms = int(h)*3600000 + int(m_part)*60000 + int(s)*1000 + int(cs)*10
                                        if ms > last_end_ms:
                                            last_end_ms = ms
                                    except: pass
                            
                            lines_out = [header] + dialogues
                            if last_end_ms > 0:
                                brand_start = SubtitleConverter.format_ass_time(last_end_ms + 5000)
                                brand_end = SubtitleConverter.format_ass_time(last_end_ms + 8000)
                                lines_out.append(f"Dialogue: 0,{brand_start},{brand_end},Brand,,0,0,0,,{SIGNATURE_BRAND}\\N{SIGNATURE_URL}")
                            
                            with open(str(new_sub_path), 'w', encoding='utf-8') as f:
                                f.write('\n'.join(lines_out))
                            
                            app_logger.info(f"[{task_id}] Re-styled bilingual ASS: {sub_file.name}")
                        else:
                            # For non-ASS bilingual (SRT) or format change, skip with warning
                            app_logger.warning(f"[{task_id}] Skipping bilingual {sub_file.name} (cannot re-style SRT bilingual)")
                            new_sublist.append(sub)
                            continue
                    else:
                        # Non-bilingual: use convert_file as before, with fresh signature
                        new_sub_path = sub_file.with_suffix(f".{target_format}")
                        
                        # Build signature meta from existing sig or defaults
                        new_sig = _build_signature_meta(
                            source_video=sig.get('source', '') if sig else Path(media.file_path).name,
                            bilingual=False,
                            primary_lang=sig.get('primary', '') if sig else '',
                            secondary_lang=''
                        )
                        
                        SubtitleConverter.convert_file(
                            str(sub_file), 
                            target_format, 
                            output_path=str(new_sub_path), 
                            style_config=config.subtitle_style,
                            signature_meta=new_sig
                        )
                    
                    if sub_file != new_sub_path:
                        try: sub_file.unlink()
                        except: pass
                        sub.path = str(new_sub_path)
                        
                    updated_any_sub = True
                        
                except Exception as e:
                    app_logger.error(f"[{task_id}] Failed to update style for {sub_file.name}: {e}")
                
                new_sublist.append(sub)
                
            if updated_any_sub:
                all_subs = [s for s in media.subtitles if not getattr(s, 'is_app_generated', False)] + new_sublist
                MediaDAO.update_media_subtitles(media.file_path, all_subs, media.has_translated)
                updated_count += 1
                
        log_msg(f"Updated styles for {updated_count} files.", status=TaskStatus.COMPLETED, progress=100)

    def _ensure_temp_dir(self, task_id: int) -> Path:
        """Create and return task-specific temp directory"""
        temp_dir = APP_ROOT / 'data' / 'temp' / f'task_{task_id}'
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    def _get_media_context(self, file_path: str, temp_dir: Path, log_msg) -> dict:
        """Probe media and return context info (embedded tracks, etc)"""
        from database.media_dao import MediaDAO
        media_info = MediaDAO.get_media_by_path(file_path)
        
        # extracted_subs will be a dict of {lang_code: stream_index}
        extracted_subs = {}
        has_analyzed_tracks = False
        
        if media_info and media_info.embedded_tracks:
            for t in media_info.embedded_tracks:
                lang = t.get('lang')
                idx = t.get('index')
                if lang and idx is not None:
                    extracted_subs[lang] = idx
                    has_analyzed_tracks = True
        
        if has_analyzed_tracks:
            log_msg(f"Using cached info for {len(extracted_subs)} tracks: {extracted_subs}")
        else:
            log_msg("Probing embedded subtitles (quick scan)...")
            extracted_subs = detect_embedded_languages(file_path, str(temp_dir))
            log_msg(f"Embedded scan finished. Tracks found: {extracted_subs}")
            
            if media_info and extracted_subs:
                full_tracks = get_embedded_subtitles_info(file_path)
                for t in full_tracks:
                    idx = t.get('index')
                    for lang, s_idx in extracted_subs.items():
                        if s_idx == idx:
                            t['lang'] = lang
                            break
                MediaDAO.update_embedded_tracks(file_path, full_tracks)
                log_msg("Saved detected languages to database.")
                
        return {
            'info': media_info,
            'extracted_subs': extracted_subs,
            'whisper_extracted': False,
            'whisper_base_path': temp_dir / f"{Path(file_path).stem}.whisper.srt"
        }

    def _process_task(self, task, config: AppConfig):
        """Process a single task"""
        task_id = task.id
        file_path = task.file_path
        
        try:
            def log_msg(msg: str, status=None, progress=None):
                app_logger.info(f"[{task_id}] {msg}")
                TaskDAO.update_task(task_id, status=status, progress=progress, log=msg)

            if self._is_cancelled(task_id):
                app_logger.info(f"[{task_id}] Task cancelled before processing")
                return

            log_msg("Checking file...", status=TaskStatus.PROCESSING, progress=0)
            
            if not os.path.exists(file_path):
                log_msg("File missing", status=TaskStatus.FAILED)
                return
            
            # Permission check
            video_dir = os.path.dirname(os.path.abspath(file_path))
            if not os.access(video_dir, os.W_OK):
                log_msg("Permission denied: cannot write to video directory", status=TaskStatus.PERMISSION_ERROR)
                return
            
            # Logic branch: update_style vs translation
            try:
                params_dict = json.loads(task.params) if task.params else {}
                if params_dict.get('action') == 'update_style':
                    self._process_update_style_task(task_id, file_path, config, log_msg, lambda: self._is_cancelled(task_id))
                    return
            except Exception as e:
                app_logger.error(f"[{task_id}] Error parsing task parameters: {e}")

            temp_dir = self._ensure_temp_dir(task_id)
            context = self._get_media_context(file_path, temp_dir, log_msg)
            
            # Determine tasks
            translation_tasks = config.translation.tasks if config.translation.enabled else []
            try:
                params_dict = json.loads(task.params) if task.params else {}
                if 'target_language' in params_dict:
                    translation_tasks = [TranslationTask.from_dict(params_dict)]
                    log_msg(f"Manual override detected: {translation_tasks[0].target_language}")
            except: pass

            if not translation_tasks:
                log_msg("No translation tasks defined, skipping", status=TaskStatus.SKIPPED, progress=100)
                return

            # Main processing loop
            self._execute_translation_queue(task_id, file_path, temp_dir, context, translation_tasks, config, log_msg)
            
        except Exception as e:
            app_logger.error(f"[{task_id}] Task failed: {e}")
            app_logger.debug(traceback.format_exc())
            TaskDAO.update_task(task_id, status=TaskStatus.FAILED, log=f"Error: {str(e)}")

    def _execute_translation_queue(self, task_id: int, file_path: str, temp_dir: Path, context: dict, tasks: list, config: AppConfig, log_msg):
        """Iterate over translation tasks and generate subtitles"""
        media_info = context['info']
        existing_subs = media_info.subtitles if media_info else []
        subs_lookup = {Path(s.path).name: s for s in existing_subs}
        
        generated_subs_this_run = []
        any_success = False
        all_skipped = True
        skip_reasons = []

        params_dict = {}
        try:
            from database.task_dao import TaskDAO
            task = TaskDAO.get_task_by_id(task_id)
            params_dict = json.loads(task.params) if task and task.params else {}
        except: pass
        is_manual_override = 'target_language' in params_dict

        for task_item in tasks:
            if self._is_cancelled(task_id):
                log_msg("Task cancelled by user", status=TaskStatus.CANCELLED)
                return
            
            lang = task_item.target_language
            log_msg(f"Processing {lang}...")
            
            # File naming logic
            code = lang if getattr(task_item, 'bilingual_filename_code', 'primary') == 'primary' else task_item.secondary_language
            ass_path = Path(file_path).parent / f"{Path(file_path).stem}.{code}.ass"
            srt_path = Path(file_path).parent / f"{Path(file_path).stem}.{code}.srt"

            # Check if already exists and generated by us
            skip = False
            for target_path in [ass_path, srt_path]:
                if target_path.exists() and target_path.name in subs_lookup:
                    db_sub = subs_lookup[target_path.name]
                    if getattr(db_sub, 'is_app_generated', False):
                        is_bi = getattr(db_sub, 'is_bilingual', False)
                        p_lang = getattr(db_sub, 'primary_lang', None)
                        s_lang = getattr(db_sub, 'secondary_lang', None)
                        
                        task_is_bi = getattr(task_item, 'bilingual_subtitles', False)
                        task_p_lang = lang
                        task_s_lang = getattr(task_item, 'secondary_language', None) if task_is_bi else None

                        if is_bi == task_is_bi and p_lang == task_p_lang and s_lang == task_s_lang:
                            if not is_manual_override:
                                log_msg(f"Skipping {target_path.name} (Metadata matched).")
                                skip_reasons.append(f"{lang}: Metadata matched")
                                skip = True
                                break
                            else:
                                log_msg(f"Overwriting {target_path.name} (Manual Override).")

            if skip: continue
            all_skipped = False

            # Check for embedded track if not bilingual
            req_lang_for_check = normalize_language_code(lang)
            if not task_item.bilingual_subtitles and req_lang_for_check in context['extracted_subs']:
                 if not is_manual_override:
                     log_msg(f"Skipping {lang} (already embedded).")
                     skip_reasons.append(f"{lang}: Already embedded")
                     any_success = True
                     continue

            # Core Generation
            primary_srt = self._get_or_create_srt(task_id, file_path, temp_dir, lang, context, config, log_msg)
            if not primary_srt:
                continue

            any_success = True
            
            if task_item.bilingual_subtitles:
                secondary_srt = self._get_or_create_srt(task_id, file_path, temp_dir, task_item.secondary_language, context, config, log_msg)
                if secondary_srt:
                    bi_sig = _build_signature_meta(Path(file_path).name, True, lang, task_item.secondary_language)
                    if 'ass' in config.export.formats:
                        SubtitleConverter.convert_to_bilingual_ass(primary_srt, secondary_srt, str(ass_path), 
                                                                  style_config=config.subtitle_style, signature_meta=bi_sig)
                        log_msg(f"Generated bilingual ASS ({code})")
                        generated_subs_this_run.append((ass_path.name, task_item))
                    if 'srt' in config.export.formats:
                        SubtitleConverter.convert_to_bilingual_srt(primary_srt, secondary_srt, str(srt_path), signature_meta=bi_sig)
                        log_msg(f"Generated bilingual SRT ({code})")
                        generated_subs_this_run.append((srt_path.name, task_item))
            else:
                mono_sig = _build_signature_meta(Path(file_path).name, False, lang)
                for fmt in config.export.formats:
                    target_p = ass_path if fmt == 'ass' else srt_path
                    if fmt == 'ass':
                        SubtitleConverter.convert_file(primary_srt, 'ass', str(target_p), 
                                                       style_config=config.subtitle_style, signature_meta=mono_sig)
                    else:
                        with open(primary_srt, 'r', encoding='utf-8', errors='ignore') as f:
                            entries = SubtitleConverter.parse_srt(f.read())
                        SubtitleConverter.save_srt(entries, str(target_p), signature_meta=mono_sig)
                    log_msg(f"Generated {fmt} ({code})")
                    generated_subs_this_run.append((target_p.name, task_item))

        # Finalize
        if any_success and not self._is_cancelled(task_id):
            if all_skipped and skip_reasons:
                log_msg("; ".join(skip_reasons), status=TaskStatus.SKIPPED, progress=100)
            else:
                self._update_db_after_generation(file_path, media_info, generated_subs_this_run)
                log_msg("Completed successfully", status=TaskStatus.COMPLETED, progress=100)
        elif not self._is_cancelled(task_id):
            log_msg("Failed to generate subtitles", status=TaskStatus.FAILED, progress=100)

    def _get_or_create_srt(self, task_id: int, file_path: str, temp_dir: Path, lang: str, context: dict, config: AppConfig, log_msg) -> Optional[str]:
        """Returns path to a temp srt file for the given language, creating it if needed"""
        if self._is_cancelled(task_id): return None
        
        req_lang = normalize_language_code(lang)
        lang_srt_path = temp_dir / f"{Path(file_path).stem}.{lang}.srt"
        if lang_srt_path.exists():
            return str(lang_srt_path)
            
        # 1. Direct match among detected tracks
        extracted_subs = context['extracted_subs']
        if req_lang in extracted_subs:
            stream_idx = extracted_subs[req_lang]
            if extract_single_subtitle(file_path, stream_idx, str(lang_srt_path)):
                return str(lang_srt_path)
            
        # 2. Find a BASE track to translate from
        source_lang = config.whisper.source_language
        if source_lang == 'auto':
            source_lang = get_audio_language_info(file_path)
        norm_source = normalize_language_code(source_lang)
        
        base_track = None
        if norm_source in extracted_subs:
            base_path = temp_dir / f"base_{norm_source}.srt"
            if base_path.exists() or extract_single_subtitle(file_path, extracted_subs[norm_source], str(base_path)):
                base_track = str(base_path)
        elif extracted_subs:
            first_lang = next(iter(extracted_subs))
            base_path = temp_dir / f"base_fallback_{first_lang}.srt"
            if base_path.exists() or extract_single_subtitle(file_path, extracted_subs[first_lang], str(base_path)):
                base_track = str(base_path)
                
        # 3. Whisper fallback
        if not base_track:
            if not context['whisper_extracted']:
                log_msg("No text tracks found. Starting Whisper...")
                if self._extract_subtitle(task_id, file_path, config, str(context['whisper_base_path']), log_msg, lambda: self._is_cancelled(task_id)):
                    context['whisper_extracted'] = True
                    base_track = str(context['whisper_base_path'])
            else:
                base_track = str(context['whisper_base_path'])
                
        if not base_track:
            return None
            
        # Translate if needed
        base_detected = detect_language_from_subtitle(base_track)
        if normalize_language_code(base_detected) == req_lang:
            shutil.copy(base_track, str(lang_srt_path))
            return str(lang_srt_path)
            
        if not config.translation.enabled:
            log_msg(f"Translation disabled, cannot generate {lang}")
            return None
            
        if self._translate_subtitle(task_id, base_track, lang, config, str(lang_srt_path)):
            return str(lang_srt_path)
        return None

    def _update_db_after_generation(self, file_path: str, media_info, generated_subs: list):
        """Update database with info about generated subtitle files"""
        if not media_info or not generated_subs: return
        
        from database.media_dao import MediaDAO
        from core.models import SubtitleInfo
        
        existing_subs_by_name = {Path(s.path).name: s for s in media_info.subtitles}
        for g_name, g_task in generated_subs:
            is_bi = getattr(g_task, 'bilingual_subtitles', False)
            p_lang = g_task.target_language
            s_lang = getattr(g_task, 'secondary_language', None) if is_bi else None
            
            if g_name in existing_subs_by_name:
                db_sub = existing_subs_by_name[g_name]
                db_sub.is_app_generated, db_sub.is_bilingual = True, is_bi
                db_sub.primary_lang, db_sub.secondary_lang = p_lang, s_lang
            else:
                media_info.subtitles.append(SubtitleInfo(
                    path=str(Path(file_path).parent / g_name),
                    lang=p_lang or 'unknown',
                    tag="Scanning...",
                    is_app_generated=True,
                    is_bilingual=is_bi,
                    primary_lang=p_lang,
                    secondary_lang=s_lang
                ))
        MediaDAO.update_media_subtitles(file_path, media_info.subtitles, media_info.has_translated)
        rescan_video_subtitles(file_path)
    
    def _extract_subtitle(self, task_id: int, file_path: str, config: AppConfig, output_path: str = None, log_callback=None, is_cancelled=None) -> Optional[str]:
        srt_path = Path(output_path) if output_path else Path(file_path).with_suffix('.srt')
        if srt_path.exists():
            if log_callback: log_callback("Base subtitle exists", progress=50)
            return str(srt_path)
        try:
            if log_callback: log_callback("Loading Whisper...", progress=5)
            vad_params = config.get_vad_parameters()
            
            # Use persistent whisper service
            if self.whisper_service is None:
                self.whisper_service = WhisperService(config.whisper, vad_params)
            else:
                # Update config in case it changed
                self.whisper_service.config = config.whisper
                self.whisper_service.vad_params = vad_params
                
            def progress_callback(current, total, message):
                if log_callback: log_callback(message, progress=current)
                else: TaskDAO.update_task(task_id, progress=current, log=message)
            
            self.whisper_service.extract_subtitle(file_path, str(srt_path), progress_callback, is_cancelled)
            return str(srt_path)
        except InterruptedError:
            if log_callback: log_callback("Whisper extraction cancelled")
            return None
        except Exception as e:
            if log_callback: log_callback(f"Extraction failed: {str(e)[:100]}", status=TaskStatus.FAILED)
            return None
    
    def _translate_subtitle(
        self,
        task_id: int,
        srt_path: str,
        target_lang: str,
        config: AppConfig,
        output_path: Optional[str] = None
    ) -> bool:
        """Translate subtitles via LLM"""
        TaskDAO.update_task(task_id, progress=50, log="Translating...")
        try:
            provider_cfg = config.get_current_provider_config()
            trans_config = TranslationConfig(
                api_key=provider_cfg.api_key,
                base_url=provider_cfg.base_url,
                model_name=provider_cfg.model_name,
                target_language=target_lang,
                source_language=config.whisper.source_language,
                max_lines_per_batch=config.translation.max_lines_per_batch,
                max_daily_calls=config.translation.max_daily_calls,
                max_retries=config.translation.max_retries,
                timeout=config.translation.timeout
            )
            
            usage_callbacks = (
                self.config_manager.get_daily_usage,
                self.config_manager.increment_daily_usage
            )

            def pcb(current, total, message):
                app_logger.info(f"[{task_id}] Translation progress: {message} ({current}/{total} lines)")
                TaskDAO.update_task(task_id, progress=50 + int((current/total)*45), log=message)
            
            def is_cancelled_cb():
                return self._is_cancelled(task_id)

            success, msg = translate_srt_file(
                srt_path, 
                trans_config, 
                output_path, 
                progress_callback=pcb, 
                is_cancelled=is_cancelled_cb,
                usage_callbacks=usage_callbacks
            )
            if not success:
               # If cancelled, translate_srt_file might return False. Check again.
               task = TaskDAO.get_task_by_id(task_id)
               if task and task.status == TaskStatus.CANCELLED:
                   return False
               
               # Report TASK_ERROR_LIMIT_REACHED clearly without cancelling the queue
               if "TASK_ERROR_LIMIT_REACHED" in msg:
                   TaskDAO.update_task(task_id, log=f"Translation failed: max error limit reached ({msg})")
                   app_logger.warning(f"[{task_id}] Translation hit max-error limit: {msg}")
                   return False
                   
               TaskDAO.update_task(task_id, log=f"Trans fail: {msg}")
               if "QUOTA_EXHAUSTED" in msg or "DAILY_LIMIT_REACHED" in msg:
                   # Re-raise outside try/except so _process_task can catch it
                   raise Exception(msg)
            return success
        except Exception as e:
            error_str = str(e)
            # Report TASK_ERROR_LIMIT_REACHED clearly without cancelling the queue
            if "TASK_ERROR_LIMIT_REACHED" in error_str:
                TaskDAO.update_task(task_id, log=f"Translation failed: max error limit reached ({error_str[:80]})")
                app_logger.warning(f"[{task_id}] Translation hit max-error limit: {error_str[:80]}")
                return False
            TaskDAO.update_task(task_id, log=f"Trans exception: {error_str[:100]}")
            # Propagate quota/limit errors to _process_task for mass cancellation
            if "QUOTA_EXHAUSTED" in error_str or "DAILY_LIMIT_REACHED" in error_str:
                raise
            return False


# ============================================================================
# Global Worker Instance
# ============================================================================

_worker_instance: Optional[TaskWorker] = None


def start_worker():
    """Start global worker"""
    global _worker_instance
    
    if _worker_instance is None:
        _worker_instance = TaskWorker()
    
    _worker_instance.start()

def trigger_worker_event():
    """Trigger the worker to wake up and check the queue immediately"""
    if _worker_instance:
        _worker_instance.trigger()


def stop_worker():
    """Stop global worker"""
    
    if _worker_instance:
        _worker_instance.stop()


def get_worker() -> Optional[TaskWorker]:
    """Get global worker instance"""
    return _worker_instance


def trigger_worker():
    """Wake up the global worker thread immediately to process new tasks."""
    if _worker_instance:
        _worker_instance.task_event.set()