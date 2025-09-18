"""
工具管理模块
负责MCP工具的注册、验证和管理
"""
import asyncio
import traceback
import sys
from typing import Dict, Any, List, Union, Callable
from .mcp import (
    StdioServerParams, 
    StreamableHttpServerParams, 
    SseServerParams, 
    mcp_server_tools,
    SseMcpToolAdapter,
    StdioMcpToolAdapter,
    StreamableHttpMcpToolAdapter, 
    McpSessionManager
)
from rich.console import Console as RichConsole

class ToolManager:
    """工具管理器"""
    
    def __init__(self):
        self._tools: Dict[str, Any] = {}
        self._console = RichConsole()
        self._mcp_session_manager = McpSessionManager()
    
    def add_context_tool(self, tools: List[StdioMcpToolAdapter]):
        """
        添加上下文工具（该工具要求 ClientSession 在生命周期内容不变）
        """
        for tool in tools:
            tool_name = tool.name
            if not self._validate_tool_name(tool_name):
                continue
            self._tools[tool_name] = tool
        return self._tools
        

    async def register_tools(
        self, 
        name : str,
        param: Union[StdioServerParams, StreamableHttpServerParams, SseServerParams, Dict[str, Callable]]
    ) -> Dict[str, Any]:
        """
        注册工具
        
        Args:
            param: 工具参数，可以是MCP服务器参数或工具字典
            
        Returns:
            已注册的工具字典
        """
        if isinstance(param, dict) and all(callable(v) for v in param.values()):
            # 直接注册函数工具
            for k, v in param.items():
                self._tools[k] = v
        elif isinstance(param, (StdioServerParams, StreamableHttpServerParams, SseServerParams)):
            # 注册MCP工具
            client = None
            try:
                client = await self._mcp_session_manager.create_session(name, param)
                tools = await mcp_server_tools(param, session=client)
                for tool in tools:
                    tool_name = tool.schema.get('name')
                    
                    # 验证工具名称
                    if not self._validate_tool_name(tool_name):
                        continue
                        
                    self._tools[tool_name] = tool
            except ConnectionError as e:
                # 连接错误通常是配置问题或服务器问题
                self._console.print(f"[red]🔌 连接 MCP 服务器失败 [{name}]: {e}[/red]")
                
                # 如果会话创建成功但连接失败，需要清理会话
                if self._mcp_session_manager.has_session(name):
                    try:
                        await self._mcp_session_manager.close_session(name)
                        self._console.print(f"[yellow]🔧 已清理失败的会话: {name}[/yellow]")
                    except Exception:
                        pass  # 忽略清理错误
                        
            except Exception as e:
                self._console.print(f"[red]⚠️  注册工具失败 [{name}]: {e}[/red]")
                
                # 如果会话创建成功但工具注册失败，需要清理会话
                if client is not None and self._mcp_session_manager.has_session(name):
                    try:
                        await self._mcp_session_manager.close_session(name)
                        self._console.print(f"[yellow]🔧 已清理失败的会话: {name}[/yellow]")
                    except Exception as cleanup_err:
                        self._console.print(f"[red]⚠️  清理会话失败: {cleanup_err}[/red]")
                
                # 只在调试模式下打印详细错误信息
                if "--debug" in sys.argv:
                    traceback.print_exc()
                
        return self._tools
    
    def _validate_tool_name(self, tool_name: Any) -> bool:
        """验证工具名称是否有效"""
        if not isinstance(tool_name, str) or not tool_name.strip():
            self._console.print(
                f"[red]⚠️  Warning: Skipping tool with invalid name: {tool_name} "
                f"(type: {type(tool_name)})[/red]"
            )
            return False
        return True
    
    def get_tools_by_names(self, tool_names: list, strict: bool = False) -> list:
        """
        根据工具名称获取工具列表
        
        Args:
            tool_names: 工具名称列表
            strict: 如果为True，工具不存在时抛出异常；如果为False，只发出警告
        
        Returns:
            可用的工具列表
        """
        tools = []
        missing_tools = []
        
        for tool_name in tool_names:
            if tool_name in self._tools:
                tools.append(self._tools[tool_name])
            else:
                missing_tools.append(tool_name)
                if strict:
                    raise ValueError(f"Tool '{tool_name}' not found in registered tools.")
        
        if missing_tools:
            print(f"⚠️  警告: 以下工具未注册: {', '.join(missing_tools)}")
        
        return tools
    
    def get_all_tools(self) -> list:
        """获取所有已注册的工具"""
        return list(self._tools.values())
    
    def get_tool_info(self, debug: bool = False) -> Dict[str, Any]:
        """获取工具信息用于调试"""
        info = {
            'total_count': len(self._tools),
            'tool_names': list(self._tools.keys())
        }
        
        if debug:
            info['tool_details'] = {}
            for name, tool in self._tools.items():
                if hasattr(tool, 'schema'):
                    info['tool_details'][name] = tool.schema
                else:
                    info['tool_details'][name] = str(type(tool))
                    
        return info
    
    @property
    def tools(self) -> Dict[str, Any]:
        """获取工具字典"""
        return self._tools.copy()
    
    async def clear(self):
        """清除所有已注册的工具"""
        self._tools.clear()
        try:
            await self._mcp_session_manager.close_all_sessions()
        except Exception as e:
            # Check if it's a common cleanup error
            error_msg = str(e).lower()
            common_cleanup_keywords = [
                'cancel', 'cancelled', 'scope', 'generator', 'wouldblock', 
                'subprocess', 'process', 'taskgroup'
            ]
            
            is_common_error = any(keyword in error_msg for keyword in common_cleanup_keywords)
            
            if is_common_error:
                # These are expected during cleanup, show less alarming message
                self._console.print(f"[dim yellow]ℹ️  会话清理完成（正常的清理过程）[/dim yellow]")
            else:
                # Unexpected error, show warning
                self._console.print(f"[yellow]⚠️  清理会话时出现错误: {e}[/yellow]")
    
    async def cleanup_session(self, session_id: str) -> bool:
        """清理指定的会话"""
        try:
            return await self._mcp_session_manager.close_session(session_id)
        except Exception as e:
            self._console.print(f"[red]⚠️  清理会话 {session_id} 失败: {e}[/red]")
            return False
    
    def get_session_info(self) -> dict:
        """获取会话信息"""
        return {
            'active_sessions': self._mcp_session_manager.list_sessions(),
            'session_count': len(self._mcp_session_manager)
        }
