"""Debug API Router — Manage and view application logs"""

import os
from fastapi import APIRouter, Query
from core.logger import LOG_FILE, app_logger
from core.models import StandardResponse

router = APIRouter()

@router.get("/logs", response_model=StandardResponse)
def get_logs(lines: int = Query(100, ge=1, le=5000)):
    """Fetch the last N lines of the debug log"""
    if not LOG_FILE.exists():
        return StandardResponse(success=True, message="Log file does not exist yet", data={"logs": []})
    
    try:
        import collections
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            # Memory efficient way to get total lines and last N lines
            total_lines = sum(1 for _ in f)
            f.seek(0)
            last_lines = list(collections.deque(f, maxlen=lines))
            return StandardResponse(success=True, message="Logs loaded", data={
                "logs": [line.strip() for line in last_lines],
                "total_lines": total_lines,
                "returned_lines": len(last_lines)
            })
    except Exception as e:
        app_logger.error(f"[DebugAPI] Failed to read log file: {e}")
        return StandardResponse(success=False, message=str(e), data={"logs": []})

@router.delete("/logs", response_model=StandardResponse)
def clear_logs_endpoint():
    """Clear the content of the debug log file"""
    try:
        from core.logger import clear_logs as safe_clear_logs
        safe_clear_logs()
        return StandardResponse(success=True, message="Logs cleared successfully")
    except Exception as e:
        app_logger.error(f"[DebugAPI] Failed to clear log file: {e}")
        return StandardResponse(success=False, message=str(e))
