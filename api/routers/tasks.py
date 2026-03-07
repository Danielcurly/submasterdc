"""Tasks API Router — Task queue management"""

from fastapi import APIRouter
from database.task_dao import TaskDAO
from core.models import TaskStatus, StandardResponse

router = APIRouter()


@router.get("", response_model=StandardResponse)
def list_tasks():
    """List all tasks"""
    tasks = TaskDAO.get_all_tasks()
    return StandardResponse(success=True, message="Tasks loaded", data=[t.to_dict() for t in tasks])


from pydantic import BaseModel
from typing import Optional

class AddTaskRequest(BaseModel):
    file_path: str
    params: Optional[str] = None

@router.post("", response_model=StandardResponse)
def add_task(req: AddTaskRequest):
    """Add a new task manually"""
    try:
        success, msg = TaskDAO.add_task(req.file_path, req.params, force_failed_retry=True, is_manual=True)
        if not success:
            return StandardResponse(success=False, message=msg)
        from core.worker import trigger_worker
        trigger_worker()
        return StandardResponse(success=True, message="Task added cleanly", data={"file_path": req.file_path})
    except Exception as e:
        return StandardResponse(success=False, message=str(e))


@router.post("/{task_id}/cancel", response_model=StandardResponse)
def cancel_task_api(task_id: int):
    """Cancel a pending or processing task"""
    task = TaskDAO.get_task_by_id(task_id)
    if not task:
        return StandardResponse(success=False, message="Task not found")
    success = TaskDAO.cancel_task(task_id)
    if not success:
        return StandardResponse(success=False, message="Only pending or processing tasks can be cancelled")
    return StandardResponse(success=True, message="Task cancelled successfully")

@router.post("/cancel_all", response_model=StandardResponse)
def cancel_all_tasks_api():
    """Cancel all active tasks"""
    count = TaskDAO.cancel_all_tasks()
    return StandardResponse(success=True, message=f"{count} tasks cancelled")

@router.delete("/completed", response_model=StandardResponse)
def clear_completed():
    """Clear all completed and failed tasks"""
    TaskDAO.clear_completed_tasks()
    return StandardResponse(success=True, message="Completed tasks cleared")


@router.post("/{task_id}/retry", response_model=StandardResponse)
def retry_task(task_id: int):
    """Retry a failed, cancelled or skipped task by resetting it to pending"""
    task = TaskDAO.get_task_by_id(task_id)
    if not task:
        return StandardResponse(success=False, message="Task not found")
    TaskDAO.reset_task(task_id)
    from core.worker import trigger_worker
    trigger_worker()
    return StandardResponse(success=True, message="Task reset to pending")


@router.get("/stats", response_model=StandardResponse)
def task_stats():
    """Get task count by status"""
    data = {
        "pending": TaskDAO.get_task_count_by_status(TaskStatus.PENDING),
        "processing": TaskDAO.get_task_count_by_status(TaskStatus.PROCESSING),
        "completed": TaskDAO.count_processed_files(),
        "failed": TaskDAO.get_task_count_by_status(TaskStatus.FAILED),
        "skipped": TaskDAO.get_task_count_by_status(TaskStatus.SKIPPED),
        "cancelled": TaskDAO.get_task_count_by_status(TaskStatus.CANCELLED),
        "quota_exhausted": TaskDAO.get_task_count_by_status(TaskStatus.QUOTA_EXHAUSTED),
        "permission_error": TaskDAO.get_task_count_by_status(TaskStatus.PERMISSION_ERROR),
    }
    return StandardResponse(success=True, message="Stats loaded", data=data)
