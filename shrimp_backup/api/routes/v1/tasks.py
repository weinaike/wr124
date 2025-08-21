"""Task endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId

from shrimp.models import Task, TaskCreate, TaskUpdate, TodoItem
from shrimp.services.task_service import TaskService
from shrimp.api.dependencies import get_task_service, get_current_project
from shrimp.api.utils import handle_service_response
from fastapi import Request

router = APIRouter()


@router.post("/{project_id}/tasks", response_model=Task)
async def create_task(
    project_id: str,
    task: TaskCreate,
    task_service: TaskService = Depends(get_task_service),
    current_project: str = Depends(get_current_project)
):
    """Create a new task."""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    response = await task_service.create_task(project_id, task)
    return handle_service_response(response)


@router.post("/{project_id}/tasks/bulk_create")
async def bulk_create_tasks(
    project_id: str,
    tasks: List[TaskCreate],
    task_service: TaskService = Depends(get_task_service),
    current_project: str = Depends(get_current_project)
):
    """Bulk create tasks."""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    response = await task_service.bulk_create_tasks(project_id, tasks)
    return handle_service_response(response)


@router.get("/{project_id}/tasks", response_model=List[Task])
async def list_tasks(
    project_id: str,
    status: Optional[str] = Query(None, description="任务状态过滤"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    task_service: TaskService = Depends(get_task_service),
    current_project: str = Depends(get_current_project)
):
    """List tasks with filtering."""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    response = await task_service.list_tasks(project_id, status, skip, limit)
    return handle_service_response(response)


@router.get("/{project_id}/tasks/{task_id}", response_model=Task)
async def get_task(
    project_id: str,
    task_id: str,
    task_service: TaskService = Depends(get_task_service),
    current_project: str = Depends(get_current_project)
):
    """Get a specific task."""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    response = await task_service.get_task(project_id, task_id)
    return handle_service_response(response)


@router.patch("/{project_id}/tasks/{task_id}", response_model=Task)
async def update_task(
    project_id: str,
    task_id: str,
    task: TaskUpdate,
    if_match: Optional[str] = Query(None, description="乐观锁版本检查"),
    task_service: TaskService = Depends(get_task_service),
    current_project: str = Depends(get_current_project)
):
    """Update a task with optimistic locking."""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    response = await task_service.update_task(project_id, task_id, task, if_match)
    return handle_service_response(response)


@router.delete("/{project_id}/tasks/{task_id}")
async def delete_task(
    project_id: str,
    task_id: str,
    task_service: TaskService = Depends(get_task_service),
    current_project: str = Depends(get_current_project)
):
    """Delete a task (soft delete)."""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    response = await task_service.delete_task(project_id, task_id)
    if response.success:
        return {"message": response.message or "Task deleted successfully"}
    else:
        raise HTTPException(
            status_code=response.code,
            detail=response.error or "Failed to delete task"
        )


@router.get("/projects")
async def get_projects():
    """Get all unique project IDs from tasks and versions."""
    from shrimp.db.database import db_manager
    if db_manager.database is None:
        await db_manager.connect_to_mongo()
    db = db_manager.database
    
    try:
        # Get projects from tasks
        task_projects = await db.tasks.distinct("project_id", {"deleted_at": None})
        # Get projects from versions as fallback
        version_projects = await db.task_versions.distinct("project_id")
        
        # Combine and deduplicate
        all_projects = list(set(task_projects + version_projects))
        
        return {
            "projects": all_projects,
            "count": len(all_projects)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve projects: {str(e)}"
        )


@router.get("/project/{project_id}/info")
async def get_project_info(project_id: str):
    """Get detailed information about a specific project."""
    task_service = TaskService()
    
    try:
        stats = await task_service.get_task_statistics(project_id)
        if not stats.success:
            raise HTTPException(
                status_code=404,
                detail=f"Project {project_id} not found"
            )
        
        return {
            "project_id": project_id,
            "statistics": stats.data
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve project info: {str(e)}"
        )


@router.delete("/project/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and all its associated data."""
    task_service = TaskService()
    
    try:
        # Delete all tasks for this project
        delete_response = await task_service.delete_project_tasks(project_id)
        
        if not delete_response.success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete project tasks: {delete_response.message}"
            )
        
        return {
            "success": True,
            "message": f"Project {project_id} and all associated data have been deleted",
            "deleted_tasks": delete_response.data.get("deleted_tasks", 0),
            "deleted_versions": delete_response.data.get("deleted_versions", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete project: {str(e)}"
        )


@router.get("/{project_id}/tasks/{task_id}/todos")
async def get_todos(
    project_id: str,
    task_id: str,
    task_service: TaskService = Depends(get_task_service),
    current_project: str = Depends(get_current_project)
):
    """Get todos for a specific task."""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    response = await task_service.get_todos(project_id, task_id)
    return handle_service_response(response)


@router.put("/{project_id}/tasks/{task_id}/todos")
async def set_todos(
    project_id: str,
    task_id: str,
    todos: List[TodoItem],
    task_service: TaskService = Depends(get_task_service),
    current_project: str = Depends(get_current_project)
):
    """Set todos for a specific task."""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    response = await task_service.set_todos(project_id, task_id, todos, notes="Updated todos via API")
    return handle_service_response(response)