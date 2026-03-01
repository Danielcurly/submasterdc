import logging
import os
from pathlib import Path

# Provide a global logger for the app
LOG_FILE = Path("logs/debug.log")

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

app_logger = _setup_logger()
