import asyncio
import contextvars
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import AsyncGenerator

from mcp import ClientSession
from mcp.client.session import SamplingFnT
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from ._config import McpServerParams, SseServerParams, StdioServerParams, StreamableHttpServerParams


class McpSessionInfo:
    """Information about a single MCP session."""
    
    def __init__(self, session_task: asyncio.Task, session: ClientSession):
        self.session_task = session_task
        self.session = session
        self._cancelled = False
    
    async def close(self):
        """Cancel the session task and wait for cleanup."""
        if not self._cancelled:
            self._cancelled = True
            self.session_task.cancel()
            try:
                await self.session_task
            except asyncio.CancelledError:
                pass  # Expected when cancelling
            except Exception:
                pass  # Ignore cleanup exceptions


async def _run_session_context(
    server_params: McpServerParams,
    sampling_callback: SamplingFnT | None,
    session_ready: asyncio.Event,
    session_holder: list  # 用 list 来存储 session 以便外部访问
):
    """在独立的任务中运行会话上下文管理器"""
    try:
        async with create_mcp_server_session(server_params, sampling_callback) as session:
            # 初始化会话
            await session.initialize()
            
            # 将 session 传递给外部
            session_holder.append(session)
            session_ready.set()
            
            # 保持会话活跃直到任务被取消
            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                # 正常的取消，会话会被正确清理
                raise
    except Exception as e:
        # 设置事件以便外部知道会话创建失败
        session_ready.set()
        raise
class McpSessionManager:
    """MCP Session Manager for managing multiple MCP sessions."""
    
    def __init__(self):
        self._sessions: dict[str, McpSessionInfo] = {}
    
    async def create_session(
        self, 
        session_id: str,
        server_params: McpServerParams, 
        sampling_callback: SamplingFnT | None = None
    ) -> ClientSession:
        """Create and return an MCP client session with the given ID."""
        if session_id in self._sessions:
            raise RuntimeError(f"Session '{session_id}' already exists. Call close_session() first.")
        
        # 创建用于同步的事件和存储
        session_ready = asyncio.Event()
        session_holder = []
        
        # 在独立的任务中启动会话
        session_task = asyncio.create_task(
            _run_session_context(server_params, sampling_callback, session_ready, session_holder)
        )
        
        try:
            # 等待会话准备就绪
            await asyncio.wait_for(session_ready.wait(), timeout=30.0)
            
            if not session_holder:
                # 会话创建失败
                await session_task  # 这会重新抛出异常
                raise RuntimeError("Failed to create session")
            
            session = session_holder[0]
            
            # 存储会话信息
            session_info = McpSessionInfo(session_task, session)
            self._sessions[session_id] = session_info
            
            return session
            
        except asyncio.TimeoutError:
            # 会话创建超时
            session_task.cancel()
            try:
                await session_task
            except asyncio.CancelledError:
                pass
            raise ConnectionError(f"Session '{session_id}' creation timeout")
            try:
                await session_task
            except asyncio.CancelledError:
                pass
            raise ConnectionError(f"Session creation timeout for {session_id}. Check if MCP server is responsive.")
        except Exception as e:
            # 如果创建失败，确保清理任务
            session_task.cancel()
            try:
                await session_task
            except asyncio.CancelledError:
                pass
            raise
    
    def get_session(self, session_id: str) -> ClientSession | None:
        """Get an existing session by ID."""
        session_info = self._sessions.get(session_id)
        return session_info.session if session_info else None
    
    def list_sessions(self) -> list[str]:
        """List all active session IDs."""
        return list(self._sessions.keys())
    
    def has_session(self, session_id: str) -> bool:
        """Check if a session exists."""
        return session_id in self._sessions
    
    async def close_session(self, session_id: str) -> bool:
        """Close a specific session and clean up its resources."""
        session_info = self._sessions.get(session_id)
        if session_info is None:
            return False
        
        try:
            await session_info.close()
        except Exception:
            pass  # 忽略清理异常
        finally:
            # Always remove from sessions dict
            self._sessions.pop(session_id, None)
        
        return True
    
    async def close_all_sessions(self):
        """Close all sessions and clean up all resources."""
        session_ids = list(self._sessions.keys())
        if not session_ids:
            return
        
        # 并行关闭所有会话
        close_tasks = []
        for session_id in session_ids:
            session_info = self._sessions.get(session_id)
            if session_info:
                close_tasks.append(session_info.close())
        
        if close_tasks:
            # 等待所有会话关闭，但使用超时保护
            try:
                await asyncio.wait_for(
                    asyncio.gather(*close_tasks, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                pass  # 超时时强制清理
            except Exception:
                pass  # 忽略清理异常
        
        # 强制清空会话字典
        self._sessions.clear()
    
    def __len__(self) -> int:
        """Return the number of active sessions."""
        return len(self._sessions)


@asynccontextmanager
async def create_mcp_server_session(
    server_params: McpServerParams, sampling_callback: SamplingFnT | None = None
) -> AsyncGenerator[ClientSession, None]:
    """Create an MCP client session for the given server parameters."""
    if isinstance(server_params, StdioServerParams):
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(
                read_stream=read,
                write_stream=write,
                read_timeout_seconds=timedelta(seconds=server_params.read_timeout_seconds),
                sampling_callback=sampling_callback,
            ) as session:
                yield session
    elif isinstance(server_params, SseServerParams):
        async with sse_client(**server_params.model_dump(exclude={"type"})) as (read, write):
            async with ClientSession(
                read_stream=read,
                write_stream=write,
                read_timeout_seconds=timedelta(seconds=server_params.sse_read_timeout),
                sampling_callback=sampling_callback,
            ) as session:
                yield session
    elif isinstance(server_params, StreamableHttpServerParams):
        # Convert float seconds to timedelta for the streamablehttp_client
        params_dict = server_params.model_dump(exclude={"type"})
        params_dict["timeout"] = timedelta(seconds=server_params.timeout)
        params_dict["sse_read_timeout"] = timedelta(seconds=server_params.sse_read_timeout)

        async with streamablehttp_client(**params_dict) as (
            read,
            write,
            session_id_callback,  # type: ignore[assignment, unused-variable]
        ):
            # TODO: Handle session_id_callback if needed
            async with ClientSession(
                read_stream=read,
                write_stream=write,
                read_timeout_seconds=timedelta(seconds=server_params.sse_read_timeout),
                sampling_callback=sampling_callback,
            ) as session:
                yield session
