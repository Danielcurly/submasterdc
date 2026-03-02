import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from core.models import SUPPORTED_VIDEO_EXTENSIONS
from core.config import ConfigManager
from database.connection import get_db_connection

router = APIRouter()

@router.get("")
def list_directory(path: str = ""):
    """
    List contents of a directory.
    Limited to paths within configured libraries.
    """
    mgr = ConfigManager(get_db_connection)
    config = mgr.load()
    allowed_roots = [os.path.abspath(lib.path) for lib in config.libraries]
    
    if not path:
        # If no path given, list the library roots themselves
        results = []
        for lib in config.libraries:
            results.append({
                "name": lib.name,
                "path": os.path.abspath(lib.path),
                "type": "directory",
                "size": None
            })
        return {"current_path": "Mapped Units", "contents": results}

    target_abs = os.path.abspath(path)
    
    # Check if target is equal to or under an allowed root
    is_allowed = False
    for root in allowed_roots:
        if target_abs == root or target_abs.startswith(root + os.sep):
            is_allowed = True
            break
            
    if not is_allowed:
        raise HTTPException(status_code=403, detail="Access denied: path is outside mapped units")

    target = Path(target_abs)
    
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path '{path}' does not exist")
        
    if not target.is_dir():
        raise HTTPException(status_code=400, detail=f"Path '{path}' is not a directory")
        
    results = []
    
    # Parental traversal logic
    try:
        parent_abs = os.path.abspath(target.parent)
        is_parent_allowed = False
        for root in allowed_roots:
            if parent_abs == root or parent_abs.startswith(root + os.sep):
                is_parent_allowed = True
                break
        
        if is_parent_allowed and target_abs not in allowed_roots:
            results.append({
                "name": "..",
                "path": parent_abs,
                "type": "directory",
                "size": None
            })
    except Exception:
        pass

    try:
        for entry in os.scandir(str(target)):
            if entry.name.startswith('.'):
                continue
                
            is_dir = entry.is_dir()
            
            if is_dir:
                results.append({
                    "name": entry.name,
                    "path": entry.path,
                    "type": "directory",
                    "size": None
                })
            elif entry.is_file():
                ext = Path(entry.name).suffix.lower()
                if ext in SUPPORTED_VIDEO_EXTENSIONS:
                    results.append({
                        "name": entry.name,
                        "path": entry.path,
                        "type": "file",
                        "size": entry.stat().st_size
                    })
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied to read this directory")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading directory: {e}")
        
    # Sort: folders first, then files alphabetically
    results = sorted(results, key=lambda x: (
        0 if x['name'] == '..' else 1, 
        0 if x['type'] == 'directory' else 1, 
        x['name'].lower()
    ))
    
    return {
        "current_path": str(target),
        "contents": results
    }
