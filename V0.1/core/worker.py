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
from services.media_scanner import rescan_video_subtitles
from services.whisper_service import WhisperService
from services.watchdog_service import WatchdogService
from core.logger import app_logger


class TaskWorker:
    """Task Processor"""
    
    def __init__(self):
        """Initialize task processor"""
        self.running = False
        self.config_manager = ConfigManager(get_db_connection)
        self.last_scan_times = {}
        self.watchdog = WatchdogService(self.config_manager)
    
    def start(self):
        """Start processor (runs in a separate thread)"""
        if self.running:
            print("[TaskWorker] Already running")
            return
        
        # Wait for database to be ready
        if not wait_for_database():
            print("[TaskWorker] Database not ready, worker stopped")
            return
        
        print("[TaskWorker] Starting...")
        self.running = True
        
        # Start watchdog
        self.watchdog.start()
        
        # Start processing loop
        threading.Thread(target=self._worker_loop, daemon=True).start()
    
    def stop(self):
        """Stop processor"""
        print("[TaskWorker] Stopping...")
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
                
                # Check for periodic scans
                current_time = time.time()
                from services.media_scanner import scan_media_directory
                for lib in config.libraries:
                    if lib.scan_mode.value == 'periodic':
                        last_scan = self.last_scan_times.get(lib.id, 0)
                        interval_sec = lib.scan_interval_hours * 3600
                        # Auto-trigger scan if it's been longer than the interval, or on the first loop
                        if last_scan == 0 or (current_time - last_scan >= interval_sec):
                            print(f"[TaskWorker] Starting background periodic scan for {lib.name} ({lib.path})")
                            threading.Thread(target=scan_media_directory, args=(lib.path,), daemon=True).start()
                            self.last_scan_times[lib.id] = current_time
                            
                # Get pending task
                task = TaskDAO.get_pending_task()
                
                if task:
                    print(f"[TaskWorker] Processing task {task.id}: {task.file_path}")
                    self._process_task(task, config)
                else:
                    # Sleep when no tasks
                    time.sleep(5)
            
            except Exception as e:
                print(f"[TaskWorker] Error in worker loop: {e}")
                time.sleep(10)
    
    def _process_task(self, task, config: AppConfig):
        """
        Process a single task
        """
        task_id = task.id
        file_path = task.file_path
        
        try:
            # Update task status
            def log_msg(msg: str, status=None, progress=None):
                app_logger.info(f"[{task_id}] {msg}")
                TaskDAO.update_task(task_id, status=status, progress=progress, log=msg)

            def is_cancelled() -> bool:
                curr = TaskDAO.get_task_by_id(task_id)
                return curr is not None and curr.status == TaskStatus.CANCELLED

            if is_cancelled():
                app_logger.info(f"[{task_id}] Task cancelled before processing")
                return

            log_msg("Checking file...", status=TaskStatus.PROCESSING, progress=0)
            
            if not os.path.exists(file_path):
                log_msg("File missing", status=TaskStatus.FAILED)
                return
            
            from services.embedded_extractor import (
                extract_embedded_subtitle, 
                get_embedded_subtitles_info, 
                get_audio_language_info,
                LANGUAGE_MAP
            )
            from services.subtitle_converter import SubtitleConverter
            
            # Create temp directory for intermediate files
            temp_dir = Path('./data/temp') / f'task_{task_id}'
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            base_srt_path = temp_dir / f"{Path(file_path).stem}.srt"
            whisper_extracted = False
            embedded_streams = get_embedded_subtitles_info(file_path)
            
            def is_embedded(lang_code: str) -> bool:
                allowed = LANGUAGE_MAP.get(lang_code.lower(), [lang_code.lower()])
                for stream in embedded_streams:
                    tags = stream.get("tags", {})
                    if tags.get("language", "").lower() in allowed:
                        return True
                return False
            
            def ensure_base_srt():
                nonlocal whisper_extracted
                if is_cancelled(): return False
                
                if base_srt_path.exists():
                    return True
                
                # Check for source language
                source_lang = config.whisper.source_language
                if source_lang == 'auto':
                    # Best attempt to guess language from audio track
                    source_lang = get_audio_language_info(file_path)
                    
                # Try embedded extraction first
                if is_embedded(source_lang):
                     log_msg(f"Extracting base embedded {source_lang}")
                     if extract_embedded_subtitle(file_path, source_lang, str(base_srt_path)):
                         whisper_extracted = True  # Mark as extracted (bypasses whisper logic below)
                         return True
                         
                # Fallback to whisper
                if not whisper_extracted:
                    res = self._extract_subtitle(task_id, file_path, config, str(base_srt_path), log_msg, is_cancelled)
                    whisper_extracted = True
                    return res is not None
                    
                return False

            def get_or_create_srt(lang: str) -> Optional[str]:
                """Returns path to a temp srt file for the given language"""
                if is_cancelled(): return None
                
                # Extract to temp directory
                lang_srt_path = temp_dir / f"{Path(file_path).stem}.{lang}.srt"
                if lang_srt_path.exists():
                    return str(lang_srt_path)
                
                if extract_embedded_subtitle(file_path, lang, str(lang_srt_path)):
                    from utils.lang_detection import detect_language_from_subtitle
                    detected = detect_language_from_subtitle(str(lang_srt_path))
                    
                    base_detected = detected
                    if detected in ['chs', 'cht']: base_detected = 'zh'
                    elif detected == 'eng': base_detected = 'en'
                    
                    base_lang = lang if lang not in ['chs', 'cht'] else 'zh'
                    
                    if base_detected != 'unknown' and base_detected != base_lang:
                        log_msg(f"Discarded mislabeled embedded {lang} (was {detected})")
                        app_logger.warning(f"[{task_id}] Mislabeled Sub: expected {lang}, found {detected}")
                        try: Path(lang_srt_path).unlink()
                        except: pass
                    else:
                        log_msg(f"Extracted embedded {lang}")
                        return str(lang_srt_path)
                
                if ensure_base_srt():
                    from utils.lang_detection import detect_language_from_subtitle
                    base_detected = detect_language_from_subtitle(str(base_srt_path))
                    base_lang_norm = base_detected
                    if base_detected in ['chs', 'cht']: base_lang_norm = 'zh'
                    elif base_detected == 'eng': base_lang_norm = 'en'
                    
                    if lang == base_lang_norm:
                        shutil.copy(base_srt_path, lang_srt_path)
                        return str(lang_srt_path)
                    
                    if not config.translation.enabled:
                        log_msg(f"Translation disabled, cannot meet requested lang {lang} from extracted {base_lang_norm}")
                        app_logger.warning(f"Translation disabled, cannot copy extracted {base_lang_norm} to {lang}.srt")
                        return None
                    
                    success = self._translate_subtitle(
                        task_id=task_id,
                        srt_path=str(base_srt_path),
                        target_lang=lang,
                        config=config,
                        output_path=str(lang_srt_path)
                    )
                    if success:
                        return str(lang_srt_path)
                return None

            tasks = config.translation.tasks if config.translation.enabled else []
            is_manual_override = False
            
            # Check for manual overrides stored in the task
            if getattr(task, 'params', None):
                import json
                try:
                    params_dict = json.loads(task.params)
                    if 'target_language' in params_dict:
                        task_item = TranslationTask.from_dict(params_dict)
                        tasks = [task_item]
                        is_manual_override = True
                        log_msg(f"Manual override detected: {task_item.target_language}")
                except Exception as e:
                    print(f"[TaskWorker] Error parsing task parameters: {e}")
            
            if not tasks:
                log_msg("No translation tasks defined, skipping", status=TaskStatus.SKIPPED, progress=100)
                return
                
            from database.media_dao import MediaDAO
            media_info = MediaDAO.get_media_by_path(file_path)
            existing_subs = media_info.subtitles if media_info else []
            subs_lookup = {Path(s.path).name: s for s in existing_subs}
            generated_subs_this_run = []
                
            any_success = False
            all_skipped = True
            skip_reasons = []
            for task_item in tasks:
                if is_cancelled():
                    log_msg("Task cancelled by user", status=TaskStatus.CANCELLED)
                    app_logger.info(f"[{task_id}] Task cancelled during loop")
                    return
                    
                lang = task_item.target_language
                log_msg(f"Processing {lang}...")
                
                if task_item.bilingual_subtitles:
                    code = lang if getattr(task_item, 'bilingual_filename_code', 'primary') == 'primary' else task_item.secondary_language
                else:
                    code = lang
                
                ass_path = Path(file_path).parent / f"{Path(file_path).stem}.{code}.ass"
                srt_path = Path(file_path).parent / f"{Path(file_path).stem}.{code}.srt"

                skip = False
                for target_path in [ass_path, srt_path]:
                    if target_path.exists() and target_path.suffix.lstrip('.') in config.export.formats:
                        filename = target_path.name
                        if filename in subs_lookup:
                            db_sub = subs_lookup[filename]
                            if getattr(db_sub, 'is_app_generated', False):
                                is_bi = getattr(db_sub, 'is_bilingual', False)
                                p_lang = getattr(db_sub, 'primary_lang', None)
                                s_lang = getattr(db_sub, 'secondary_lang', None)
                                
                                task_is_bi = getattr(task_item, 'bilingual_subtitles', False)
                                task_p_lang = task_item.target_language
                                task_s_lang = getattr(task_item, 'secondary_language', None) if task_is_bi else None
                                
                                if is_bi == task_is_bi and p_lang == task_p_lang and s_lang == task_s_lang:
                                    if not is_manual_override:
                                        log_msg(f"Skipping {filename} (Metadata matched).")
                                        skip = True
                                    else:
                                        log_msg(f"Overwriting {filename} (Manual Override).")
                                else:
                                    log_msg(f"Overwriting {filename} (Rule changed).")
                            else:
                                if target_path.suffix.lower() == '.ass':
                                    if not is_manual_override:
                                        log_msg(f"Skipping {filename} (External ASS).")
                                        skip = True
                                    else:
                                        log_msg(f"Overwriting {filename} (Manual Override).")
                                else:
                                    log_msg(f"Overwriting {filename} (External SRT).")
                        else:
                            if target_path.suffix.lower() == '.ass':
                                if not is_manual_override:
                                    log_msg(f"Skipping {filename} (External ASS).")
                                    skip = True
                                else:
                                    log_msg(f"Overwriting {filename} (Manual Override).")
                                
                if skip:
                    any_success = True
                    continue
                
                if not task_item.bilingual_subtitles and is_embedded(lang):
                    if not is_manual_override:
                        reason = f"{code}: Already embedded in video"
                        skip_reasons.append(reason)
                        app_logger.info(f"[{task_id}] Skipping {code} external (already embedded).")
                        any_success = True
                        continue
                    else:
                        app_logger.info(f"[{task_id}] Generating {code} despite embedded (Manual Override).")
                
                primary_srt = get_or_create_srt(lang)
                if not primary_srt:
                    log_msg(f"Failed {lang}")
                    continue
                
                any_success = True
                all_skipped = False
                
                if task_item.bilingual_subtitles:
                    secondary_srt = get_or_create_srt(task_item.secondary_language)
                    if secondary_srt:
                        # Generate ASS first (reads from source SRTs)
                        if 'ass' in config.export.formats:
                            SubtitleConverter.convert_to_bilingual_ass(primary_srt, secondary_srt, str(ass_path))
                            log_msg(f"Generated bilingual ASS ({code})")
                            generated_subs_this_run.append((ass_path.name, task_item))
                        # Generate bilingual SRT (may overwrite primary_srt if same path)
                        if 'srt' in config.export.formats:
                            SubtitleConverter.convert_to_bilingual_srt(primary_srt, secondary_srt, str(srt_path))
                            log_msg(f"Generated bilingual SRT ({code})")
                            generated_subs_this_run.append((srt_path.name, task_item))
                        # If only ASS was requested, remove the intermediate SRT
                        elif srt_path.exists():
                            try: srt_path.unlink()
                            except: pass
                                
                    # Cleanup: temp dir handles this now
                    pass
                else:
                    for ext in config.export.formats:
                        if ext == 'ass':
                            SubtitleConverter.convert_file(primary_srt, 'ass', str(ass_path))
                            log_msg(f"Generated single ASS ({code})")
                            generated_subs_this_run.append((ass_path.name, task_item))
                        elif ext == 'srt':
                            shutil.copy(primary_srt, str(srt_path))
                            log_msg(f"Generated single SRT ({code})")
                            generated_subs_this_run.append((srt_path.name, task_item))
            
            if any_success and not is_cancelled():
                if all_skipped and skip_reasons:
                    reason_str = "; ".join(skip_reasons)
                    log_msg(reason_str, status=TaskStatus.SKIPPED, progress=100)
                else:
                    log_msg("Completed successfully", status=TaskStatus.COMPLETED, progress=100)
            elif not is_cancelled():
                log_msg("Failed to generate subtitles", status=TaskStatus.FAILED, progress=100)
            
            if not is_cancelled():
               rescan_video_subtitles(file_path)
            
            # Post-process DB to save rules on freshly generated files
            if generated_subs_this_run:
                media_info = MediaDAO.get_media_by_path(file_path)
                if media_info:
                    for db_sub in media_info.subtitles:
                        fname = Path(db_sub.path).name
                        for g_name, g_task in generated_subs_this_run:
                            if fname == g_name:
                                db_sub.is_app_generated = True
                                db_sub.is_bilingual = getattr(g_task, 'bilingual_subtitles', False)
                                db_sub.primary_lang = getattr(g_task, 'target_language', None)
                                db_sub.secondary_lang = getattr(g_task, 'secondary_language', None) if db_sub.is_bilingual else None
                    MediaDAO.update_media_subtitles(file_path, media_info.subtitles, media_info.has_translated)
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[TaskWorker] Task {task_id} failed: {e}\n{tb}")
            app_logger.error(f"[{task_id}] Exception: {e}\n{tb}")
            TaskDAO.update_task(task_id, status=TaskStatus.FAILED, log=f"Exception: {str(e)[:100]}")
            
            if "QUOTA_EXHAUSTED" in str(e):
                app_logger.error(f"[{task_id}] ALL AI QUOTAS EXHAUSTED. CANCELLING ENTIRE QUEUE.")
                TaskDAO.cancel_all_tasks()
        finally:
            # Always cleanup temp directory
            try:
                temp_dir = Path('./data/temp') / f'task_{task_id}'
                if temp_dir.exists():
                    shutil.rmtree(str(temp_dir), ignore_errors=True)
            except:
                pass
    
    def _extract_subtitle(self, task_id: int, file_path: str, config: AppConfig, output_path: str = None, log_callback=None, is_cancelled=None) -> Optional[str]:
        srt_path = Path(output_path) if output_path else Path(file_path).with_suffix('.srt')
        if srt_path.exists():
            if log_callback: log_callback("Base subtitle exists", progress=50)
            return str(srt_path)
        try:
            if log_callback: log_callback("Loading Whisper...", progress=5)
            vad_params = config.get_vad_parameters()
            whisper = WhisperService(config.whisper, vad_params)
            def progress_callback(current, total, message):
                if log_callback: log_callback(message, progress=current)
                else: TaskDAO.update_task(task_id, progress=current, log=message)
            whisper.extract_subtitle(file_path, str(srt_path), progress_callback, is_cancelled)
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
        from database.task_dao import TaskDAO
        import os
        TaskDAO.update_task(task_id, progress=50, log="Translating...")
        try:
            from services.translator import TranslationConfig, translate_srt_file
            provider_cfg = config.get_current_provider_config()
            trans_config = TranslationConfig(
                api_key=provider_cfg.api_key,
                base_url=provider_cfg.base_url,
                model_name=provider_cfg.model_name,
                target_language=target_lang,
                source_language=config.whisper.source_language,
                max_lines_per_batch=config.translation.max_lines_per_batch
            )
            def pcb(current, total, message):
                TaskDAO.update_task(task_id, progress=50 + int((current/total)*45), log=message)
            
            def is_cancelled_cb():
                t = TaskDAO.get_task_by_id(task_id)
                return t is not None and t.status == TaskStatus.CANCELLED

            success, msg = translate_srt_file(
                srt_path, 
                trans_config, 
                output_path, 
                progress_callback=pcb, 
                is_cancelled=is_cancelled_cb
            )
            if not success:
               # If cancelled, translate_srt_file might return False. Check again.
               task = TaskDAO.get_task_by_id(task_id)
               if task and task.status == TaskStatus.CANCELLED:
                   return False
                   
               TaskDAO.update_task(task_id, log=f"Trans fail: {msg}")
               if "QUOTA_EXHAUSTED" in msg:
                   raise Exception(msg)
            return success
        except Exception as e:
            TaskDAO.update_task(task_id, log=f"Trans exception: {str(e)[:100]}")
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


def stop_worker():
    """Stop global worker"""
    global _worker_instance
    
    if _worker_instance:
        _worker_instance.stop()


def get_worker() -> Optional[TaskWorker]:
    """Get global worker instance"""
    return _worker_instance