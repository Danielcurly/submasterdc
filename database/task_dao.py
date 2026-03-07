#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task Data Access Object (DAO)
Responsible for task-related database operations
"""

import sqlite3
from typing import List, Optional, Tuple

from database.connection import get_db_connection
from core.models import Task, TaskStatus


class TaskDAO:
    """Task Data Access Object"""
    
    @staticmethod
    def add_task(file_path: str, params: Optional[str] = None, force_failed_retry: bool = False, is_manual: bool = False) -> Tuple[bool, str]:
        """
        Add a new task
        
        Args:
            file_path: File path
            params: Optional manual task parameters as JSON string
            force_failed_retry: Whether to force re-queuing of failed/cancelled tasks
            is_manual: Whether the task was explicitly added by the user manually
        
        Returns:
            (Success flag, Message)
        """
        conn = get_db_connection()
        try:
            # Check if task already exists
            cursor = conn.execute("SELECT id, status, params FROM tasks WHERE file_path = ?", (file_path,))
            result = cursor.fetchone()
            
            if result:
                task_id, status, stored_params = result
                if status == 'processing':
                    return False, "Task is already being processed"
                
                if status in ('completed', 'skipped'):
                    # Style updates must always be re-runnable
                    is_style_update = False
                    if params:
                        try:
                            import json as _json
                            is_style_update = _json.loads(params).get('action') == 'update_style'
                        except: pass
                    
                    # If config hasn't changed since last run AND it's not a manual task, skip silently
                    if not is_manual and (stored_params == params) and not is_style_update:
                        return False, "Task already processed"
                        
                    # Config changed, style update, or explicit manual generation — re-evaluate this file
                    conn.execute(
                        "UPDATE tasks SET status = 'pending', progress = 0, log = 'Re-queuing (manual or config changed)...', "
                        "params = ?, hidden = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (params, task_id)
                    )
                    conn.commit()
                    try:
                        from core.worker import trigger_worker_event
                        trigger_worker_event()
                    except ImportError:
                        pass
                    return True, "Task re-queued"
                
                if status in ('failed', 'cancelled', 'quota_exhausted') and not force_failed_retry:
                    # Don't re-queue failed tasks during automatic scans
                    return False, f"Task is {status}, skipping automatic re-queuing"
                
                # Update existing task to pending
                conn.execute(
                    "UPDATE tasks SET status = 'pending', progress = 0, log = 'Preparing (Rescan)...', "
                    "params = ?, hidden = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (params, task_id)
                )
                conn.commit()
                try:
                    from core.worker import trigger_worker_event
                    trigger_worker_event()
                except ImportError:
                    pass
                return True, "Task updated to pending"
            
            # Create new task
            conn.execute(
                "INSERT INTO tasks (file_path, status, log, params) VALUES (?, 'pending', 'Preparing...', ?)",
                (file_path, params)
            )
            conn.commit()
            try:
                from core.worker import trigger_worker_event
                trigger_worker_event()
            except ImportError:
                pass
            return True, "Task added"
        except Exception as e:
            print(f"[TaskDAO] Failed to add task: {e}")
            return False, f"Failed to add: {str(e)}"
        finally:
            conn.close()

    @staticmethod
    def cancel_task(task_id: int) -> bool:
        """
        Cancel a pending or processing task
        
        Args:
            task_id: Task ID
            
        Returns:
            Success flag
        """
        conn = get_db_connection()
        try:
            cursor = conn.execute(
                "SELECT status FROM tasks WHERE id=?", (task_id,)
            )
            result = cursor.fetchone()
            if not result:
                return False
                
            status = result[0]
            if status not in ['pending', 'processing']:
                return False
                
            conn.execute(
                "UPDATE tasks SET status='cancelled', log='Task cancelled by user', updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (task_id,)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[TaskDAO] Failed to cancel task {task_id}: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def cancel_task_by_path(file_path: str) -> bool:
        """
        Cancel a pending task by file path (used when a file is deleted).
        
        Args:
            file_path: Path of the file whose task should be cancelled
            
        Returns:
            Success flag
        """
        conn = get_db_connection()
        try:
            cursor = conn.execute(
                "UPDATE tasks SET status='cancelled', log='File deleted', updated_at=CURRENT_TIMESTAMP "
                "WHERE file_path=? AND status IN ('pending', 'processing')",
                (file_path,)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[TaskDAO] Failed to cancel task for path {file_path}: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def cancel_all_tasks() -> int:
        """
        Cancel all pending and processing tasks
        
        Returns:
            Number of tasks cancelled
        """
        conn = get_db_connection()
        try:
            cursor = conn.execute(
                "UPDATE tasks SET status='cancelled', log='Task cancelled by user', updated_at=CURRENT_TIMESTAMP WHERE status IN ('pending', 'processing')"
            )
            count = cursor.rowcount
            conn.commit()
            return count
        except Exception as e:
            print(f"[TaskDAO] Failed to cancel all tasks: {e}")
            return 0
        finally:
            conn.close()
    
    @staticmethod
    def get_all_tasks() -> List[Task]:
        """
        Get all tasks
        
        Returns:
            List of tasks
        """
        conn = get_db_connection()
        try:
            cursor = conn.execute(
                "SELECT id, file_path, status, progress, log, params, created_at, updated_at "
                "FROM tasks WHERE hidden = 0 ORDER BY id DESC"
            )
            
            tasks = []
            for row in cursor.fetchall():
                try:
                    task = Task(
                        id=row[0],
                        file_path=row[1],
                        status=TaskStatus(row[2]),
                        progress=row[3],
                        log=row[4],
                        params=row[5],
                        created_at=row[6],
                        updated_at=row[7]
                    )
                    tasks.append(task)
                except Exception as e:
                    print(f"[TaskDAO] Failed to parse task {row[0]}: {e}")
                    continue
            
            return tasks
        finally:
            conn.close()
    
    @staticmethod
    def get_pending_task() -> Optional[Task]:
        """
        Get the first pending task
        
        Returns:
            Task object, or None if not found
        """
        conn = get_db_connection()
        try:
            result = conn.execute(
                "SELECT id, file_path, status, progress, log, params, created_at, updated_at "
                "FROM tasks WHERE status='pending' AND hidden=0 LIMIT 1"
            ).fetchone()
            
            if not result:
                return None
            
            return Task(
                id=result[0],
                file_path=result[1],
                status=TaskStatus(result[2]),
                progress=result[3],
                log=result[4],
                params=result[5],
                created_at=result[6],
                updated_at=result[7]
            )
        finally:
            conn.close()
    
    @staticmethod
    def get_task_by_id(task_id: int) -> Optional[Task]:
        """
        Get task by ID
        
        Args:
            task_id: Task ID
        
        Returns:
            Task object, or None if not found
        """
        conn = get_db_connection()
        try:
            result = conn.execute(
                "SELECT id, file_path, status, progress, log, params, created_at, updated_at "
                "FROM tasks WHERE id=?",
                (task_id,)
            ).fetchone()
            
            if not result:
                return None
            
            return Task(
                id=result[0],
                file_path=result[1],
                status=TaskStatus(result[2]),
                progress=result[3],
                log=result[4],
                params=result[5],
                created_at=result[6],
                updated_at=result[7]
            )
        finally:
            conn.close()
    
    @staticmethod
    def update_task(
        task_id: int,
        status: Optional[TaskStatus] = None,
        progress: Optional[int] = None,
        log: Optional[str] = None
    ):
        """
        Update task status
        
        Args:
            task_id: Task ID
            status: New status (optional)
            progress: Progress (optional)
            log: Log message (optional)
        """
        conn = get_db_connection()
        try:
            # Guard: never overwrite a cancelled task
            if status is not None:
                current = conn.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
                if current and current[0] == 'cancelled':
                    # Only allow log updates on cancelled tasks, ignore status/progress changes
                    if log is not None:
                        conn.execute("UPDATE tasks SET log=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (log, task_id))
                        conn.commit()
                    return
            
            updates = []
            params = []
            
            if status is not None:
                updates.append("status=?")
                params.append(status.value if isinstance(status, TaskStatus) else status)
            
            if progress is not None:
                updates.append("progress=?")
                params.append(progress)
            
            if log is not None:
                updates.append("log=?")
                params.append(log)
            
            if not updates:
                return
            
            updates.append("updated_at=CURRENT_TIMESTAMP")
            params.append(task_id)
            
            query = f"UPDATE tasks SET {','.join(updates)} WHERE id=?"
            conn.execute(query, params)
            conn.commit()
            
        except Exception as e:
            print(f"[TaskDAO] Failed to update task {task_id}: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    @staticmethod
    def delete_task(task_id: int):
        """
        Delete task
        
        Args:
            task_id: Task ID
        """
        conn = get_db_connection()
        try:
            conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
            conn.commit()
        except Exception as e:
            print(f"[TaskDAO] Failed to delete task {task_id}: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    @staticmethod
    def clear_completed_tasks():
        """Hide all finished tasks and cancel all pending tasks.
        Only the currently processing task (if any) remains visible and active."""
        conn = get_db_connection()
        try:
            # First, cancel all pending tasks so they don't execute without visual feedback
            conn.execute(
                "UPDATE tasks SET status = 'cancelled', log = 'Cancelled (queue cleared)', "
                "hidden = 1, updated_at = CURRENT_TIMESTAMP WHERE status = 'pending'"
            )
            # Then hide all other finished tasks
            conn.execute(
                "UPDATE tasks SET hidden = 1 WHERE status IN ('completed', 'failed', 'skipped', 'cancelled', 'quota_exhausted', 'permission_error')"
            )
            conn.commit()
        except Exception as e:
            print(f"[TaskDAO] Failed to clear completed tasks: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    @staticmethod
    def reset_task(task_id: int):
        """
        Reset task to pending state
        
        Args:
            task_id: Task ID
        """
        conn = get_db_connection()
        try:
            conn.execute(
                "UPDATE tasks SET status='pending', progress=0, log='Retrying...', "
                "updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (task_id,)
            )
            conn.commit()
        except Exception as e:
            print(f"[TaskDAO] Failed to reset task {task_id}: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    @staticmethod
    def get_task_count_by_status(status: TaskStatus) -> int:
        """
        Get number of tasks with a specific status
        
        Args:
            status: Task status
        
        Returns:
            Number of tasks
        """
        conn = get_db_connection()
        try:
            result = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE status=? AND hidden=0",
                (status.value,)
            ).fetchone()
            return result[0] if result else 0
        finally:
            conn.close()
    
    @staticmethod
    def count_processed_files() -> int:
        """
        Count the number of unique media files that have been processed successfully.
        A file is considered processed if its most recent task was 'completed' or 'skipped'
        (meaning it met all requirements or subtitles were successfully generated).
        
        Returns:
            Number of unique fully processed media files.
        """
        conn = get_db_connection()
        try:
            # We count unique file paths that have at least one task in completed/skipped
            # AND which hasn't been hidden (cleared) by the user in the UI.
            result = conn.execute(
                "SELECT COUNT(DISTINCT file_path) FROM tasks WHERE status IN ('completed', 'skipped') AND hidden=0"
            ).fetchone()
            return result[0] if result else 0
        except Exception as e:
            print(f"[TaskDAO] Failed to count processed files: {e}")
            return 0
        finally:
            conn.close()
            
    @staticmethod
    def has_processing_task() -> bool:
        """
        Check if there are any tasks currently being processed
        
        Returns:
            bool: True if there are processing tasks
        """
        count = TaskDAO.get_task_count_by_status(TaskStatus.PROCESSING)
        return count > 0

    @staticmethod
    def reset_stuck_processing_tasks() -> int:
        """
        Reset tasks that are stuck in 'processing' state (e.g., after an unexpected shutdown)
        back to 'pending' so they can be picked up again by the worker.
        
        Returns:
            Number of tasks reset.
        """
        conn = get_db_connection()
        try:
            cursor = conn.execute(
                "UPDATE tasks SET status = 'pending', progress = 0, log = 'Reset after unexpected shutdown', updated_at = CURRENT_TIMESTAMP WHERE status = 'processing'"
            )
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            conn.rollback()
            print(f"[TaskDAO] Failed to reset stuck processing tasks: {e}")
            return 0
        finally:
            conn.close()