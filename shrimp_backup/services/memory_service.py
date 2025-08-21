"""Memory service for managing memories."""

from typing import List, Optional, cast
from datetime import datetime, timezone
from bson import ObjectId, errors as bson_errors

from shrimp.models.memory import Memory, MemoryCreate, MemoryUpdate
from shrimp.db.database import get_database, MCPDatabase


class MemoryService:
    """Service for managing memories."""
    
    def __init__(self, database: Optional[MCPDatabase] = None):
        # Use structural typing so IDE knows collections on self.db
        self.db: MCPDatabase = database if database is not None else cast(MCPDatabase, get_database())
    
    async def create_memory(self, project_id: str, memory_create: MemoryCreate) -> Memory:
        """Create a new memory."""
        memory_data = {
            **memory_create.model_dump(),
            "project_id": project_id,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        # Validate task exists if task_id provided
        if memory_data.get("task_id"):
            task_exists = await self._validate_task_exists(
                project_id, memory_data["task_id"]
            )
            if not task_exists:
                raise ValueError(f"Task {memory_data['task_id']} not found")
        
        result = await self.db.memories.insert_one(memory_data)
        memory_data["_id"] = str(result.inserted_id)
        memory_data["id"] = str(result.inserted_id)
        
        return Memory(**memory_data)
    
    async def get_memory(self, project_id: str, memory_id: str) -> Optional[Memory]:
        """Get a memory by ID."""
        try:
            memory_data = await self.db.memories.find_one({
                "_id": ObjectId(memory_id),
                "project_id": project_id
            })
            if memory_data:
                memory_data["_id"] = str(memory_data["_id"])
                memory_data["id"] = str(memory_data["_id"])
            return Memory(**memory_data) if memory_data else None
        except bson_errors.InvalidId:
            return None
    
    async def list_memories(
        self,
        project_id: str,
        task_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        q: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Memory]:
        """List memories with filtering."""
        query = {"project_id": project_id}
        
        if task_id:
            query["task_id"] = task_id
        
        if tags:
            query["tags"] = {"$in": tags}
        
        # Handle text search with fallback
        if q:
            try:
                # Try text search first
                text_query = dict(query)
                text_query["$text"] = {"$search": q}
                cursor = self.db.memories.find(text_query).sort("created_at", -1)
                
                memories = []
                async for memory_data in cursor.skip(skip).limit(limit):
                    if memory_data:
                        memory_data["_id"] = str(memory_data["_id"])
                        memory_data["id"] = str(memory_data["_id"])
                        memories.append(Memory(**memory_data))
                
                return memories
                
            except Exception:
                # Fallback to regex search if text index is not available
                regex_query = dict(query)
                regex_query["$or"] = [
                    {"raw_text": {"$regex": q, "$options": "i"}},
                    {"title": {"$regex": q, "$options": "i"}}
                ]
                cursor = self.db.memories.find(regex_query).sort("created_at", -1)
        else:
            cursor = self.db.memories.find(query).sort("created_at", -1)
        
        memories = []
        async for memory_data in cursor.skip(skip).limit(limit):
            if memory_data:
                memory_data["_id"] = str(memory_data["_id"])
                memory_data["id"] = str(memory_data["_id"])
                memories.append(Memory(**memory_data))
        
        return memories
    
    async def update_memory(
        self,
        project_id: str,
        memory_id: str,
        memory_update: MemoryUpdate
    ) -> Optional[Memory]:
        """Update a memory."""
        try:
            update_data = memory_update.model_dump(exclude_unset=True)
            update_data["updated_at"] = datetime.now(timezone.utc)
            
            # Validate task exists if task_id is being updated
            if "task_id" in update_data:
                task_exists = await self._validate_task_exists(
                    project_id, update_data["task_id"]
                )
                if not task_exists:
                    raise ValueError(f"Task {update_data['task_id']} not found")
            
            result = await self.db.memories.update_one(
                {
                    "_id": ObjectId(memory_id),
                    "project_id": project_id
                },
                {"$set": update_data}
            )
            
            if result.modified_count == 0:
                return None
            
            return await self.get_memory(project_id, memory_id)
            
        except bson_errors.InvalidId:
            return None
    
    async def delete_memory(
        self,
        project_id: str,
        memory_id: str
    ) -> bool:
        """Delete a memory."""
        try:
            result = await self.db.memories.delete_one({
                "_id": ObjectId(memory_id),
                "project_id": project_id
            })
            return result.deleted_count > 0
        except bson_errors.InvalidId:
            return False
    
    async def _validate_task_exists(self, project_id: str, task_id: str) -> bool:
        """Validate that a task exists."""
        try:
            count = await self.db.tasks.count_documents({
                "_id": ObjectId(task_id),
                "project_id": project_id,
                "deleted_at": None
            })
            return count > 0
        except bson_errors.InvalidId:
            return False