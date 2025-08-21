"""Versioning endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException

from shrimp.models import TaskVersion
from shrimp.services.version_service import VersionService
from shrimp.api.dependencies import get_version_service, get_current_project

router = APIRouter()


@router.get("/{project_id}/tasks/{task_id}/versions", response_model=List[TaskVersion])
async def get_task_versions(
    project_id: str,
    task_id: str,
    skip: int = 0,
    limit: int = 100,
    version_service: VersionService = Depends(get_version_service),
    current_project: str = Depends(get_current_project)
):
    """Get all versions for a task."""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
        
    return await version_service.get_task_versions(
        project_id, task_id, skip, limit
    )


@router.post("/{project_id}/tasks/{task_id}/revert", response_model=dict)
async def revert_task_version(
    project_id: str,
    task_id: str,
    version_id: str,
    version_service: VersionService = Depends(get_version_service),
    current_project: str = Depends(get_current_project)
):
    """Revert a task to a specific version."""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
        
    task = await version_service.revert_task_version(
        project_id, task_id, version_id
    )
    if not task:
        raise HTTPException(status_code=404, detail="Version or task not found")
    return {"task_id": task_id, "version_id": version_id, "reverted_to": version_id}