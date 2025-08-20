"""Refactored Task service for business logic."""

import json
from typing import List, Optional, Dict, Any, cast, Union
from datetime import datetime, timezone
from enum import Enum
from bson import ObjectId, errors as bson_errors

from shrimp.models.task import Task, TaskCreate, TaskUpdate, TaskStatus, TodoItem
from shrimp.db.database import get_database, MCPDatabase
from shrimp.core.response import ServiceResponse, ValidationResult
from shrimp.core.validators import TaskValidator
from .version_service import VersionService


class UpdateMode(str, Enum):
    """Task update mode enumeration."""
    APPEND = "append"
    OVERWRITE = "overwrite"
    SELECTIVE = "selective"
    CLEAR_ALL_TASKS = "clearAllTasks"


class TaskService:
    """Refactored service for managing tasks with consistent responses."""
    
    def __init__(self, database: Optional[MCPDatabase] = None):
        self.db: MCPDatabase = database if database is not None else cast(MCPDatabase, get_database())
        self.validator = TaskValidator
        self.version_service = VersionService(self.db, task_service=self)

    # ==================== Core CRUD Operations ====================
    
    async def create_task(self, project_id: str, task_create: TaskCreate, changed_by: str = "system") -> ServiceResponse[Task]:
        """Create a new task."""
        try:
            task_data = {
                **task_create.model_dump(),
                "project_id": project_id,
                "current_version_id": str(ObjectId()),  # Generate initial version
                "version_number": 1,
                "status": TaskStatus.PENDING,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            
            # Resolve dependencies (handle both names and IDs)
            resolved_deps, errors = await self._resolve_dependencies_by_name(project_id, task_data["dependencies"])
            if errors:
                return ServiceResponse.validation_error("; ".join(errors))
            
            # Update dependencies with resolved IDs
            task_data["dependencies"] = resolved_deps
            
            # Insert task
            result = await self.db.tasks.insert_one(task_data)
            task_data["_id"] = str(result.inserted_id)
            task_data["id"] = str(result.inserted_id)
            
            task = Task(**task_data)
            
            # Create initial version
            try:
                await self.version_service.create_version(
                    project_id=project_id,
                    task_id=str(result.inserted_id),
                    operation="create",
                    changed_by=changed_by,
                    message="Initial creation"
                )
            except Exception as e:
                # Log version creation failure but don't fail the whole operation
                print(f"Warning: Failed to create initial version for task {str(result.inserted_id)}: {str(e)}")
            
            return ServiceResponse.success_response(task, "Task created successfully")
            
        except Exception as e:
            return ServiceResponse.error_response(f"Failed to create task: {str(e)}")
    
    async def get_task(self, project_id: str, task_id: str) -> ServiceResponse[Task]:
        """Get a task by ID."""
        try:
            # Validate task ID format
            if not self.validator.validate_uuid(task_id):
                return ServiceResponse.validation_error("Invalid task ID format")
            
            task_data = await self.db.tasks.find_one({
                "_id": ObjectId(task_id),
                "project_id": project_id,
                "deleted_at": None
            })
            
            if not task_data:
                return ServiceResponse.not_found_error("Task")
            
            task_data["_id"] = str(task_data["_id"])
            task_data["id"] = str(task_data["_id"])
            
            # Ensure status is TaskStatus enum
            if "status" in task_data and isinstance(task_data["status"], str):
                task_data["status"] = TaskStatus(task_data["status"])
            
            task = Task(**task_data)
            return ServiceResponse.success_response(task)
            
        except bson_errors.InvalidId:
            return ServiceResponse.validation_error("Invalid task ID format")
        except Exception as e:
            return ServiceResponse.error_response(f"Failed to get task: {str(e)}")
    
    async def update_task(
        self, 
        project_id: str, 
        task_id: str, 
        updates: TaskUpdate,
        if_match: Optional[str] = None,
        changed_by: str = "system"
    ) -> ServiceResponse[Task]:
        """Unified task update method with optimistic locking."""
        try:
            # Validate task ID format
            if not self.validator.validate_uuid(task_id):
                return ServiceResponse.validation_error("Invalid task ID format")
            
            # Get current task
            current_task_response = await self.get_task(project_id, task_id)
            if not current_task_response.success:
                return current_task_response
            
            current_task = current_task_response.data
            
            # Check optimistic locking
            if if_match and current_task.current_version_id != if_match:
                return ServiceResponse.conflict_error("Version conflict detected")
            
            # Handle different update input types
            update_data = updates.model_dump(exclude_unset=True)

            update_data["updated_at"] = datetime.now(timezone.utc)
            
            # Resolve dependencies if provided (handle both names and IDs)
            if "dependencies" in update_data:
                resolved_deps, errors = await self._resolve_dependencies_by_name(project_id, update_data["dependencies"])
                if errors:
                    return ServiceResponse.validation_error("; ".join(errors))
                update_data["dependencies"] = resolved_deps
            
            # Perform update
            result = await self.db.tasks.update_one(
                {
                    "_id": ObjectId(task_id),
                    "project_id": project_id,
                    "deleted_at": None
                },
                {"$set": update_data}
            )
            
            if result.modified_count == 0:
                return ServiceResponse.error_response("Task not found or no changes made")
            
            ## Create version for update
            try:
                await self.version_service.create_version(
                    project_id=project_id,
                    task_id=task_id,
                    operation="update",
                    changed_by=changed_by,
                    message="Task updated"
                )
            except Exception as e:
                # Log version creation failure but don't fail the whole operation
                print(f"Warning: Failed to create version for update of task {task_id}: {str(e)}")
            
            # Return updated task
            updated_task_response = await self.get_task(project_id, task_id)
            if updated_task_response.success:
                updated_task_response.message = "Task updated successfully"
            
            return updated_task_response
            
        except bson_errors.InvalidId:
            return ServiceResponse.validation_error("Invalid task ID format")
        except Exception as e:
            return ServiceResponse.error_response(f"Failed to update task: {str(e)}")
    
    async def delete_task(self, project_id: str, task_id: str, changed_by: str = "system") -> ServiceResponse[bool]:
        """Soft delete a task."""
        try:
            # Validate task ID format
            if not self.validator.validate_uuid(task_id):
                return ServiceResponse.validation_error("Invalid task ID format")
            
            result = await self.db.tasks.update_one(
                {
                    "_id": ObjectId(task_id),
                    "project_id": project_id,
                    "deleted_at": None
                },
                {
                    "$set": {
                        "deleted_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            if result.modified_count == 0:
                return ServiceResponse.not_found_error("Task")
            
            # Create version for delete (soft delete)
            try:
                await self.version_service.create_version(
                    project_id=project_id,
                    task_id=task_id,
                    operation="delete",
                    changed_by=changed_by,
                    message="Task soft deleted"
                )
            except Exception as e:
                # Log version creation failure but don't fail the whole operation
                print(f"Warning: Failed to create version for delete of task {task_id}: {str(e)}")
            
            return ServiceResponse.success_response(True, "Task deleted successfully")
            
        except bson_errors.InvalidId:
            return ServiceResponse.validation_error("Invalid task ID format")
        except Exception as e:
            return ServiceResponse.error_response(f"Failed to delete task: {str(e)}")
    
    async def delete_project_tasks(self, project_id: str) -> ServiceResponse[Dict[str, Any]]:
        """Delete all tasks and associated data for a project."""
        try:
            # Get all tasks for this project first
            tasks_cursor = self.db.tasks.find({"project_id": project_id, "deleted_at": None})
            tasks = []
            async for task_data in tasks_cursor:
                tasks.append(str(task_data["_id"]))
            
            # Soft delete all tasks
            delete_result = await self.db.tasks.update_many(
                {"project_id": project_id, "deleted_at": None},
                {
                    "$set": {
                        "deleted_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            # Delete all task versions for this project
            versions_result = await self.db.task_versions.delete_many({"project_id": project_id})
            
            return ServiceResponse.success_response(
                {
                    "deleted_tasks": delete_result.modified_count,
                    "deleted_versions": versions_result.deleted_count,
                    "task_ids": tasks
                },
                f"Successfully deleted {delete_result.modified_count} tasks and {versions_result.deleted_count} versions"
            )
            
        except Exception as e:
            return ServiceResponse.error_response(f"Failed to delete project tasks: {str(e)}")
    
    async def list_tasks(
        self, 
        project_id: str, 
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> ServiceResponse[List[Task]]:
        """List tasks with optional filtering."""
        try:
            query = {"project_id": project_id, "deleted_at": None}
            
            if status:
                query["status"] = status
            
            cursor = self.db.tasks.find(query).sort("created_at", 1)
            
            tasks = []
            async for task_data in cursor.skip(skip).limit(limit):
                if task_data:
                    task_data["_id"] = str(task_data["_id"])
                    task_data["id"] = str(task_data["_id"])
                    # Ensure status is TaskStatus enum
                    if "status" in task_data and isinstance(task_data["status"], str):
                        task_data["status"] = TaskStatus(task_data["status"])
                tasks.append(Task(**task_data))
            
            return ServiceResponse.success_response(tasks, f"Found {len(tasks)} tasks")
            
        except Exception as e:
            return ServiceResponse.error_response(f"Failed to list tasks: {str(e)}")

    # ==================== Enhanced Batch Operations ====================
    
    async def bulk_create_tasks(
        self, 
        project_id: str, 
        tasks_create: List[TaskCreate],
        changed_by: str = "system"
    ) -> ServiceResponse[List[Task]]:
        """Bulk create tasks (simple version)."""
        try:
            tasks_data = []
            
            for task_create in tasks_create:
                task_data = {
                    **task_create.model_dump(),
                    "project_id": project_id,
                    "current_version_id": str(ObjectId()),
                    "version_number": 1,
                    "status": TaskStatus.PENDING,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
                tasks_data.append(task_data)
            
            # Validate all dependencies considering the current batch
            for task_data in tasks_data:
                dep_validation = await self._validate_dependencies_name(project_id, task_data["dependencies"], tasks_data)
                if not dep_validation.is_valid:
                    return ServiceResponse.validation_error(
                        f"Dependency validation failed for task {task_data['name']}: {dep_validation.error_message}"
                    )
            
            # Bulk insert
            result = await self.db.tasks.insert_many(tasks_data)
            created_tasks = []
            
            for i, task_data in enumerate(tasks_data):
                task_id = str(result.inserted_ids[i])
                task_data["_id"] = task_id
                task_data["id"] = task_id
                created_task = Task(**task_data)
                created_tasks.append(created_task)
                
                # Create initial version for each created task
                try:
                    await self.version_service.create_version(
                        project_id=project_id,
                        task_id=task_id,
                        operation="create",
                        changed_by= changed_by,
                        message="Initial creation via bulk operation"
                    )
                except Exception as e:
                    print(f"Warning: Failed to create initial version for task {task_id}: {str(e)}")
            
            return ServiceResponse.success_response(
                created_tasks, 
                f"Successfully created {len(created_tasks)} tasks"
            )
            
        except Exception as e:
            return ServiceResponse.error_response(f"Failed to bulk create tasks: {str(e)}")
    
    async def bulk_create_or_update_tasks(
        self,
        project_id: str,
        tasks_data: List[TaskCreate],
        update_mode: UpdateMode = UpdateMode.APPEND,
        global_analysis_result: Optional[str] = None,
        changed_by: str = "system"
    ) -> ServiceResponse[Dict[str, Any]]:
        """
        Enhanced bulk create or update tasks with multiple modes.
        
        Args:
            project_id: Project identifier
            tasks_data: Task data in various formats (TaskCreate objects, dicts, or JSON string)
            update_mode: How to handle existing tasks
            global_analysis_result: Optional global analysis to add to all tasks
            
        Returns:
            ServiceResponse containing operation results with created/updated tasks
        """
        try:
            # Parse input data
            parsed_tasks = []
            for task_item in tasks_data:
                parsed_tasks.append(task_item.model_dump())
            if not parsed_tasks:
                return ServiceResponse.validation_error("No valid tasks provided")
            
            # Validate all tasks
            validation_result = await self._validate_bulk_tasks(project_id, parsed_tasks)
            if not validation_result.is_valid:
                return ServiceResponse.validation_error(validation_result.error_message)
            
            # Handle different update modes
            operation_result = await self._execute_bulk_operation(
                project_id, parsed_tasks, update_mode, global_analysis_result, changed_by
            )
            
            return ServiceResponse.success_response(
                operation_result,
                f"Successfully processed {len(operation_result.get('all_tasks', []))} tasks using {update_mode.value} mode"
            )
            
        except Exception as e:
            return ServiceResponse.error_response(f"Bulk operation failed: {str(e)}")
    
    # ==================== Business Operations ====================
    
    async def verify_task(
        self,
        project_id: str,
        task_id: str,
        summary: str,
        score: int
    ) -> ServiceResponse[Task]:
        """Verify task completion and update status."""
        try:
            # Validate inputs
            if not self.validator.validate_uuid(task_id):
                return ServiceResponse.validation_error("Invalid task ID format")
            
            summary_validation = self.validator.validate_task_summary(summary)
            if not summary_validation.is_valid:
                return ServiceResponse.validation_error(summary_validation.error_message)
            
            score_validation = self.validator.validate_task_score(score)
            if not score_validation.is_valid:
                return ServiceResponse.validation_error(score_validation.error_message)
            
            # Get task
            task_response = await self.get_task(project_id, task_id)
            if not task_response.success:
                return task_response
            
            task = task_response.data
            
            # Check task status
            if task.status not in [TaskStatus.IN_PROGRESS, TaskStatus.PENDING]:
                return ServiceResponse.error_response(
                    f"Task {task.name} has status {task.status.value}. only status 'in_progress' and 'pending' can verify"
                )
            
            # Update based on score
            if score >= 80:
                # Task passes verification
                task_update = TaskUpdate(
                    status="completed",
                    summary=summary
                )
                
                updated_task_response = await self.update_task(project_id, task_id, task_update)
                if not updated_task_response.success:
                    return updated_task_response

                updated_task_response.message = f"Task {task.name} completed successfully. next work is using `add_memory` to record it."
                return updated_task_response
            else:
                # Task needs improvement - set to in_progress if pending
                if task.status == TaskStatus.PENDING:
                    task_update = TaskUpdate(status="in_progress")
                    updated_task_response = await self.update_task(project_id, task_id, task_update)
                    if updated_task_response.success:
                        task = updated_task_response.data
                
                return ServiceResponse.success_response(
                    task,
                    f"Task {task.name} needs improvement (score: {score}/100), please using todo_write append new todos for remaining issues"
                )
                
        except Exception as e:
            return ServiceResponse.error_response(f"Failed to verify task: {str(e)}")
    
    async def get_task_statistics(self, project_id: str) -> ServiceResponse[Dict[str, Any]]:
        """Get task statistics for a project."""
        try:
            # Count tasks by status
            pipeline = [
                {"$match": {"project_id": project_id, "deleted_at": None}},
                {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            ]
            
            status_counts = {}
            async for result in self.db.tasks.aggregate(pipeline):
                status_counts[result["_id"]] = result["count"]
            
            # Get total count
            total_count = await self.db.tasks.count_documents({
                "project_id": project_id,
                "deleted_at": None
            })
            
            statistics = {
                "project_id": project_id,
                "total_tasks": total_count,
                "status_counts": status_counts,
                "pending": status_counts.get(TaskStatus.PENDING, 0),
                "in_progress": status_counts.get(TaskStatus.IN_PROGRESS, 0),
                "completed": status_counts.get(TaskStatus.COMPLETED, 0),
                "failed": status_counts.get(TaskStatus.FAILED, 0),
                "cancelled": status_counts.get(TaskStatus.CANCELLED, 0),
            }
            
            return ServiceResponse.success_response(statistics, "Statistics retrieved successfully")
            
        except Exception as e:
            return ServiceResponse.error_response(f"Failed to get statistics: {str(e)}")
    
    async def get_task_dependencies(self, project_id: str, task_id: str) -> ServiceResponse[Dict[str, Any]]:
        """Get task dependencies and dependent tasks."""
        try:
            task_response = await self.get_task(project_id, task_id)
            if not task_response.success:
                return task_response
            
            task = task_response.data
            
            # Get dependency tasks (tasks this task depends on)
            dependencies = []
            if task.dependencies:
                # All dependencies should be ObjectId format
                dependency_object_ids = []
                
                for dep_id in task.dependencies:
                    if self.validator.validate_object_id(dep_id):
                        try:
                            dependency_object_ids.append(ObjectId(dep_id))
                        except:
                            continue  # Skip invalid ObjectIds
                
                # Query for ObjectId dependencies
                if dependency_object_ids:
                    cursor = self.db.tasks.find({
                        "_id": {"$in": dependency_object_ids},
                        "project_id": project_id,
                        "deleted_at": None
                    })
                    async for dep_task in cursor:
                        dep_task["_id"] = str(dep_task["_id"])
                        dep_task["id"] = str(dep_task["_id"])
                        dependencies.append(Task(**dep_task))
            
            # Get dependent tasks (tasks that depend on this task)
            dependents = []
            cursor = self.db.tasks.find({
                "dependencies": task_id,
                "project_id": project_id,
                "deleted_at": None
            })
            async for dep_task in cursor:
                dep_task["_id"] = str(dep_task["_id"])
                dep_task["id"] = str(dep_task["_id"])
                dependents.append(Task(**dep_task))
            
            dependency_info = {
                "task_id": task_id,
                "task_name": task.name,
                "dependencies": [dep.model_dump() for dep in dependencies],
                "dependents": [dep.model_dump() for dep in dependents],
                "can_start": len([d for d in dependencies if d.status != TaskStatus.COMPLETED]) == 0
            }
            
            return ServiceResponse.success_response(dependency_info, "Dependencies retrieved successfully")
            
        except Exception as e:
            return ServiceResponse.error_response(f"Failed to get dependencies: {str(e)}")

    # ==================== Todo Management Methods ====================
    
    async def get_todos(self, project_id: str, task_id: str) -> ServiceResponse[List[Dict[str, Any]]]:
        """Get todos for a specific task."""
        try:
            # Validate task ID format
            if not self.validator.validate_uuid(task_id):
                return ServiceResponse.validation_error("Invalid task ID format")
            
            task_data = await self.db.tasks.find_one({
                "_id": ObjectId(task_id),
                "project_id": project_id,
                "deleted_at": None
            })
            
            if not task_data:
                return ServiceResponse.not_found_error(f"Task {task_id}")
            
            todos = task_data.get("todos", [])
            return ServiceResponse.success_response(todos, "Todos retrieved successfully")
            
        except bson_errors.InvalidId:
            return ServiceResponse.validation_error("Invalid task ID format")
        except Exception as e:
            return ServiceResponse.error_response(f"Failed to get todos: {str(e)}")
    
    async def set_todos(self, project_id: str, task_id: str, todos: List[TodoItem], notes:str, changed_by: str = "system") -> ServiceResponse[List[Dict[str, Any]]]:
        """Set todos for a specific task."""
        try:
            # Validate task ID format
            if not self.validator.validate_uuid(task_id):
                return ServiceResponse.validation_error("Invalid task ID format")
            
            # Validate todos format
            validated_todos = []
            for i, todo in enumerate(todos):
                try:
                    # Convert TodoItem to dict for processing
                    if isinstance(todo, TodoItem):
                        todo_dict = todo.model_dump()
                    else:
                        todo_dict = dict(todo)
                    
                    # Ensure required fields exist
                    if not todo_dict.get("id"):
                        todo_dict["id"] = f"todo_{i}"
                    if not todo_dict.get("priority"):
                        todo_dict["priority"] = "medium"
                    if not todo_dict.get("status"):
                        todo_dict["status"] = "pending"
                    if not todo_dict.get("content"):
                        return ServiceResponse.validation_error(f"Todo item {i} missing content")
                    
                    validated_todos.append(todo_dict)
                except Exception as e:
                    return ServiceResponse.validation_error(f"Invalid todo item {i}: {str(e)}")
            
            # Update task with new todos
            result = await self.db.tasks.update_one(
                {
                    "_id": ObjectId(task_id),
                    "project_id": project_id,
                    "deleted_at": None
                },
                {
                    "$set": {
                        "todos": validated_todos,
                        "updated_at": datetime.now(timezone.utc),
                        "notes": notes
                    }
                }
            )
            
            if result.modified_count == 0:
                return ServiceResponse.not_found_error("Task")
            
            # Create version for todos update
            try:
                await self.version_service.create_version(
                    project_id=project_id,
                    task_id=task_id,
                    operation="update",
                    changed_by=changed_by,
                    message=f"Todos updated. Notes: {notes}"
                )
            except Exception as e:
                print(f"Warning: Failed to create version for todos update of task {task_id}: {str(e)}")
            
            return ServiceResponse.success_response(validated_todos, "Todos updated successfully")
            
        except bson_errors.InvalidId:
            return ServiceResponse.validation_error("Invalid task ID format")
        except Exception as e:
            return ServiceResponse.error_response(f"Failed to set todos: {str(e)}")

    # ==================== Helper Methods ====================
    
    async def _resolve_dependencies_by_name(self, project_id: str, dependencies: List[str]) -> tuple[List[str], List[str]]:
        """
        Resolve task names to IDs for dependencies.
        Returns a tuple of (resolved_ids, error_messages).
        """
        if not dependencies:
            return dependencies, []
        
        resolved_ids = []
        error_messages = []
        
        for dep in dependencies:
            # Check if it's already a valid ObjectId
            if self.validator.validate_object_id(dep):
                # Verify this ObjectId exists in the project
                try:
                    count = await self.db.tasks.count_documents({
                        "_id": ObjectId(dep),
                        "project_id": project_id,
                        "deleted_at": None
                    })
                    if count > 0:
                        resolved_ids.append(dep)
                    else:
                        error_messages.append(f"Task ID {dep} not found")
                except Exception as e:
                    error_messages.append(f"Error validating task ID {dep}: {str(e)}")
            else:
                # Try to resolve by name
                task_doc = await self.db.tasks.find_one({
                    "name": dep,
                    "project_id": project_id,
                    "deleted_at": None
                })
                if task_doc:
                    resolved_ids.append(str(task_doc["_id"]))
                else:
                    error_messages.append(f"Task name '{dep}' not found")
        
        return resolved_ids, error_messages
    
    async def _validate_dependencies(
        self, 
        project_id: str, 
        dependencies: List[str]
    ) -> ValidationResult:
        """Validate that all dependencies exist."""
        result = ValidationResult(is_valid=True)
        
        if not dependencies:
            return result
        
        try:
            dependency_ids = [ObjectId(dep_id) for dep_id in dependencies]
        except bson_errors.InvalidId:
            result.add_error("Invalid dependency ID format")
            return result
        
        # Check if all dependency tasks exist
        existing_deps = await self.db.tasks.count_documents({
            "_id": {"$in": dependency_ids},
            "project_id": project_id,
            "deleted_at": None
        })
        
        if existing_deps != len(dependencies):
            result.add_error("Some dependencies do not exist")
        
        return result
    
    async def _validate_dependencies_name(
        self, 
        project_id: str, 
        dependencies: List[str],
        current_tasks: List[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Validate that all dependencies exist using task names instead of IDs."""
        result = ValidationResult(is_valid=True)
        
        if not dependencies:
            return result
        
        # Collect all available task names from both database and current batch
        available_task_names = set()
        
        # Add task names from database (existing tasks)
        cursor = self.db.tasks.find({
            "project_id": project_id,
            "deleted_at": None
        }, {"name": 1})
        
        async for task_doc in cursor:
            available_task_names.add(task_doc.get("name", ""))
        
        # Add task names from current batch being created
        if current_tasks:
            for task_data in current_tasks:
                task_name = task_data.get("name", "").strip()
                if task_name:
                    available_task_names.add(task_name)
        
        # Check if all dependency names exist in available tasks
        missing_deps = []
        for dep_name in dependencies:
            if dep_name not in available_task_names:
                missing_deps.append(dep_name)
        
        if missing_deps:
            result.add_error(f"Dependencies not found: {', '.join(missing_deps)}")
        
        return result


    
    async def check_task_exists(self, project_id: str, task_id: str) -> bool:
        """Check if a task exists."""
        try:
            count = await self.db.tasks.count_documents({
                "_id": ObjectId(task_id),
                "project_id": project_id,
                "deleted_at": None
            })
            return count > 0
        except bson_errors.InvalidId:
            return False
    
    # ==================== Enhanced Bulk Operation Helpers ====================
    
    async def _parse_tasks_input(self, tasks_data: Union[List[TaskCreate], List[Dict[str, Any]], str]) -> List[Dict[str, Any]]:
        """Parse various input formats into standardized task dictionaries."""
        if isinstance(tasks_data, str):
            # Parse JSON string
            try:
                tasks_data = json.loads(tasks_data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format: {str(e)}")
        
        if isinstance(tasks_data, list):
            parsed_tasks = []
            for task_item in tasks_data:
                if isinstance(task_item, TaskCreate):
                    # Convert TaskCreate to dict
                    parsed_tasks.append(task_item.model_dump())
                elif isinstance(task_item, dict):
                    parsed_tasks.append(task_item)
                else:
                    raise ValueError(f"Invalid task format: {type(task_item)}")
            return parsed_tasks
        
        raise ValueError("tasks_data must be a list or JSON string")
    
    async def _validate_bulk_tasks(self, project_id: str, tasks: List[Dict[str, Any]]) -> ValidationResult:
        """Comprehensive validation for bulk tasks."""
        result = ValidationResult(is_valid=True)
        
        if not tasks:
            result.add_error("At least one task is required")
            return result
        
        # Check for duplicate names
        names = [task.get('name', '').strip() for task in tasks]
        seen_names = set()
        for name in names:
            if not name:
                result.add_error("Task name cannot be empty")
            elif name in seen_names:
                result.add_error(f"Duplicate task name: {name}")
            else:
                seen_names.add(name)
        
        # Validate each task
        for i, task in enumerate(tasks):
            task_validation = self.validator.validate_task_input(task, True)
            if not task_validation.is_valid:
                for error in task_validation.errors:
                    result.add_error(f"Task {i+1} ({task.get('name', 'unnamed')}): {error}")
            
            # Validate dependencies exist (if provided)
            dependencies = task.get('dependencies', [])
            if dependencies:
                dep_validation = await self._validate_dependencies_name(project_id, dependencies, tasks)
                if not dep_validation.is_valid:
                    result.add_error(f"Task {i+1} dependency validation failed: {dep_validation.error_message}")
        
        return result
    
    async def _execute_bulk_operation(
        self, 
        project_id: str, 
        tasks: List[Dict[str, Any]], 
        update_mode: UpdateMode,
        global_analysis_result: Optional[str],
        changed_by: str = "system"
    ) -> Dict[str, Any]:
        """Execute the bulk operation based on update mode."""
        
        created_tasks = []
        updated_tasks = []
        backup_info = None
        
        if update_mode == UpdateMode.CLEAR_ALL_TASKS:
            # Create backup before clearing
            backup_info = await self._create_task_backup(project_id)
            
            # Clear all incomplete tasks using version-aware soft delete
            tasks_to_delete = await self.db.tasks.find({
                "project_id": project_id,
                "status": {"$ne": TaskStatus.COMPLETED},
                "deleted_at": None
            }).to_list(length=None)
            
            for task_doc in tasks_to_delete:
                try:
                    await self.delete_task(project_id, str(task_doc["_id"]), changed_by=changed_by)
                except Exception as e:
                    print(f"Warning: Failed to properly delete task {str(task_doc['_id'])}: {str(e)}")
            
            # Create all new tasks
            created_tasks = await self._create_tasks_from_dicts(project_id, tasks, global_analysis_result, changed_by)
            
        elif update_mode == UpdateMode.OVERWRITE:
            # Delete incomplete tasks, keep completed ones using version-aware soft delete
            tasks_to_delete = await self.db.tasks.find({
                "project_id": project_id,
                "status": {"$ne": TaskStatus.COMPLETED},
                "deleted_at": None
            }).to_list(length=None)
            
            for task_doc in tasks_to_delete:
                try:
                    await self.delete_task(project_id, str(task_doc["_id"]), changed_by=changed_by)
                except Exception as e:
                    print(f"Warning: Failed to properly delete task {str(task_doc['_id'])}: {str(e)}")
            
            # Create all new tasks
            created_tasks = await self._create_tasks_from_dicts(project_id, tasks, global_analysis_result, changed_by)
            
        elif update_mode == UpdateMode.SELECTIVE:
            # Update existing tasks by name, create new ones
            existing_tasks = {}
            cursor = self.db.tasks.find({
                "project_id": project_id,
                "deleted_at": None
            })
            async for task in cursor:
                existing_tasks[task['name']] = task
            
            for task_data in tasks:
                task_name = task_data.get('name', '').strip()
                
                if task_name in existing_tasks and existing_tasks[task_name]['status'] != TaskStatus.COMPLETED:
                    # Update existing task
                    existing_task = existing_tasks[task_name]
                    task_update = TaskUpdate(**{k: v for k, v in task_data.items() if v is not None})
                    
                    update_response = await self.update_task(project_id, str(existing_task["_id"]), task_update, changed_by=changed_by)
                    if update_response.success:
                        updated_tasks.append(update_response.data)
                else:
                    # Create new task
                    new_task = await self._create_single_task_from_dict(project_id, task_data, global_analysis_result, changed_by)
                    created_tasks.append(new_task)
                    
        elif update_mode == UpdateMode.APPEND:
            # Simply create all new tasks
            created_tasks = await self._create_tasks_from_dicts(project_id, tasks, global_analysis_result, changed_by)
        
        # Get all current tasks for summary
        all_tasks_response = await self.list_tasks(project_id, limit=1000)  # Large limit for complete view
        all_tasks = all_tasks_response.data if all_tasks_response.success else []
        
        return {
            "success": True,
            "created_tasks": [task.model_dump() for task in created_tasks],
            "updated_tasks": [task.model_dump() for task in updated_tasks],
            "all_tasks": [task.model_dump() for task in all_tasks],
            "backup_info": backup_info,
            "update_mode": update_mode.value,
            "summary": {
                "total_processed": len(created_tasks) + len(updated_tasks),
                "created_count": len(created_tasks),
                "updated_count": len(updated_tasks),
                "total_in_project": len(all_tasks)
            }
        }
    
    async def _create_tasks_from_dicts(
        self, 
        project_id: str, 
        tasks_data: List[Dict[str, Any]], 
        global_analysis: Optional[str],
        changed_by: str = "system"
    ) -> List[Task]:
        """Create multiple tasks from dictionary data."""
        created_tasks = []
        
        for task_data in tasks_data:
            try:
                task = await self._create_single_task_from_dict(project_id, task_data, global_analysis, changed_by)
                created_tasks.append(task)
            except Exception as e:
                # Log error but continue with other tasks
                print(f"Failed to create task {task_data.get('name', 'unnamed')}: {str(e)}")
        
        return created_tasks
    
    async def _create_single_task_from_dict(
        self, 
        project_id: str, 
        task_data: Dict[str, Any], 
        global_analysis: Optional[str],
        changed_by: str = "system"
    ) -> Task:
        """Create a single task from dictionary data."""
        # Add global analysis to task if provided
        if global_analysis:
            task_data = {**task_data}  # Create copy
            if not task_data.get('summary'):
                task_data['summary'] = global_analysis
        
        # Directly create the task to avoid duplicate version creation
        task_data_full = {
            **task_data,
            "project_id": project_id,
            "current_version_id": str(ObjectId()),
            "version_number": 1,
            "status": TaskStatus.PENDING,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        # Resolve dependencies
        resolved_deps, errors = await self._resolve_dependencies_by_name(project_id, task_data_full.get("dependencies", []))
        if errors:
            raise ValueError("; ".join(errors))
        task_data_full["dependencies"] = resolved_deps
        
        # Insert task
        result = await self.db.tasks.insert_one(task_data_full)
        task_id = str(result.inserted_id)
        task_data_full["_id"] = task_id
        task_data_full["id"] = task_id
        
        task = Task(**task_data_full)
        
        # Create initial version
        try:
            await self.version_service.create_version(
                project_id=project_id,
                task_id=task_id,
                operation="create",
                changed_by=changed_by,
                message="Initial creation via bulk operation"
            )
        except Exception as e:
            print(f"Warning: Failed to create initial version for task {task_id}: {str(e)}")
        
        return task
    
    async def _create_task_backup(self, project_id: str) -> Dict[str, Any]:
        """Create backup of current tasks before clearing."""
        try:
            # Get all current tasks
            tasks_response = await self.list_tasks(project_id, skip=0, limit=1000)  # Large limit for backup
            if not tasks_response.success:
                return {"error": "Failed to create backup"}
            
            tasks = tasks_response.data
            backup_data = {
                "project_id": project_id,
                "backup_timestamp": datetime.now(timezone.utc).isoformat(),
                "task_count": len(tasks),
                "tasks": [task.model_dump() for task in tasks]
            }
            
            return {
                "success": True,
                "backup_timestamp": backup_data["backup_timestamp"],
                "task_count": backup_data["task_count"],
                "backup_data": backup_data
            }
            
        except Exception as e:
            return {"error": f"Backup failed: {str(e)}"}