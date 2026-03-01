"""Scan API Router — Trigger media library scanning"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.media_scanner import scan_media_directory

router = APIRouter()


class ScanRequest(BaseModel):
    library_path: str
    debug: bool = False


@router.post("")
def trigger_scan(body: ScanRequest):
    """Trigger a scan on a specific library path"""
    try:
        count, logs = scan_media_directory(directory=body.library_path, debug=body.debug)
        return {
            "files_added": count,
            "logs": logs if body.debug else [],
            "message": f"Added {count} new media files" if count > 0 else "No new media found"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
