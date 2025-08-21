"""MCP工具统一返回格式规范和工具类

为所有MCP工具提供统一的返回格式，便于智能体理解和处理结果。
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone


class MCPToolResponse:
    """MCP工具统一返回格式类"""
    
    @staticmethod
    def success(
        data: Any,
        operation: str,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建成功响应
        
        Args:
            data: 操作返回的具体数据
            operation: 操作名称 (如 'create_task', 'get_memory')
            message: 可选的成功消息
            metadata: 可选的元数据信息
            
        Returns:
            dict: 统一格式的成功响应
        """
        return {
            "success": True,
            "operation": operation,
            "data": data,
            "message": message or f"{operation} completed successfully",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
            "error": None
        }
    
    @staticmethod
    def error(
        operation: str,
        error_message: str,        
        error_code: Optional[str] = None,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建错误响应
        
        Args:
            operation: 操作名称
            error_message: 错误消息
            error_code: 可选的错误代码
            metadata: 可选的元数据信息
            
        Returns:
            dict: 统一格式的错误响应
        """
        return {
            "success": False,
            "operation": operation,
            "data": None,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
            "error": {
                "message": error_message,
                "code": error_code or "OPERATION_FAILED"
            }
        }
    
    @staticmethod
    def list_success(
        items: List[Any],
        operation: str,
        total_count: Optional[int] = None,
        page_info: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建列表操作成功响应
        
        Args:
            items: 列表项目
            operation: 操作名称
            total_count: 可选的总数量
            page_info: 可选的分页信息
            message: 可选的消息
            
        Returns:
            dict: 统一格式的列表响应
        """
        count = len(items)
        metadata = {
            "count": count,
            "total_count": total_count or count
        }
        
        if page_info:
            metadata["pagination"] = page_info
            
        return MCPToolResponse.success(
            data=items,
            operation=operation,
            message=message or f"Retrieved {count} items",
            metadata=metadata
        )
    
    @staticmethod
    def bulk_success(
        created_items: List[Any],
        updated_items: List[Any],
        operation: str,
        message: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建批量操作成功响应
        
        Args:
            created_items: 创建的项目列表
            updated_items: 更新的项目列表
            operation: 操作名称
            message: 可选的消息
            additional_data: 可选的额外数据
            
        Returns:
            dict: 统一格式的批量操作响应
        """
        data = {
            "created": created_items,
            "updated": updated_items,
            "summary": {
                "created_count": len(created_items),
                "updated_count": len(updated_items),
                "total_processed": len(created_items) + len(updated_items)
            }
        }
        
        if additional_data:
            data.update(additional_data)
            
        metadata = {
            "operation_type": "bulk",
            "created_count": len(created_items),
            "updated_count": len(updated_items)
        }
        
        return MCPToolResponse.success(
            data=data,
            operation=operation,
            message=message or f"Bulk operation completed: {len(created_items)} created, {len(updated_items)} updated",
            metadata=metadata
        )