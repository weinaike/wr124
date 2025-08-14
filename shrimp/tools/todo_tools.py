
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
    async def todo_write(task_id: str, todos: List[TodoItem]) -> Dict[str, Any]:
        """更新任务的代办事项
        
        Args:
            task_id: 任务ID 
            todos: 代办事项列表，每项包含: id, content, priority(low/medium/high), status(pending/in_progress/completed)
        """
        try:
            task_service = await get_mcp_task_service()
            project_id = BaseTool.get_project_id()
            result = await task_service.set_todos(project_id, task_id, todos, changed_by="mcp_tool")
            
            if result.success:
                return MCPToolResponse.success(
                    data=result.data,
                    operation="todo_write",
                    message=f"Successfully updated todos for task {task_id}"
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
