import logging
import os
from pathlib import Path

# Provide a global logger for the app
LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "debug.log"

def _setup_logger():
    os.makedirs(LOG_FILE.parent, exist_ok=True)
    logger = logging.getLogger("SubMasterDC")
    logger.setLevel(logging.DEBUG)
    
    # Avoid adding multiple handlers if setup is called multiple times
    if not logger.handlers:
        fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        
        logger.addHandler(fh)
        
    return logger

_current_log_level = None

def set_log_level(level: str):
    """Dynamically set the application log level"""
    global _current_log_level
    level = level.lower()
    mapping = {
        'off': logging.CRITICAL + 1, # Effectively disabling logging
        'normal': logging.INFO,
        'debug': logging.DEBUG
    }
    target = mapping.get(level, logging.INFO)
    
    # Update app logger and all its existing handlers
    app_logger.setLevel(target)
    for handler in app_logger.handlers:
        handler.setLevel(target)
    
    # Only Log if level actually changed to avoid spamming the log file
    if _current_log_level != target:
        if _current_log_level is not None: # Avoid logging the very first initial setup
             app_logger.info(f"[Logger] Log level changed to: {level.upper()} ({target})")
        _current_log_level = target

def clear_logs():
    """Safely clear the log file without breaking FileHandlers"""
    for handler in app_logger.handlers:
        if isinstance(handler, logging.FileHandler):
            # Safe truncation of the active stream
            handler.acquire()
            try:
                handler.stream.seek(0)
                handler.stream.truncate()
            finally:
                handler.release()
    app_logger.info("[Logger] Log file cleared.")

app_logger = _setup_logger()
set_log_level('normal') # Default to normal quietly
