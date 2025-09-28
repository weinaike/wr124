"""
键盘监听工具，用于监听ESC键中断执行

修复说明：
- 区分真正的ESC按键和ANSI转义序列（如鼠标滚动产生的 ^[[A）
- ANSI转义序列以ESC字符开始，后面紧跟其他字符
- 真正的ESC按键是单独的ESC字符，后面没有紧跟其他字符
- 使用短暂的超时检查来区分这两种情况
"""
import asyncio
import sys
import termios
import tty
import threading
import select
import os
import subprocess
from typing import Callable, Optional
from autogen_core import CancellationToken
from rich.console import Console as RichConsole
from .terminal_manager import TerminalManager


class AsyncKeyboardListener:
    """异步版本的键盘监听器"""
    
    def __init__(self):
        self.console = RichConsole()
        self._listener_task: Optional[asyncio.Task] = None
        self._cancellation_source: Optional[CancellationToken] = None
        self._is_listening = False
        self._old_settings = None
        
    def set_cancellation_token(self, cancellation_token: CancellationToken):
        """设置要触发的取消令牌"""
        self._cancellation_source = cancellation_token
        
    async def start_listening(self):
        """开始异步监听ESC键"""
        if self._listener_task and not self._listener_task.done():
            return
            
        self.console.print("[dim]💡 提示: 按 ESC 键可中断当前任务执行[/dim]")
        self._is_listening = True
        self._listener_task = asyncio.create_task(self._async_listen())
    
    async def _async_listen(self):
        """异步监听ESC键"""
        try:
            # 使用线程来处理键盘输入
            loop = asyncio.get_event_loop()
            
            while self._is_listening:
                try:
                    # 在线程池中执行阻塞的键盘读取
                    char = await asyncio.wait_for(
                        loop.run_in_executor(None, self._read_single_char),
                        timeout=0.5  # 增加超时时间
                    )
                    
                    if char and ord(char) == 27:  # ESC字符
                        # 检查是否为ANSI转义序列的开始
                        if select.select([sys.stdin], [], [], 0.5) != ([], [], []):
                            # 有后续字符，可能是ANSI转义序列，消耗掉这些字符
                            try:
                                # 读取并丢弃ANSI转义序列的其余部分
                                while select.select([sys.stdin], [], [], 0.1) != ([], [], []):
                                    sys.stdin.read(1)
                            except:
                                pass
                            continue  # 不处理ANSI转义序列，继续监听
                        
                        # 没有后续字符，是真正的ESC按键
                        self.console.print("\n[yellow]⏸️  检测到 ESC 键，正在中断任务...[/yellow]")
                        if self._cancellation_source:
                            self._cancellation_source.cancel()
                        self._is_listening = False
                        break
                        
                except asyncio.TimeoutError:
                    # 超时是正常的，继续监听
                    continue
                except Exception as e:
                    # 忽略大部分异常，避免中断程序
                    continue
                    
        except asyncio.CancelledError:
            pass
        finally:
            self._restore_terminal()
    
    def _read_single_char(self) -> Optional[str]:
        """在线程中读取单个字符，使用非阻塞模式，能区分ESC键和ANSI转义序列"""
        try:
            # 检查是否有输入可读
            if select.select([sys.stdin], [], [], 0) == ([], [], []):
                return None
                
            # 保存原始终端设置
            if self._old_settings is None:
                self._old_settings = termios.tcgetattr(sys.stdin)
                
            try:
                tty.setraw(sys.stdin.fileno())
                char = sys.stdin.read(1)
                
                # 如果是ESC字符，检查是否为ANSI转义序列的开始
                if ord(char) == 27:
                    # 短暂等待检查是否有后续字符（ANSI转义序列）
                    if select.select([sys.stdin], [], [], 0.05) != ([], [], []):
                        # 有后续字符，可能是ANSI转义序列，消耗掉这些字符
                        try:
                            # 读取并丢弃ANSI转义序列的其余部分
                            while select.select([sys.stdin], [], [], 0.01) != ([], [], []):
                                sys.stdin.read(1)
                        except:
                            pass
                        return None  # 不处理ANSI转义序列
                    # 没有后续字符，是真正的ESC按键
                
                return char
            finally:
                if self._old_settings:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_settings)
        except:
            return None
    
    def _restore_terminal(self):
        """恢复终端设置"""
        if self._old_settings is not None:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_settings)
            except:
                pass
            self._old_settings = None
    
    def stop_listening(self):
        """停止监听"""
        self._is_listening = False
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
        self._restore_terminal()


class SimpleKeyboardListener:
    """简化版键盘监听器，使用线程"""
    
    def __init__(self):
        self.console = RichConsole()
        self._cancellation_source: Optional[CancellationToken] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._terminal_manager = TerminalManager.get_instance()
        
    def set_cancellation_token(self, cancellation_token: CancellationToken):
        """设置要触发的取消令牌"""
        self._cancellation_source = cancellation_token
        
    async def start_listening(self):
        """开始监听ESC键"""
        if self._thread and self._thread.is_alive():
            return
            
        self.console.print("[dim]💡 提示: 按 ESC 键可中断当前任务执行[/dim]")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._listen_thread, daemon=True)
        self._thread.start()
    
    def _listen_thread(self):
        """在独立线程中监听键盘"""
        old_settings = None
        try:
            # 保存当前终端设置（仅在监听期间）
            old_settings = termios.tcgetattr(sys.stdin)
            # 使用cbreak模式而不是raw模式，保留一些终端功能
            tty.setcbreak(sys.stdin.fileno())
            
            while not self._stop_event.is_set():
                try:
                    # 使用select检查是否有输入
                    if select.select([sys.stdin], [], [], 0.1) == ([], [], []):
                        continue
                        
                    char = sys.stdin.read(1)
                    if ord(char) == 27:  # ESC字符
                        # 检查是否为ANSI转义序列的开始
                        if select.select([sys.stdin], [], [], 0.05) != ([], [], []):
                            # 有后续字符，可能是ANSI转义序列，消耗掉这些字符
                            try:
                                # 读取并丢弃ANSI转义序列的其余部分
                                while select.select([sys.stdin], [], [], 0.01) != ([], [], []):
                                    sys.stdin.read(1)
                            except:
                                pass
                            continue  # 不处理ANSI转义序列，继续监听
                        
                        # 没有后续字符，是真正的ESC按键
                        self.console.print("\n[yellow]⏸️  检测到 ESC 键，正在中断任务...[/yellow]")
                        if self._cancellation_source:
                            self._cancellation_source.cancel()
                        # 立即恢复终端设置
                        self._restore_terminal_settings(old_settings)
                        break
                        
                except (KeyboardInterrupt, EOFError):
                    break
                except:
                    # 忽略其他异常
                    continue
                    
        except Exception as e:
            # 静默处理异常
            pass
        finally:
            # 确保恢复终端设置
            self._restore_terminal_settings(old_settings)
    
    def stop_listening(self):
        """停止监听"""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        
        # 确保终端恢复到正常状态
        self._terminal_manager.ensure_terminal_ready_for_input()
        
        # 额外等待一小段时间确保终端状态稳定
        import time
        time.sleep(0.1)
    
    def _restore_terminal_settings(self, old_settings):
        """恢复终端设置的辅助方法"""
        if old_settings is not None:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                # 额外确保回显功能开启
                attrs = termios.tcgetattr(sys.stdin)
                attrs[3] |= termios.ECHO  # 确保回显开启
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, attrs)
            except:
                # 如果直接恢复失败，使用终端管理器恢复
                self._terminal_manager.ensure_terminal_ready_for_input()
