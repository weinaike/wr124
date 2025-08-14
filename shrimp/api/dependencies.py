"""API dependencies provider."""

from typing import Optional
from fastapi import Depends, HTTPException, Header
from shrimp.services.task_service import TaskService
from shrimp.services.memory_service import MemoryService
from shrimp.services.version_service import VersionService
from shrimp.db.database import MCPDatabase
from typing import Annotated
from fastapi import Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

async def get_task_db():
    """Get database connection with auto-connect for task service."""
    from shrimp.db.database import db_manager
    if db_manager.database is None:
        await db_manager.connect_to_mongo()
    return db_manager.database


async def get_memory_db():
    """Get database connection with auto-connect for memory service."""
    from shrimp.db.database import db_manager
    if db_manager.database is None:
        await db_manager.connect_to_mongo()
    return db_manager.database


async def get_version_db():
    """Get database connection with auto-connect for version service."""
    from shrimp.db.database import db_manager
    if db_manager.database is None:
        await db_manager.connect_to_mongo()
    return db_manager.database


TaskDB = Annotated[MCPDatabase, Depends(get_task_db)]
MemoryDB = Annotated[MCPDatabase, Depends(get_memory_db)]
VersionDB = Annotated[MCPDatabase, Depends(get_version_db)]


async def get_task_service(db: TaskDB) -> TaskService:
    """Get task service with auto-connected database."""
    return TaskService(db)


async def get_memory_service(db: MemoryDB) -> MemoryService:
    """Get memory service with auto-connected database."""
    return MemoryService(db)


async def get_version_service(db: VersionDB) -> VersionService:
    """Get version service with auto-connected database."""
    return VersionService(db)


async def get_current_project(
    x_project_id: Optional[str] = Header(None),
) -> str:
    """Get the current project ID from header."""
    if not x_project_id:
        raise HTTPException(status_code=400, detail="X-Project-ID header is required")
    return x_project_id