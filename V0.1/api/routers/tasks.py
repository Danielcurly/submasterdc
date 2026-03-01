"""Tasks API Router — Task queue management"""

from fastapi import APIRouter, HTTPException
from database.task_dao import TaskDAO
from core.models import TaskStatus

router = APIRouter()


@router.get("")
def list_tasks():
    """List all tasks"""
    tasks = TaskDAO.get_all_tasks()
    return [t.to_dict() for t in tasks]


from pydantic import BaseModel
from typing import Optional

class AddTaskRequest(BaseModel):
    file_path: str
    params: Optional[str] = None

@router.post("")
def add_task(req: AddTaskRequest):
    """Add a new task manually"""
    success, msg = TaskDAO.add_task(req.file_path, req.params)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": "Task added cleanly", "file_path": req.file_path}



@router.post("/{task_id}/cancel")
def cancel_task_api(task_id: int):
    """Cancel a pending or processing task"""
    task = TaskDAO.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    success = TaskDAO.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Only pending or processing tasks can be cancelled")
    return {"message": "Task cancelled successfully"}

@router.post("/cancel_all")
def cancel_all_tasks_api():
    """Cancel all active tasks"""
    count = TaskDAO.cancel_all_tasks()
    return {"message": f"{count} tasks cancelled"}

@router.delete("/completed")
def clear_completed():
    """Clear all completed and failed tasks"""
    TaskDAO.clear_completed_tasks()
    return {"message": "Completed tasks cleared"}


@router.post("/{task_id}/retry")
def retry_task(task_id: int):
    """Retry a failed task by resetting it to pending"""
    task = TaskDAO.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    TaskDAO.reset_task(task_id)
    return {"message": "Task reset to pending"}


@router.get("/stats")
def task_stats():
    """Get task count by status"""
    return {
        "pending": TaskDAO.get_task_count_by_status(TaskStatus.PENDING),
        "processing": TaskDAO.get_task_count_by_status(TaskStatus.PROCESSING),
        "completed": TaskDAO.get_task_count_by_status(TaskStatus.COMPLETED),
        "failed": TaskDAO.get_task_count_by_status(TaskStatus.FAILED),
    }
