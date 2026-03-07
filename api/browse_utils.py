"""Shared utilities for file browsing endpoints"""

import os
import string

# Directories that should never appear in the root-level file browser.
# These are system/application dirs inside a Docker container (or bare Linux).
_SYSTEM_DIRS = {
    'app', 'bin', 'boot', 'dev', 'etc', 'home', 'lib', 'lib32', 'lib64',
    'libx32', 'mnt', 'opt', 'proc', 'root', 'run', 'sbin', 'snap',
    'srv', 'sys', 'tmp', 'usr', 'var',
}


def get_root_dirs():
    """
    List top-level directories suitable for browsing.
    - Windows: returns available drive letters.
    - Linux/Docker: returns '/' subdirectories excluding system/app dirs.
    """
    if os.name == 'nt':
        return [f"{letter}:\\" for letter in string.ascii_uppercase if os.path.exists(f"{letter}:\\")]

    # Linux: list / but filter out system dirs
    try:
        return sorted([
            f"/{d}" for d in os.listdir("/")
            if os.path.isdir(f"/{d}") and not d.startswith('.') and d not in _SYSTEM_DIRS
        ], key=str.lower)
    except (PermissionError, OSError):
        return []
