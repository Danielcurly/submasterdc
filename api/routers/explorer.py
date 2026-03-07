import os
from pathlib import Path
from fastapi import APIRouter
from core.models import SUPPORTED_VIDEO_EXTENSIONS, StandardResponse
from api.deps import get_config_manager

router = APIRouter()

@router.get("", response_model=StandardResponse)
def list_directory(path: str = ""):
    """
    List contents of a directory.
    Allows generic browsing of the filesystem.
    """
    if not path:
        # If no path given, show available mount points / root dirs
        results = []
        from api.browse_utils import get_root_dirs
        for d in get_root_dirs():
            results.append({
                "name": os.path.basename(d) or d,
                "path": d,
                "type": "directory",
                "size": None
            })
        return StandardResponse(success=True, message="Volumes loaded", data={"current_path": "Available Volumes", "contents": results})

    target_abs = os.path.abspath(path)
    target = Path(target_abs)
    
    if not target.exists():
        return StandardResponse(success=False, message=f"Path '{path}' does not exist", data=[])
        
    if not target.is_dir():
        return StandardResponse(success=False, message=f"Path '{path}' is not a directory", data=[])
        
    results = []
    
    # Parental traversal logic
    try:
        parent_abs = os.path.abspath(target.parent)
        # Avoid going above system root (e.g., above '/' in linux or 'C:\' in windows)
        if target_abs != parent_abs:
            results.append({
                "name": "..",
                "path": parent_abs,
                "type": "directory",
                "size": None
            })
    except Exception:
        pass

    try:
        is_root = (target_abs == '/' or target_abs == os.path.abspath('/'))
        from api.browse_utils import _SYSTEM_DIRS

        for entry in os.scandir(str(target)):
            if entry.name.startswith('.'):
                continue
            
            if is_root and entry.name in _SYSTEM_DIRS:
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
        return StandardResponse(success=False, message="Permission denied to read this directory", data=[])
    except Exception as e:
        return StandardResponse(success=False, message=f"Error reading directory: {e}", data=[])
        
    # Sort: folders first, then files alphabetically
    results = sorted(results, key=lambda x: (
        0 if x['name'] == '..' else 1, 
        0 if x['type'] == 'directory' else 1, 
        x['name'].lower()
    ))
    
    return StandardResponse(
        success=True,
        message="Directory loaded",
        data={
            "current_path": str(target),
            "contents": results
        }
    )
