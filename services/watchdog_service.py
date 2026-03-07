#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Watchdog Service
Responsible for monitoring library directories for new media files
"""

import time
import os
from pathlib import Path
from typing import Dict, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from core.models import ScanMode, SUPPORTED_VIDEO_EXTENSIONS
from services.media_scanner import scan_media_directory
from core.logger import app_logger

class MediaFolderHandler(FileSystemEventHandler):
    """Handles file system events for a specific library"""
    
    def __init__(self, library_path: str):
        self.library_path = library_path
        # Dictionary to track last processed time per file to avoid rapid duplicate triggers
        self.last_triggered = {}
        
    def on_created(self, event):
        if not event.is_directory:
            self._handle_event(event.src_path)
            
    def on_moved(self, event):
        if not event.is_directory:
            self._handle_event(event.dest_path)
    
    def on_deleted(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS:
            app_logger.info(f"[Watchdog] Media file deleted: {event.src_path}")
            try:
                from database.media_dao import MediaDAO
                from database.task_dao import TaskDAO
                # Remove from media_files table
                MediaDAO.delete_media_file(event.src_path)
                # Cancel any pending task for this file
                TaskDAO.cancel_task_by_path(event.src_path)
            except Exception as e:
                app_logger.error(f"[Watchdog] Failed to clean up deleted file {event.src_path}: {e}")
            
    def _handle_event(self, file_path: str):
        path = Path(file_path)
        if path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS:
            # Check for cooldown (5 seconds) to avoid multiple triggers for the same file
            now = time.time()
            if now - self.last_triggered.get(file_path, 0) < 5:
                return
            
            self.last_triggered[file_path] = now
            app_logger.info(f"[Watchdog] New/Moved media detected: {file_path}. Waiting for transfer to complete...")
            
            # Wait for file to be fully written by checking if it can be opened exclusively.
            # On Windows network shares, os.path.getsize() reports the FINAL size immediately,
            # so we must use a lock-based approach instead.
            def wait_for_file_ready(path_str: str, check_interval=3.0, max_wait=600) -> bool:
                """Wait until the file is no longer locked by another process (copy finished)."""
                import time as _time
                elapsed = 0.0
                while elapsed < max_wait:
                    try:
                        # Try to open the file for exclusive read+write access.
                        # If another process (e.g. Windows file copy) holds a lock, this will fail.
                        with open(path_str, 'r+b'):
                            pass
                        # If we get here, the file is not locked. Wait one more interval to be safe.
                        _time.sleep(check_interval)
                        # Double-check it's still accessible (not a brief unlock between copy chunks)
                        with open(path_str, 'r+b'):
                            pass
                        return True
                    except (PermissionError, OSError):
                        _time.sleep(check_interval)
                        elapsed += check_interval
                return False
                
            if wait_for_file_ready(file_path):
                app_logger.info(f"[Watchdog] File transfer complete: {file_path}")
            else:
                app_logger.warning(f"[Watchdog] File still locked after timeout: {file_path}. Scanning anyway.")
            
            try:
                # Get library path context
                # Trigger scan for the directory containing the file
                scan_media_directory(directory=self.library_path, subdirectory=str(path.parent))
            except Exception as e:
                app_logger.error(f"[Watchdog] Failed to process {file_path}: {e}")

class WatchdogService:
    """Manages watchers for all libraries in watchdog mode"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.observer = Observer()
        self.watchers = {}  # library_id -> watch object
        
    def start(self):
        """Start the watchdog observer"""
        app_logger.info("[Watchdog] Starting service...")
        self.observer.start()
        self.refresh_watchers()
        
    def stop(self):
        """Stop the watchdog observer"""
        app_logger.info("[Watchdog] Stopping service...")
        self.observer.stop()
        self.observer.join()
        
    def refresh_watchers(self):
        """Sync watchers with current configuration"""
        try:
            config = self.config_manager.load()
            watchdog_libs = {lib.id: lib for lib in config.libraries if lib.scan_mode == ScanMode.AUTOMATIC}
            
            # Remove watchers for libraries no longer in watchdog mode
            to_remove = []
            for lib_id in self.watchers:
                if lib_id not in watchdog_libs:
                    to_remove.append(lib_id)
            
            for lib_id in to_remove:
                app_logger.info(f"[Watchdog] Removing watcher for library {lib_id}")
                try:
                    self.observer.unschedule(self.watchers[lib_id])
                except Exception as e:
                    app_logger.warning(f"[Watchdog] Failed to unschedule watcher for lib {lib_id}: {e}")
                del self.watchers[lib_id]
            
            # Add/Update watchers for libraries in watchdog mode
            for lib_id, lib in watchdog_libs.items():
                if lib_id not in self.watchers:
                    if Path(lib.path).exists():
                        app_logger.info(f"[Watchdog] Adding watcher for {lib.name} at {lib.path}")
                        handler = MediaFolderHandler(lib.path)
                        watch = self.observer.schedule(handler, lib.path, recursive=True)
                        self.watchers[lib_id] = watch
                    else:
                        app_logger.warning(f"[Watchdog] Cannot watch {lib.path} (path not found)")
        except Exception as e:
            app_logger.error(f"[Watchdog] Error refreshing watchers: {e}")
