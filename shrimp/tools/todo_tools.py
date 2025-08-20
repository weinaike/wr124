
from typing import Annotated, List, Optional, Dict, Any, Union
from fastmcp import FastMCP

from shrimp.models import task
from shrimp.models.task import TaskCreate, TaskUpdate, TodoItem
from shrimp.services.task_service import TaskService
from shrimp.db.database import mcp_db_manager
from .base_tool import BaseTool
from .response_format import MCPToolResponse


async def get_mcp_task_service():
    """Get TaskService instance with MCP database connection."""
    if mcp_db_manager.database is None:
        await mcp_db_manager.connect_to_mongo()
    return TaskService(mcp_db_manager.database)


def register_todo_tools(app: FastMCP):
    """Register all task-related tools with the FastMCP application.
    
    Args:
        app: The FastMCP application instance to register tools with
    """
    
    

    @app.tool
    async def todo_read(task_id: Annotated[str, "任务ID"]) -> Dict[str, Any]:
        """获取任务的代办事项列表
            Use this tool to read the current to-do list for the session. This tool should be used proactively and frequently to ensure that you are aware of the status of the current task list. You should make use of this tool as often as possible, especially in the following situations:
            - At the beginning of conversations to see what's pending
            - Before starting new todos to prioritize work
            - Whenever you're uncertain about what to do next
            - After completing todos to update your understanding of remaining work
            - After every few messages to ensure you're on track

            Usage:
            - Returns a list of todo items with their status, priority, and content
            - Use this information to track progress and plan next steps
            - If no todos exist yet, an empty list will be returned
            Args:
            task_id: 任务ID
        """
        try:
            task_service = await get_mcp_task_service()
            project_id = BaseTool.get_project_id()
            result = await task_service.get_todos(project_id, task_id)
            
            if result.success:
                return MCPToolResponse.success(
                    data=result.data,
                    operation="todo_read",
                    message=f"Successfully retrieved todos for task {task_id}"
                )
            else:
                return MCPToolResponse.error(
                    operation="todo_read",
                    error_message=result.error or "Failed to read todos"
                )
                
        except Exception as e:
            return MCPToolResponse.error(
                operation="todo_read", 
                error_message=f"Failed to read todos: {str(e)}"
            )
    
    
    @app.tool
    async def todo_write(task_id: Annotated[str, "task ID"],
                         todos: List[TodoItem], 
                         notes: Annotated[str, "notes for updating the todos"],
                         operator: Annotated[str, "Agent's Name"]) -> Dict[str, Any]:
        """
Before you use this tool, you MUST first create a task using `split_task` or `create_task` to generate a TaskID.

Use this tool to create and manage a structured todo list for your current coding session. This helps you track progress, organize complex tasks, and demonstrate thoroughness to the user.
It also helps the user understand the progress of the task and overall progress of their requests.

## Use this tool proactively in these scenarios:
1. When you start working on a new task, mark the todo as in_progress. Ideally you should only have one todo as in_progress at a time. Complete existing tasks before starting new ones.
2. After receiving new instructions - Immediately capture user requirements as todos. Feel free to edit the todo list based on new information.
## ToDo States and Management

1. **ToDo States**: Use these states to track progress:
- pending: Todo not yet started
- in_progress: Currently working on (limit to ONE todo at a time)
- completed: Todo finished successfully
- cancelled: Todo no longer needed

2. **ToDo Management**:
- Update todo status in real-time as you work
- Mark todos complete IMMEDIATELY after finishing (don't batch completions)
- Only have ONE todo in_progress at any time
- Complete current todos before starting new ones
- Cancel todos that become irrelevant

3. **ToDo Breakdown**:
- Create specific, actionable items
- Break complex todos into smaller, manageable steps
- Use clear, descriptive todo names

When in doubt, use this tool. Being proactive with todo management demonstrates attentiveness and ensures you complete all requirements successfully."

        """
        try:
            task_service = await get_mcp_task_service()
            project_id = BaseTool.get_project_id()
            result = await task_service.set_todos(project_id, task_id, todos, notes, changed_by=operator)
            
            if result.success:
                completed = True
                status = [todo.get("status") for todo in result.data]
                if "in_progress" in status or "pending" in status:
                    completed = False

                return MCPToolResponse.success(
                    data=result.data,
                    operation="todo_write",
                    message=f"Successfully updated todos for task {task_id}" if completed is False else "All todos completed, call verify_task tool to complete the task"
                )
            else:
                return MCPToolResponse.error(
                    operation="todo_write",
                    error_message=result.error or "Failed to update todos"
                )
                
        except Exception as e:
            return MCPToolResponse.error(
                operation="todo_write",
                error_message=f"Failed to update todos: {str(e)}"
            )
