"""Memory endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from shrimp.models import Memory, MemoryCreate, MemoryUpdate
from shrimp.services.memory_service import MemoryService
from shrimp.api.dependencies import get_memory_service, get_current_project

router = APIRouter()


@router.post("/{project_id}/memories", response_model=Memory)
async def create_memory(
    project_id: str,
    memory: MemoryCreate,
    memory_service: MemoryService = Depends(get_memory_service),
    current_project: str = Depends(get_current_project)
):
    """Create a new memory."""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
        
    return await memory_service.create_memory(project_id, memory)


@router.get("/{project_id}/memories", response_model=List[Memory])
async def list_memories(
    project_id: str,
    task_id: Optional[str] = Query(None, description="关联任务ID"),
    tags: Optional[str] = Query(None, description="逗号分隔的标签列表"),
    q: Optional[str] = Query(None, description="搜索关键词"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    memory_service: MemoryService = Depends(get_memory_service),
    current_project: str = Depends(get_current_project)
):
    """List memories with filtering."""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    tag_list = tags.split(",") if tags else None
    return await memory_service.list_memories(
        project_id, task_id, tag_list, q, skip, limit
    )


@router.get("/{project_id}/memories/{memory_id}", response_model=Memory)
async def get_memory(
    project_id: str,
    memory_id: str,
    memory_service: MemoryService = Depends(get_memory_service),
    current_project: str = Depends(get_current_project)
):
    """Get a specific memory."""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
        
    return await memory_service.get_memory(project_id, memory_id)


@router.patch("/{project_id}/memories/{memory_id}", response_model=Memory)
async def update_memory(
    project_id: str,
    memory_id: str,
    memory: MemoryUpdate,
    memory_service: MemoryService = Depends(get_memory_service),
    current_project: str = Depends(get_current_project)
):
    """Update a memory."""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
        
    return await memory_service.update_memory(project_id, memory_id, memory)


@router.delete("/{project_id}/memories/{memory_id}")
async def delete_memory(
    project_id: str,
    memory_id: str,
    memory_service: MemoryService = Depends(get_memory_service),
    current_project: str = Depends(get_current_project)
):
    """Delete a memory."""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
        
    success = await memory_service.delete_memory(project_id, memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"message": "Memory deleted successfully"}