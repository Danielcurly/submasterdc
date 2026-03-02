#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Media Scanning Service
Responsible for scanning media directories and discovering subtitle files
"""

import os
import json
from pathlib import Path
from typing import List, Tuple, Optional

from core.models import SubtitleInfo, SUPPORTED_VIDEO_EXTENSIONS
from database.media_dao import MediaDAO
from utils.lang_detection import detect_language_combined


# Default media root directory
# Resolve MEDIA_ROOT to absolute path to avoid ambiguity in Docker/different CWDs
MEDIA_ROOT = os.path.abspath(os.getenv("MEDIA_ROOT", "/media" if os.name != 'nt' else "./media"))


class MediaScanner:
    """Media Scanner"""
    
    def __init__(self, media_root: str = MEDIA_ROOT):
        """
        Initialize scanner
        
        Args:
            media_root: Media root directory
        """
        self.media_root = Path(media_root)
    
    def discover_subdirectories(self, max_depth: int = 3) -> List[str]:
        """
        Discover all subdirectories under the media root
        
        Args:
            max_depth: Maximum scanning depth
        
        Returns:
            List of relative paths (e.g. ["Movies/Action", "TV Shows/Drama"])
        """
        if not self.media_root.exists():
            return []
        
        subdirs = []
        
        try:
            # Breadth-first search to avoid recursion depth issues
            to_scan = [(self.media_root, 0)]  # (path, depth)
            
            while to_scan:
                current_dir, depth = to_scan.pop(0)
                
                if depth >= max_depth:
                    continue
                
                try:
                    for item in current_dir.iterdir():
                        if item.is_dir() and not item.name.startswith('.'):
                            # Calculate relative path
                            rel_path = str(item.relative_to(self.media_root))
                            subdirs.append(rel_path)
                            
                            # Continue scanning next level
                            if depth + 1 < max_depth:
                                to_scan.append((item, depth + 1))
                except PermissionError:
                    continue
        
        except Exception as e:
            print(f"[MediaScanner] Failed to discover subdirectories: {e}")
        
        return sorted(subdirs)
    
    def scan_directory(
        self, 
        subdirectory: Optional[str] = None,
        debug: bool = False
    ) -> Tuple[int, List[str], List[str]]:
        """
        Scan media directory
        
        Args:
            subdirectory: Relative path of subdirectory (None=scan all)
            debug: Whether to output debug logs
        
        Returns:
            (Number of added files, Debug logs list, List of found video paths)
        """
        # Determine scan path
        if subdirectory:
            # Use resolve() to get absolute path
            scan_path = (self.media_root / subdirectory).resolve()
            if not scan_path.exists():
                return 0, [f"Subdirectory does not exist: {subdirectory}"], []
        else:
            scan_path = self.media_root.resolve()
        
        if not scan_path.exists():
            return 0, [f"Path does not exist: {scan_path}"], []
        
        added_count = 0
        debug_logs = []
        batch_data = []
        found_paths = []
        
        if debug:
            debug_logs.append(f"📂 Scanning directory: {scan_path}")
        
        try:
            # Traverse directory
            for root, dirs, files in os.walk(scan_path):
                for file in files:
                    file_path = Path(root) / file
                    
                    # Check if supported video extension
                    if file_path.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
                        continue
                    
                    try:
                        existing_media = MediaDAO.get_media_by_path(str(file_path))
                        existing_subs = existing_media.subtitles if existing_media else []
                        
                        # Scan subtitles for video
                        subtitles = self._scan_subtitles_for_video(file_path, existing_subs)
                        
                        # Check if has translations
                        has_translated = self._check_has_translation(subtitles)
                        
                        # Prepare batch data for insertion
                        subtitles_json = json.dumps(
                            [s.to_dict() for s in subtitles],
                            ensure_ascii=False
                        )
                        
                        batch_data.append((
                            str(file_path),
                            file,
                            file_path.stat().st_size,
                            subtitles_json,
                            int(has_translated)
                        ))
                        
                        found_paths.append(str(file_path))
                        added_count += 1
                        
                        if debug:
                            debug_logs.append(f"✓ Found: {file}")
                    
                    except Exception as e:
                        if debug:
                            debug_logs.append(f"✗ ERROR {file}: {e}")
            
            # Batch write to database
            if batch_data:
                MediaDAO.batch_add_or_update_media_files(batch_data)
                if debug:
                    debug_logs.append(f"✓ Batch wrote {len(batch_data)} records")
        
        except Exception as e:
            print(f"[MediaScanner] Scan failed: {e}")
            if debug:
                debug_logs.append(f"✗ Scan failed: {e}")
        
        return added_count, debug_logs, found_paths
    
    def _scan_subtitles_for_video(self, video_path: Path, existing_subs: List[SubtitleInfo] = None) -> List[SubtitleInfo]:
        """
        Scan subtitles corresponding to a video file
        """
        subtitles = []
        base_name = video_path.stem
        parent_dir = video_path.parent
        existing_lookup = {s.path: s for s in (existing_subs or [])}
        
        try:
            # Find SRT and ASS files with same name
            all_files = list(parent_dir.iterdir())
            
            potential_subs = [
                p for p in all_files
                if p.is_file()
                and p.name.lower().endswith(('.srt', '.ass'))
                and p.name.lower().startswith(base_name.lower())
            ]
            
            for sub_path in potential_subs:
                sub_name = sub_path.name
                path_str = str(sub_path)
                
                # Check if it was tracked as app-generated
                is_app_generated = False
                is_bilingual = False
                primary_lang = None
                secondary_lang = None
                
                if path_str in existing_lookup:
                    s_info = existing_lookup[path_str]
                    is_app_generated = getattr(s_info, 'is_app_generated', False)
                    is_bilingual = getattr(s_info, 'is_bilingual', False)
                    primary_lang = getattr(s_info, 'primary_lang', None)
                    secondary_lang = getattr(s_info, 'secondary_lang', None)
                
                # Detect language
                lang_code, tag = detect_language_combined(
                    path_str,
                    sub_name
                )
                
                # Check if default subtitle
                if sub_path.stem.lower() == base_name.lower():
                    tag += " (Default)"
                
                subtitles.append(SubtitleInfo(
                    path=path_str,
                    lang=lang_code,
                    tag=tag,
                    is_app_generated=is_app_generated,
                    is_bilingual=is_bilingual,
                    primary_lang=primary_lang,
                    secondary_lang=secondary_lang
                ))
        
        except Exception as e:
            print(f"[MediaScanner] Failed to scan subtitles for {video_path}: {e}")
        
        return subtitles
    
    def _check_has_translation(self, subtitles: List[SubtitleInfo]) -> bool:
        """Check if there are Chinese translation subtitles"""
        for sub in subtitles:
            if sub.lang.lower() in ['zh', 'chs', 'cht']:
                return True
        return False
    
    def rescan_single_video(self, video_path: str):
        """Rescan subtitles for a single video file"""
        path = Path(video_path)
        if not path.exists():
            return
        
        existing_media = MediaDAO.get_media_by_path(video_path)
        existing_subs = existing_media.subtitles if existing_media else []
        
        subtitles = self._scan_subtitles_for_video(path, existing_subs)
        has_translated = self._check_has_translation(subtitles)
        
        MediaDAO.update_media_subtitles(video_path, subtitles, has_translated)


# ============================================================================
# Quick Functions
# ============================================================================

def scan_media_directory(
    directory: Optional[str] = None,
    subdirectory: Optional[str] = None,
    debug: bool = False,
    force_failed_retry: bool = False
) -> Tuple[int, List[str]]:
    """
    Scan media directory (quick function)
    """
    from database.connection import get_db_connection
    from core.config import ConfigManager
    from database.task_dao import TaskDAO
    
    mgr = ConfigManager(get_db_connection)
    config = mgr.load()
    
    # Build config signature from current translation settings
    # This allows add_task to detect if translation config changed
    import json
    if config.translation.tasks:
        lang_sig = sorted(set(t.target_language for t in config.translation.tasks))
    else:
        lang_sig = []  # No tasks means no output files requested
    config_sig = json.dumps({'langs': lang_sig})
    
    def normalize_root(p):
        path_str = os.path.abspath(p)
        # If it's just a drive (e.g. D:), ensure it has a separator.
        if os.name == 'nt' and len(path_str) == 2 and path_str[1] == ':':
            path_str += os.sep
        return path_str

    roots = [normalize_root(lib.path) for lib in config.libraries]
    total_cnt = 0
    all_logs = []
    all_found_paths = []
    
    if directory:
        roots = [normalize_root(directory)]
    
    if subdirectory:
        subdirectory = normalize_root(subdirectory)
        
    for root in roots:
        current_sub = subdirectory
        # Check if subdirectory is absolute and inside root
        if subdirectory and os.path.isabs(subdirectory):
            try:
                # Use Path.is_relative_to for more robust path checking
                if Path(subdirectory).is_relative_to(Path(root)):
                    current_sub = os.path.relpath(subdirectory, root)
                    if current_sub == '.': current_sub = None
                else:
                    # Subdirectory is not under this root
                    continue
            except (ValueError, TypeError):
                # Happens if drives are different or other path issues
                continue

        scanner = MediaScanner(root)
        cnt, logs, paths = scanner.scan_directory(current_sub, debug)
        total_cnt += cnt
        if logs:
            all_logs.extend(logs)
        if paths:
            all_found_paths.extend(paths)
            
    # Trigger tasks for all found media (with config signature for dedup)
    for p in all_found_paths:
        # Ensure path is absolute and normalized
        abs_p = os.path.abspath(p)
        TaskDAO.add_task(abs_p, config_sig, force_failed_retry=force_failed_retry)
            
    return total_cnt, all_logs


def discover_media_subdirectories(
    directory: Optional[str] = None,
    max_depth: int = 2
) -> List[str]:
    """Discover media subdirectories"""
    from database.connection import get_db_connection
    from core.config import ConfigManager
    
    mgr = ConfigManager(get_db_connection)
    config = mgr.load()
    
    roots = [directory] if directory else [lib.path for lib in config.libraries]
    all_subdirs = []
    
    for root in roots:
        scanner = MediaScanner(root)
        subdirs = scanner.discover_subdirectories(max_depth)
        for sd in subdirs:
            if len(roots) > 1:
                all_subdirs.append(os.path.join(root, sd))
            else:
                all_subdirs.append(sd)
                
    return sorted(list(set(all_subdirs)))


def rescan_video_subtitles(video_path: str):
    """Rescan video subtitles"""
    scanner = MediaScanner()
    scanner.rescan_single_video(video_path)