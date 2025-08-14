"""Version service for managing task versions."""

from typing import List, Optional, cast, TYPE_CHECKING
from datetime import datetime, timezone
from bson import ObjectId, errors as bson_errors

from shrimp.models.version import TaskVersion
from shrimp.models.task import Task
from shrimp.db.database import get_database, MCPDatabase

if TYPE_CHECKING:
    from .task_service import TaskService


class VersionService:
    """Service for managing task versions."""
    
    def __init__(self, database: Optional[MCPDatabase] = None, task_service: Optional['TaskService'] = None):
        self.db: MCPDatabase = database if database is not None else cast(MCPDatabase, get_database())
        # Use provided task_service or lazy load to avoid circular import
        self._task_service = task_service
        self._task_service_initialized = False
    
    @property
    def task_service(self):
        """Lazy load task service to avoid circular imports."""
        if not self._task_service_initialized:
            if self._task_service is None:
                from .task_service import TaskService
                self._task_service = TaskService(self.db)
            self._task_service_initialized = True
        return self._task_service
    
    async def create_version(
        self,
        project_id: str,
        task_id: str,
        operation: str,
        changed_by: str,
        message: str = None
    ) -> Optional[TaskVersion]:
        """Create a new task version."""
        try:
            # Get current task
            task_response = await self.task_service.get_task(project_id, task_id)
            if not task_response.success or not task_response.data:
                return None
            
            task = task_response.data
            
            # Create version
            version_data = {
                "task_id": task_id,
                "project_id": project_id,
                "payload": task.model_dump(),
                "operation": operation,
                "changed_by": changed_by,
                "timestamp": datetime.now(timezone.utc),
                "message": message or f"{operation} task",
                "archived": False
            }
            
            result = await self.db.task_versions.insert_one(version_data)
            version_data["_id"] = str(result.inserted_id)
            
            # Update task's current_version_id
            await self.db.tasks.update_one(
                {"_id": ObjectId(task_id), "project_id": project_id},
                {
                    "$set": {
                        "current_version_id": str(result.inserted_id),
                        "version_number": task.version_number + 1
                    }
                }
            )
            
            return TaskVersion(**version_data)
            
        except bson_errors.InvalidId:
            return None
    
    async def get_task_versions(
        self,
        project_id: str,
        task_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[TaskVersion]:
        """Get all versions for a task."""
        try:
            # Verify task exists
            task_exists = await self.task_service.check_task_exists(project_id, task_id)
            if not task_exists:
                return []
            
            cursor = self.db.task_versions.find({
                "task_id": task_id,
                "project_id": project_id
            }).sort("timestamp", -1)
            
            versions = []
            async for version_data in cursor.skip(skip).limit(limit):
                # Ensure _id is converted to string
                version_data["_id"] = str(version_data["_id"])
                versions.append(TaskVersion(**version_data))
            
            return versions
            
        except bson_errors.InvalidId:
            return []
    
    async def revert_task_version(
        self,
        project_id: str,
        task_id: str,
        version_id: str,
        changed_by: str = "system"
    ) -> Optional[Task]:
        """Revert a task to a specific version."""
        try:
            # Get the version to revert to
            version = await self.db.task_versions.find_one({
                "_id": ObjectId(version_id),
                "task_id": task_id,
                "project_id": project_id
            })
            
            if not version:
                return None
            
            # Get the payload and create a new version
            task_data = version["payload"]
            
            # Remove _id and version-related fields
            task_data.pop("_id", None)
            task_data.pop("id", None)
            
            # Update the task with the reverted data
            updated_data = {**task_data}
            updated_data["updated_at"] = datetime.now(timezone.utc)
            
            # Remove version-related fields that would cause conflicts
            version_number = updated_data.pop("version_number", None)
            current_version_id = updated_data.pop("current_version_id", None)
            
            # Perform the update with separated $set and $inc operators
            await self.db.tasks.update_one(
                {"_id": ObjectId(task_id), "project_id": project_id},
                {
                    "$set": updated_data,
                    "$inc": {"version_number": 1}
                }
            )
            
            # Create a new version entry for the revert operation
            revert_version = await self.create_version(
                project_id=project_id,
                task_id=task_id,
                operation="rollback",
                changed_by=changed_by,
                message=f"Reverted to version {version_id}"
            )
            
            # Update task's current_version_id
            if revert_version:
                await self.db.tasks.update_one(
                    {"_id": ObjectId(task_id), "project_id": project_id},
                    {"$set": {"current_version_id": str(revert_version.id)}}
                )
            
            # Get the reverted task - handle the ServiceResponse properly
            task_response = await self.task_service.get_task(project_id, task_id)
            if task_response.success and task_response.data:
                return task_response.data
            return None
            
        except bson_errors.InvalidId:
            return None
        except Exception as e:
            # Log any other exceptions for debugging
            print(f"Error in revert_task_version: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def get_task_version(
        self,
        project_id: str,
        task_id: str,
        version_id: str
    ) -> Optional[TaskVersion]:
        """Get a specific task version."""
        try:
            version_data = await self.db.task_versions.find_one({
                "_id": ObjectId(version_id),
                "task_id": task_id,
                "project_id": project_id
            })
            if version_data:
                version_data["_id"] = str(version_data["_id"])
                return TaskVersion(**version_data)
            return None
        except bson_errors.InvalidId:
            return None