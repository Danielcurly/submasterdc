"""Explorer API Router — Allows traversing the system to select files"""

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter()

SUPPORTED_VIDEO_EXTS = {'.mp4', '.mkv', '.avi', '.mov', '.ts', '.flv', '.webm', '.m4v', '.wmv'}

@router.get("")
def list_directory(path: str = "/"):
    """
    List contents of a directory.
    Returns directories and supported video files.
    """
    target = Path(path)
    
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path '{path}' does not exist")
        
    if not target.is_dir():
        raise HTTPException(status_code=400, detail=f"Path '{path}' is not a directory")
        
    results = []
    
    # Try resolving parent
    try:
        parent = target.parent
        # Add a special entry to go up
        if target != parent:
            results.append({
                "name": "..",
                "path": str(parent),
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
                if ext in SUPPORTED_VIDEO_EXTS:
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
