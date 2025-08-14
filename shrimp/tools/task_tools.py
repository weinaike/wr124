"""Task management tools for MCP server.

This module provides comprehensive task management functionality including:
- CRUD operations for tasks
- Task verification and completion tracking
- Todo item management within tasks
- Bulk operations and task splitting
- Status filtering and pagination
- Project isolation through project_id
"""

from typing import Annotated, List, Literal, Optional, Dict, Any, Union
from fastmcp import FastMCP

from shrimp.models.task import TaskCreate, TaskUpdate
from shrimp.services.task_service import TaskService, UpdateMode
from shrimp.db.database import mcp_db_manager
from .base_tool import BaseTool
from .response_format import MCPToolResponse


async def get_mcp_task_service():
    """Get TaskService instance with MCP database connection."""
    if mcp_db_manager.database is None:
        await mcp_db_manager.connect_to_mongo()
    return TaskService(mcp_db_manager.database)


def register_task_tools(app: FastMCP):
    """Register all task-related tools with the FastMCP application.
    
    This function registers the following tools:
    - create_task: Create new tasks in the project
    - acquire_task: Acquire and retrieve task details with status update
    - list_tasks: List project tasks with filtering and pagination
    - update_task: Update existing task information
    - delete_task: Remove tasks from the project
    - split_tasks: Batch create/update tasks with multiple modes
    - verify_task: Verify task completion and update status
    - get_todos: Retrieve todo items for a task
    - set_todos: Set/update todo items for a task
    
    Args:
        app: The FastMCP application instance to register tools with
    """
    
    @app.tool
    async def create_task(task_create: TaskCreate, 
                          operator: Annotated[str, "Name of the agent calling this tool"]) -> Dict[str, Any]:
        """Create a new task in the project.
        
        Agent Interface Description:
        - Function: Create a new task within the specified project
        - Input: TaskCreate object containing task basic information, operator: Name of the calling agent
        - Output: Successfully created task object with generated task_id and timestamps
        - Project Isolation: Automatically retrieves project_id from request headers to ensure proper task ownership
        - Usage: Agents can use this tool to create programming tasks to be executed
        
        Args:
            task_create (TaskCreate): Task creation data including name, description, 
                                    status, dependencies, etc.
            operator (str): The name of the agent creating the task

        Returns:
            dict: Created task data with generated ID and timestamps, or error response if failed
            
        """
        task_service = await get_mcp_task_service()
        project_id = BaseTool.get_project_id()
        response = await task_service.create_task(project_id, task_create, changed_by=operator)

        if response.success and response.data:
            return MCPToolResponse.success(
                data=response.data.model_dump(),
                operation="create_task",
                message=f"Successfully created task: {response.data.name}",
                metadata={
                    "project_id": project_id,
                    "task_id": response.data.id,
                    "task_status": response.data.status
                }
            )
        else:
            return MCPToolResponse.error(
                operation="create_task",
                error_message=response.error or "Failed to create task",
                metadata={"project_id": project_id}
            )

    @app.tool
    async def acquire_task(task_id: Annotated[str, "Task ID"]) -> Dict[str, Any]:
        """Acquire a task and retrieve its detailed guidance. Essential operation before starting task execution.
        
        Agent Interface Description:
        - Function: Retrieve complete task information based on task_id and set status to 'in_progress'
        - Input: task_id string
        - Output: Detailed task information including name, description, status, dependencies, etc.
        - Project Isolation: Can only retrieve tasks within the current project
        - Usage: Agents query specific task details to understand task progress and requirements
        
        Args:
            task_id (str): Unique identifier for the task to acquire
            
        Returns:
            dict: Complete task information with updated status, or error response if not found
            
        Example Usage:
            task_info = await acquire_task("689c883d681e1760ae333035")
            if task_info and task_info.get('success'):
                print(f"Task status: {task_info['data']['status']}")
        """
        task_service = await get_mcp_task_service()
        project_id = BaseTool.get_project_id()
        update_data = TaskUpdate(
            status="in_progress",
            notes="Task acquired and in progress"
        )

        response = await task_service.update_task(project_id, task_id, updates=update_data, changed_by="system")
        # response = await task_service.get_task(project_id, task_id)
        
        if response.success and response.data:
            return MCPToolResponse.success(
                data=response.data.model_dump(),
                operation="acquire_task",
                message=f"Retrieved task: {response.data.name}",
                metadata={
                    "project_id": project_id,
                    "task_id": task_id,
                    "task_status": response.data.status
                }
            )
        else:
            return MCPToolResponse.error(
                operation="acquire_task",
                error_message=response.error or f"Task {task_id} not found",
                error_code="TASK_NOT_FOUND" if "not found" in (response.error or "").lower() else "OPERATION_FAILED",
                metadata={"project_id": project_id, "task_id": task_id}
            )

    @app.tool
    async def list_tasks(
        status: Annotated[Literal["pending", "in_progress", "completed"], "Task status filter (optional)"] = None,
        skip: Annotated[int, "Number of tasks to skip (default: 0)"] = 0,
        limit: Annotated[int, "Maximum number of tasks to return (default: 100)"] = 100,
    ):
        """List project tasks with filtering and pagination support.
        
        Agent Interface Description:
        - Function: Retrieve task list within the project with optional status filtering
        - Input: Optional status filter and pagination parameters
        - Output: Task list sorted by creation time
        - Project Isolation: Only returns tasks from the current project
        - Usage: Agents view overall project task status and plan work priorities
        
        Args:
            status (Optional[str]): Filter tasks by status (pending, in_progress, completed)
            skip (int): Number of tasks to skip for pagination (default: 0)
            limit (int): Maximum number of tasks to return (default: 100)
            
        Returns:
            dict: Response with list of task objects matching the criteria
            
        Example Usage:
            # Get all pending tasks
            pending_tasks = await list_tasks(status="pending")
            
            # Get next 20 tasks (pagination)
            next_batch = await list_tasks(skip=20, limit=20)
        """
        task_service = await get_mcp_task_service()
        project_id = BaseTool.get_project_id()
        response = await task_service.list_tasks(project_id, status, skip, limit)
        
        if response.success and response.data is not None:
            tasks_data = [task.model_dump() for task in response.data]
            return MCPToolResponse.list_success(
                items=tasks_data,
                operation="list_tasks",
                page_info={
                    "skip": skip,
                    "limit": limit,
                    "returned_count": len(tasks_data)
                },
                message=f"Retrieved {len(tasks_data)} tasks" + (f" with status '{status}'" if status else "")
            )
        else:
            return MCPToolResponse.error(
                operation="list_tasks",
                error_message=response.error or "Failed to retrieve tasks",
                metadata={
                    "project_id": project_id,
                    "status_filter": status,
                    "skip": skip,
                    "limit": limit
                }
            )

    @app.tool
    async def update_task(
        task_id: Annotated[str, "Task ID"],
        task_update: Annotated[TaskUpdate, "Task update data"],
        operator: Annotated[str, "Name of the agent calling this tool"]
    ):
        """Update task information, mainly used for task refinement.
        
        Agent Interface Description:
        - Function: Update existing task information (status, description, dependencies, etc.)
        - Input: task_id and TaskUpdate object containing fields to update
        - Output: Updated task object
        
        Args:
            task_id (str): Unique identifier for the task to update
            task_update (TaskUpdate): Updated task data (only changed fields)
            operator (str): The name of the agent updating the task
            
        Returns:
            dict: Updated task data, or error response if not found or conflict
            
        """
        task_service = await get_mcp_task_service()
        project_id = BaseTool.get_project_id()
        response = await task_service.update_task(project_id, task_id, task_update, 
                                                  if_match=None, changed_by=operator)

        if response.success and response.data:
            return MCPToolResponse.success(
                data=response.data.model_dump(),
                operation="update_task",
                message=f"Successfully updated task: {response.data.name}",
                metadata={
                    "project_id": project_id,
                    "task_id": task_id,
                    "task_status": response.data.status
                }
            )
        else:
            error_code = "VERSION_CONFLICT" if "conflict" in (response.error or "").lower() else "OPERATION_FAILED"
            return MCPToolResponse.error(
                operation="update_task",
                error_message=response.error or f"Failed to update task {task_id}",
                error_code=error_code,
                metadata={"project_id": project_id, "task_id": task_id}
            )

    @app.tool
    async def delete_task(task_id: Annotated[str, "Task ID"],
                          operator: Annotated[str, "Name of the agent calling this tool"]) -> Dict[str, Any]:
        """Delete a task from the project.
        
        Agent Interface Description:
        - Function: Delete a specified task from the project
        - Input: task_id string, operator string
        - Output: Boolean indicating whether deletion was successful
        - Project Isolation: Can only delete tasks within the current project
        - Note: Deletion operation is irreversible, use with caution
        - Usage: Agents clean up unnecessary tasks or erroneously created tasks
        
        Args:
            task_id (str): Unique identifier for the task to delete
            operator (str): The name of the agent deleting the task
            
        Returns:
            dict: Success response with deletion confirmation, or error response
            
        Example Usage:
            success = await delete_task("689c883d681e1760ae333035", "agent_123")
            if success.get('success'):
                print("Task deleted successfully")
        """
        task_service = await get_mcp_task_service()
        project_id = BaseTool.get_project_id()
        response = await task_service.delete_task(project_id, task_id, changed_by=operator)

        if response.success:
            return MCPToolResponse.success(
                data={"deleted": True, "task_id": task_id},
                operation="delete_task",
                message=f"Successfully deleted task {task_id}",
                metadata={
                    "project_id": project_id,
                    "task_id": task_id,
                    "deletion_type": "soft_delete"
                }
            )
        else:
            error_code = "TASK_NOT_FOUND" if "not found" in (response.error or "").lower() else "OPERATION_FAILED"
            return MCPToolResponse.error(
                operation="delete_task",
                error_message=response.error or f"Failed to delete task {task_id}",
                error_code=error_code,
                metadata={"project_id": project_id, "task_id": task_id}
            )

    @app.tool
    async def split_tasks(
        tasks: Annotated[List[TaskCreate], "List of tasks to create"],
        update_mode: Annotated[Literal["append", "overwrite", "selective", "clearAllTasks"], "Update mode"],
        operator: Annotated[str, "Name of the agent calling this tool"],
        global_analysis_result: Annotated[Optional[str], "Global analysis result (optional)"] = None
    ):
        """Task decomposition tool with multiple update modes support, used for batch processing.
        
        Agent Interface Description:
        - Function: Decompose large tasks into multiple subtasks with various update strategies
        - Input: List of TaskCreate objects, update mode, optional global analysis result
        - Output: Operation result details including created/updated task lists
        - Project Isolation: All operations are performed within the current project scope
        - Intelligent Decomposition: Supports dependency management and task priority arrangement
        - Usage: Agents perform complex project planning and task management
        
        Supported Update Modes:
        - append: Append mode - keep all existing tasks and add new ones
        - overwrite: Overwrite mode - delete incomplete tasks, keep completed tasks, create new tasks
        - selective: Selective mode - intelligently update existing tasks by name or create new ones
        - clearAllTasks: Clear mode - backup and clear all incomplete tasks, create new tasks
        
        Args:
            tasks (List[TaskCreate]): List of task creation objects with task definitions
            update_mode (str): Update mode (append/overwrite/selective/clearAllTasks)
            operator (str): The name of the agent performing the split
            global_analysis_result (Optional[str]): Global analysis result to be applied to all tasks
            
        Returns:
            dict: Detailed operation results including:
                - success: Whether the operation succeeded
                - created_tasks: List of newly created tasks
                - updated_tasks: List of updated tasks
                - all_tasks: All tasks after the operation
                - backup_info: Backup information (clearAllTasks mode)
                - summary: Operation summary statistics            

        Agent Usage Scenarios:
        1. **Project Initialization**: Use clearAllTasks mode to re-plan the entire project
        2. **Iterative Development**: Use selective mode to update partial tasks and add new ones  
        3. **Feature Expansion**: Use append mode to add new feature tasks
        4. **Refactoring Planning**: Use overwrite mode to replace outdated incomplete tasks
        """
        task_service = await get_mcp_task_service()
        project_id = BaseTool.get_project_id()
        
        # Convert string update_mode to UpdateMode enum
        try:
            update_mode_enum = UpdateMode(update_mode)
        except ValueError:
            return MCPToolResponse.error(
                operation="split_tasks",
                error_message=f"Invalid update mode: {update_mode}. Valid modes are: {list(UpdateMode)}",
                metadata={
                    "project_id": project_id,
                    "update_mode": update_mode,
                    "global_analysis_provided": global_analysis_result is not None
                }
            )
        
        response = await task_service.bulk_create_or_update_tasks(
            project_id, tasks, update_mode_enum, global_analysis_result, changed_by=operator
        )
        
        if response.success and response.data:
            data = response.data
            return MCPToolResponse.bulk_success(
                created_items=data.get("created_tasks", []),
                updated_items=data.get("updated_tasks", []),
                operation="split_tasks",
                message=f"Task splitting completed using {update_mode} mode",
            )
        else:
            return MCPToolResponse.error(
                operation="split_tasks",
                error_message=response.error or "Failed to split tasks",
                metadata={
                    "project_id": project_id,
                    "update_mode": update_mode,
                    "global_analysis_provided": global_analysis_result is not None
                }
            )

    @app.tool
    async def verify_task(
        task_id: Annotated[str, "Task ID"], 
        summary: Annotated[str, "Task completion summary or improvement suggestions (30-1000 words)"],
        score: Annotated[int, "Task completion score (0-100)"]
    ) -> Dict[str, Any]:
        """Verify task completion and update status based on score.
        
        Agent Interface Description:
        - Function: Verify task completion quality and update status automatically
        - Input: task_id, completion summary, and score (0-100)
        - Output: Updated task object with new status
        - Score Logic: Score >= 80 marks task as completed, < 80 sets to in_progress
        - Project Isolation: Can only verify tasks within the current project
        - Usage: Agents evaluate their own work or peer review task completion
        
        Args:
            task_id (str): Unique identifier for the task to verify
            summary (str): Completion summary (if score >= 80) or improvement suggestions (if < 80)
            score (int): Completion quality score from 0 to 100
            
        Returns:
            dict: Verification result with updated task data
            
        Example Usage:
            # Task passes verification
            result = await verify_task("689c883d681e1760ae333035", "All requirements implemented and tested ... ", 85)
            
            # Task needs improvement
            result = await verify_task("689c883d681e1760ae333035", "Missing error handling and tests ... ", 65)
        """
        task_service = await get_mcp_task_service()
        project_id = BaseTool.get_project_id()
        response = await task_service.verify_task(project_id, task_id, summary, score)

        if response.success and response.data:
            return MCPToolResponse.success(
                data=response.data.model_dump(),
                operation="verify_task",
                message=response.message,
                metadata={
                    "project_id": project_id,
                    "task_id": task_id,
                    "score": score,
                    "task_status": response.data.status
                }
            )
        else:
            return MCPToolResponse.error(
                operation="verify_task",
                error_message=response.error or f"Failed to verify task {task_id}",
                metadata={"project_id": project_id, "task_id": task_id, "score": score}
            )
