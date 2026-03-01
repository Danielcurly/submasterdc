"""Libraries API Router — CRUD for media library folders"""

import os
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from core.config import ConfigManager
from core.models import LibraryFolder, ScanMode
from database.connection import get_db_connection

router = APIRouter()


def _get_config_manager():
    return ConfigManager(get_db_connection)


class LibraryCreate(BaseModel):
    name: str
    path: str
    scan_mode: str = "manual"
    scan_interval_hours: float = 24.0


class LibraryUpdate(BaseModel):
    name: Optional[str] = None
    path: Optional[str] = None
    scan_mode: Optional[str] = None
    scan_interval_hours: Optional[float] = None


@router.get("")
def list_libraries():
    """List all configured libraries"""
    cm = _get_config_manager()
    config = cm.load()
    return [
        {
            "id": lib.id,
            "name": lib.name,
            "path": lib.path,
            "scan_mode": lib.scan_mode.value if isinstance(lib.scan_mode, ScanMode) else str(lib.scan_mode),
            "scan_interval_hours": lib.scan_interval_hours,
            "path_exists": os.path.exists(lib.path)
        }
        for lib in config.libraries
    ]


@router.post("")
def add_library(body: LibraryCreate):
    """Add a new library"""
    if not os.path.exists(body.path):
        raise HTTPException(status_code=400, detail=f"Path '{body.path}' does not exist on the server")

    cm = _get_config_manager()
    config = cm.load()

    new_lib = LibraryFolder(
        id=str(uuid.uuid4())[:8],
        name=body.name,
        path=body.path,
        scan_mode=ScanMode(body.scan_mode),
        scan_interval_hours=body.scan_interval_hours
    )
    config.libraries.append(new_lib)
    cm.save(config)

    return {"id": new_lib.id, "message": f"Library '{body.name}' added"}


@router.put("/{library_id}")
def update_library(library_id: str, body: LibraryUpdate):
    """Update an existing library"""
    cm = _get_config_manager()
    config = cm.load()

    lib = next((l for l in config.libraries if l.id == library_id), None)
    if not lib:
        raise HTTPException(status_code=404, detail="Library not found")

    if body.name is not None:
        lib.name = body.name
    if body.path is not None:
        if not os.path.exists(body.path):
            raise HTTPException(status_code=400, detail=f"Path '{body.path}' does not exist")
        lib.path = body.path
    if body.scan_mode is not None:
        lib.scan_mode = ScanMode(body.scan_mode)
    if body.scan_interval_hours is not None:
        lib.scan_interval_hours = body.scan_interval_hours

    cm.save(config)
    return {"message": "Library updated"}


@router.delete("/{library_id}")
def delete_library(library_id: str):
    """Delete a library"""
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.debug(f"[DELETE LIBRARY] Attempting to delete library with ID: {library_id}")
    
    cm = _get_config_manager()
    config = cm.load()
    
    logger.debug(f"[DELETE LIBRARY] Current libraries in config: {[l.id for l in config.libraries]}")

    idx = next((i for i, l in enumerate(config.libraries) if l.id == library_id), None)
    if idx is None:
        logger.debug(f"[DELETE LIBRARY] Library ID {library_id} not found in config. Returning 404.")
        raise HTTPException(status_code=404, detail="Library not found")

    removed = config.libraries.pop(idx)
    logger.debug(f"[DELETE LIBRARY] Found library at index {idx}: {removed.name}. Popped from list.")
    
    try:
        saved = cm.save(config)
        logger.debug(f"[DELETE LIBRARY] Configured saved: {saved}. Remaining libraries: {[l.id for l in config.libraries]}")
    except Exception as e:
        logger.error(f"[DELETE LIBRARY] Error saving config: {e}")
        raise HTTPException(status_code=500, detail="Error saving configuration")
        
    return {"message": f"Library '{removed.name}' deleted"}


@router.get("/browse")
def browse_directory(path: str = ""):
    """Browse server directories for library path selection"""
    if not path:
        if os.name == 'nt':
            # Windows: list available drives
            import string
            drives = []
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    drives.append(drive)
            return {"current": "", "parent": "", "dirs": drives}
        else:
            path = "/"

    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Invalid directory path")

    try:
        subdirs = sorted([
            d for d in os.listdir(path)
            if os.path.isdir(os.path.join(path, d)) and not d.startswith('.')
        ], key=lambda x: x.lower())
    except (PermissionError, OSError):
        subdirs = []

    parent = os.path.dirname(path)
    return {"current": path, "parent": parent, "dirs": subdirs}
