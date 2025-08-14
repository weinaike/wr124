"""Base tool class and utilities for MCP tools."""

from typing import Optional
from fastmcp.server.dependencies import get_http_request

from .response_format import MCPToolResponse


class BaseTool:
    """Base class for all MCP tools providing common functionality."""
    
    @staticmethod
    def get_project_id() -> str:
        """Get project_id from HTTP request headers.
        
        Returns:
            str: Project ID from X-Project-ID header, defaults to 'default' if not found
        """
        return get_project_id_from_request()


def get_project_id_from_request() -> str:
    """从 HTTP 请求头部获取 project_id 的辅助函数
    
    Returns:
        str: Project ID from X-Project-ID header, defaults to 'default' if not found or on error
        
    Usage:
        This function is used by all MCP tools to ensure proper project isolation.
        Each tool call automatically extracts the project_id from the request headers.
    """
    try:
        request = get_http_request()
        # 尝试不同的头部名称
        project_id = request.headers.get('X-Project-ID')
        
        return project_id or 'default'
    except:
        return 'default'