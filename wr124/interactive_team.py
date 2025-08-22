"""
InteractiveTeam模块 - 专注于交互功能
"""
from typing import AsyncGenerator, Sequence, Optional, List
import asyncio

from autogen_core import CancellationToken
from autogen_agentchat.messages import BaseChatMessage, BaseAgentEvent, TextMessage
from autogen_agentchat.base import TaskResult
from rich.console import Console as RichConsole

from .agents.team_base import Team
from .interaction_handler import InteractionHandler


class InteractiveTeam:
    """
    交互式团队 - 专注于交互功能，基于Team进行扩展
    """
    
    def __init__(self, team: Team):
        self.team = team
        self.interaction_handler = InteractionHandler()
        self._console = RichConsole()
    
    def get_agent_info(self):
        """获取智能体信息"""
        return self.team.get_agent_info()
    
    def get_tools_info(self):
        """获取工具信息"""
        return self.team.get_tools_info()
    
    def set_main_agent(self, agent_param=None, markdown_file=None):
        """设置主智能体"""
        return self.team.set_main_agent(agent_param, markdown_file)
    
    def enable_interactive_mode(self, use_default_callback: bool = True) -> None:
        """启用交互模式"""
        self.interaction_handler.enable_interactive_mode(use_default_callback)
    
    def disable_interactive_mode(self) -> None:
        """禁用交互模式"""
        self.interaction_handler.disable_interactive_mode()
    
    @property
    def is_interactive(self) -> bool:
        """检查是否启用了交互模式"""
        return self.interaction_handler.is_interactive
    
    async def setup_keyboard_listener(self, cancellation_token: CancellationToken) -> None:
        """设置键盘监听器"""
        await self.interaction_handler.setup_keyboard_listener(cancellation_token)
    
    def stop_keyboard_listener(self) -> None:
        """停止键盘监听器"""
        self.interaction_handler.stop_keyboard_listener()
    
    async def run_stream(
        self,
        task: str | BaseChatMessage | Sequence[BaseChatMessage] | None = None,
        cancellation_token: CancellationToken | None = None,
        output_task_messages: bool = True,
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None]:
        """
        运行任务流，支持交互模式
        """
        # 获取初始任务
        current_task = await self._get_initial_task(task)
        if current_task is None:
            yield TaskResult(messages=[], stop_reason="无有效任务")
            return
        
        # 启动键盘监听器（在获取任务后）
        if cancellation_token:
            await self.setup_keyboard_listener(cancellation_token)
        
        # 主循环：执行任务和处理交互
        task_was_cancelled = False
        current_cancellation_token = cancellation_token
        
        while True:
            # 检查是否有取消令牌且已被取消
            if current_cancellation_token and current_cancellation_token.is_cancelled():
                task_was_cancelled = True
                self._console.print("\n[yellow]⏸️  检测到任务中断信号[/yellow]")
            else:
                # 执行当前任务
                try:
                    async for msg in self.team.run_stream(
                        task=current_task,
                        cancellation_token=current_cancellation_token,
                        output_task_messages=output_task_messages
                    ):
                        yield msg
                        # 在消息处理过程中再次检查取消状态
                        if current_cancellation_token and current_cancellation_token.is_cancelled():
                            task_was_cancelled = True
                            break
                except Exception as e:
                    # 处理MCP流式调用可能的异常
                    exception_name = type(e).__name__
                    if exception_name in ['BrokenResourceError', 'ClosedResourceError', 'CancelledError']:
                        # 这些异常通常由ESC键中断引起
                        self._console.print(f"[yellow]⏸️  任务执行被中断 ({exception_name})[/yellow]")
                        task_was_cancelled = True
                    else:
                        # 其他异常正常抛出
                        raise
            
            # 如果任务被取消或正常完成，进入交互处理
            if task_was_cancelled:
                self.interaction_handler.handle_task_interruption()
                task_was_cancelled = False
            elif not self.is_interactive:
                self._console.print("\n[yellow]任务完成，自动退出。[/yellow]")
                yield TaskResult(messages=[], stop_reason="任务完成")
                return
            
            # 交互模式：询问用户下一步操作
            action, next_task = await self.interaction_handler.handle_interactive_next()
            
            if action == 'exit':
                yield TaskResult(messages=[], stop_reason="用户选择退出")
                return
            elif action == 'continue' and next_task:
                current_task = next_task
                # 为新任务创建新的取消令牌并更新交互处理器
                if current_cancellation_token:
                    current_cancellation_token = CancellationToken()
                    self.interaction_handler.update_cancellation_token(current_cancellation_token)
                continue
            else:
                yield TaskResult(messages=[], stop_reason="处理用户输入失败")
                return
    
    async def _get_initial_task(self, task) -> str | None:
        """获取初始任务，处理交互模式下的用户输入"""
        if task is not None:
            # 将任务转换为字符串
            if isinstance(task, str):
                return task
            elif isinstance(task, BaseChatMessage):
                return str(task.content) if hasattr(task, 'content') else str(task)
            elif isinstance(task, Sequence):
                return ' '.join(str(t) for t in task)
            else:
                return str(task)
        
        # 使用交互处理器获取任务
        return await self.interaction_handler.get_initial_task(None)
