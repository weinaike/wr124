"""
交互处理模块
负责用户输入处理、交互模式管理和键盘监听
"""
from typing import Callable, Awaitable, Optional, Tuple
from autogen_core import CancellationToken
from rich.console import Console as RichConsole
from .util import default_user_input_callback
from .keyboard_listener import SimpleKeyboardListener
from .terminal_manager import TerminalManager


class InteractionHandler:
    """交互处理器"""
    
    def __init__(self):
        self._interactive = False
        self._user_input_callback: Optional[Callable[[], Awaitable[Tuple[str, str | None]]]] = None
        self._keyboard_listener: Optional[SimpleKeyboardListener] = None
        self._console = RichConsole()
        self._keyboard_listener_was_active = False  # 用于跟踪键盘监听器状态
        self._terminal_manager = TerminalManager.get_instance()  # 获取终端管理器
    
    def enable_interactive_mode(self, use_default_callback: bool = True) -> None:
        """
        启用交互模式
        
        Args:
            use_default_callback: 是否使用默认的用户输入回调
        """
        self._interactive = True
        if use_default_callback:
            self._user_input_callback = default_user_input_callback
    
    def disable_interactive_mode(self) -> None:
        """禁用交互模式"""
        self._interactive = False
        self._user_input_callback = None
    
    def register_user_input_callback(
        self, 
        callback: Callable[[], Awaitable[Tuple[str, str | None]]]
    ) -> None:
        """
        注册用户输入回调函数
        
        Args:
            callback: 回调函数，应返回 (action, task) 元组
                     - action: 'continue' 继续新任务，'exit' 退出
                     - task: action为'continue'时的新任务字符串，为'exit'时为None
        """
        self._user_input_callback = callback
    
    async def setup_keyboard_listener(self, cancellation_token: CancellationToken) -> None:
        """设置并启动键盘监听器"""
        self._keyboard_listener = SimpleKeyboardListener()
        self._keyboard_listener.set_cancellation_token(cancellation_token)
        await self._keyboard_listener.start_listening()
    
    def update_cancellation_token(self, cancellation_token: CancellationToken) -> None:
        """更新取消令牌"""
        if self._keyboard_listener:
            self._keyboard_listener.set_cancellation_token(cancellation_token)
    
    def stop_keyboard_listener(self) -> None:
        """停止键盘监听器"""
        if self._keyboard_listener:
            self._keyboard_listener.stop_listening()
    
    def _temporarily_stop_keyboard_listener(self) -> None:
        """临时停止键盘监听器，保存状态以便恢复"""
        self._keyboard_listener_was_active = False
        if self._keyboard_listener:
            # 检查键盘监听器是否正在运行
            if hasattr(self._keyboard_listener, '_thread') and self._keyboard_listener._thread and self._keyboard_listener._thread.is_alive():
                self._keyboard_listener_was_active = True
                self._keyboard_listener.stop_listening()
                
                # 额外确保终端状态正确恢复
                self._ensure_terminal_input_ready()
    
    def _resume_keyboard_listener(self) -> None:
        """恢复键盘监听器（如果之前有运行）"""
        # 键盘监听器的生命周期由上层管理，这里只需要确保终端状态正常
        if self._keyboard_listener_was_active:
            # 确保终端状态恢复正常，特别是对中文字符的支持
            self._ensure_terminal_input_ready()
            self._keyboard_listener_was_active = False
    
    def _ensure_terminal_input_ready(self) -> None:
        """确保终端准备好接收正常输入，特别是支持中文字符"""
        self._terminal_manager.ensure_terminal_ready_for_input()
    
    async def get_initial_task(self, task: Optional[str]) -> Optional[str]:
        """
        获取初始任务，处理交互模式下的用户输入
        
        Args:
            task: 传入的任务，如果为None且未启用交互模式，将自动启用
            
        Returns:
            任务字符串或None（退出）
        """
        if task is not None:
            return task
        
        if not self.is_interactive:
            self._console.print("\n[cyan]提醒：未提供任务，默认启动交互模式。[/cyan]")
            self.enable_interactive_mode(True)
        else:
            self._console.print("\n[cyan]欢迎使用 wr124 交互模式！[/cyan]")
        
        try:
            # 临时停止键盘监听器，避免终端模式冲突
            self._temporarily_stop_keyboard_listener()
            
            action, first_task = await self._user_input_callback()
            if action == 'exit':
                self._console.print("\n[yellow]用户选择退出。[/yellow]")
                return None
            elif action == 'continue' and first_task:
                return first_task
            else:
                self._console.print("\n[red]无效输入，退出程序。[/red]")
                return None
        except Exception as e:
            self._console.print(f"\n[red]获取用户输入时发生错误: {e}，退出程序。[/red]")
            return None
        finally:
            # 恢复键盘监听器
            self._resume_keyboard_listener()
    
    async def handle_interactive_next(self) -> Tuple[str, Optional[str]]:
        """
        处理交互模式下的下一步操作
        
        Returns:
            (action, task) 元组：
            - ('exit', None): 用户选择退出
            - ('continue', task): 用户选择继续执行新任务
            - ('error', None): 发生错误
        """
        try:
            # 临时停止键盘监听器，避免终端模式冲突
            self._temporarily_stop_keyboard_listener()
            
            action, next_task = await self._user_input_callback()
            if action == 'exit':
                self._console.print("\n[green]用户选择退出程序。[/green]")
                return 'exit', None
            elif action == 'continue' and next_task:
                self._console.print(f"\n[blue]开始执行新任务: {next_task}[/blue]")
                return 'continue', next_task
            else:
                self._console.print("\n[red]无效的回调返回值，退出程序。[/red]")
                return 'error', None
        except Exception as e:
            self._console.print(f"\n[red]处理用户输入时发生错误: {e}，退出程序。[/red]")
            return 'error', None
        finally:
            # 恢复键盘监听器
            self._resume_keyboard_listener()
    
    def handle_task_interruption(self) -> None:
        """处理任务中断情况"""
        self._console.print("[cyan]📝 任务已中断，您可以选择继续执行新任务或退出程序。[/cyan]")
        # 强制启用交互模式，让用户选择下一步
        if not self.is_interactive:
            self.enable_interactive_mode(True)
            self._console.print("[dim]💡 已自动启用交互模式[/dim]")
    
    @property
    def is_interactive(self) -> bool:
        """检查是否启用了交互模式"""
        return self._interactive and self._user_input_callback is not None
