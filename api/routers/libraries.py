"""Libraries API Router — CRUD for media library folders"""

import os
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from core.config import ConfigManager
from core.models import LibraryFolder, ScanMode, StandardResponse
from database.connection import get_db_connection
from api.deps import get_config_manager

router = APIRouter()


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


@router.get("", response_model=StandardResponse)
def list_libraries():
    """List all configured libraries"""
    from database.media_dao import MediaDAO
    cm = get_config_manager()
    config = cm.load()
    data = [
        {
            "id": lib.id,
            "name": lib.name,
            "path": lib.path,
            "scan_mode": lib.scan_mode.value if isinstance(lib.scan_mode, ScanMode) else str(lib.scan_mode),
            "scan_interval_hours": lib.scan_interval_hours,
            "path_exists": os.path.exists(lib.path),
            "file_count": MediaDAO.get_media_count_for_library(lib.path)
        }
        for lib in config.libraries
    ]
    return StandardResponse(success=True, message="Libraries loaded", data=data)


@router.post("", response_model=StandardResponse)
def add_library(body: LibraryCreate):
    """Add a new library"""
    if not os.path.exists(body.path):
        return StandardResponse(success=False, message=f"Path '{body.path}' does not exist on the server")

    cm = get_config_manager()
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

    return StandardResponse(success=True, message=f"Library '{body.name}' added", data={"id": new_lib.id})


@router.put("/{library_id}", response_model=StandardResponse)
def update_library(library_id: str, body: LibraryUpdate):
    """Update an existing library"""
    cm = get_config_manager()
    config = cm.load()

    lib = next((l for l in config.libraries if l.id == library_id), None)
    if not lib:
        return StandardResponse(success=False, message="Library not found")

    if body.name is not None:
        lib.name = body.name
    if body.path is not None:
        if not os.path.exists(body.path):
            return StandardResponse(success=False, message=f"Path '{body.path}' does not exist")
        lib.path = body.path
    if body.scan_mode is not None:
        lib.scan_mode = ScanMode(body.scan_mode)
    if body.scan_interval_hours is not None:
        lib.scan_interval_hours = body.scan_interval_hours

    cm.save(config)
    return StandardResponse(success=True, message="Library updated")


@router.delete("/{library_id}", response_model=StandardResponse)
def delete_library(library_id: str):
    """Delete a library"""
    from core.logger import app_logger
    app_logger.debug(f"[DELETE LIBRARY] Attempting to delete library with ID: {library_id}")
    
    cm = get_config_manager()
    config = cm.load()
    
    app_logger.debug(f"[DELETE LIBRARY] Current libraries in config: {[l.id for l in config.libraries]}")

    idx = next((i for i, l in enumerate(config.libraries) if l.id == library_id), None)
    if idx is None:
        app_logger.debug(f"[DELETE LIBRARY] Library ID {library_id} not found in config. Returning 404.")
        return StandardResponse(success=False, message="Library not found")

    removed = config.libraries.pop(idx)
    app_logger.debug(f"[DELETE LIBRARY] Found library at index {idx}: {removed.name}. Popped from list.")
    
    try:
        saved = cm.save(config)
        app_logger.debug(f"[DELETE LIBRARY] Config saved: {saved}. Remaining libraries: {[l.id for l in config.libraries]}")
    except Exception as e:
        app_logger.error(f"[DELETE LIBRARY] Error saving config: {e}")
        return StandardResponse(success=False, message="Error saving configuration")
        
    return StandardResponse(success=True, message=f"Library '{removed.name}' deleted")


@router.get("/browse", response_model=StandardResponse)
def browse_directory(path: str = ""):
    """Browse server directories for library path selection"""
    if not path:
        from api.browse_utils import get_root_dirs
        dirs = get_root_dirs()
        return StandardResponse(success=True, message="Root loaded", data={"current": "", "parent": "", "dirs": dirs})

    if not os.path.isdir(path):
        return StandardResponse(success=False, message="Invalid directory path")

    try:
        is_root = (os.path.abspath(path) == '/' or os.path.abspath(path) == os.path.abspath('/'))
        from api.browse_utils import _SYSTEM_DIRS

        subdirs = sorted([
            d for d in os.listdir(path)
            if os.path.isdir(os.path.join(path, d)) 
            and not d.startswith('.')
            and not (is_root and d in _SYSTEM_DIRS)
        ], key=lambda x: x.lower())
    except (PermissionError, OSError):
        subdirs = []

    parent = os.path.dirname(path)
    return StandardResponse(success=True, message="Directory loaded", data={"current": path, "parent": parent, "dirs": subdirs})


@router.post("/{library_id}/update-styles", response_model=StandardResponse)
def trigger_library_style_update(library_id: str):
    """Trigger a background task to update styles for all subtitles in a library"""
    cm = get_config_manager()
    config = cm.load()
    
    lib = next((l for l in config.libraries if l.id == library_id), None)
    if not lib:
        return StandardResponse(success=False, message="Library not found")
        
    from database.task_dao import TaskDAO
    import json
    
    params = json.dumps({"action": "update_style"})
    success, msg = TaskDAO.add_task(lib.path, params)
    
    if not success:
        return StandardResponse(success=False, message=msg)
        
    return StandardResponse(success=True, message=f"Style update task queued for library '{lib.name}'")


@router.get("/media-stats", response_model=StandardResponse)
def get_media_stats():
    """Get global media subtitle statistics"""
    from database.media_dao import MediaDAO
    cm = get_config_manager()
    config = cm.load()
    
    target_langs = []
    if getattr(config, 'translation', None) and getattr(config.translation, 'enabled', False):
        target_langs = [task.target_language for task in config.translation.tasks]
        
    stats = MediaDAO.get_library_subtitle_stats(target_langs, config.libraries)
    return StandardResponse(success=True, message="Stats loaded", data=stats)
