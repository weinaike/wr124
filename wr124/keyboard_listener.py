"""
键盘监听工具，用于监听ESC键中断执行
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
                    
                    if char and ord(char) == 27:  # ESC键
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
        """在线程中读取单个字符，使用非阻塞模式"""
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
            # 保存原始终端设置
            old_settings = termios.tcgetattr(sys.stdin)
            # 使用cbreak模式而不是raw模式，保留一些终端功能
            tty.setcbreak(sys.stdin.fileno())
            
            while not self._stop_event.is_set():
                try:
                    # 使用select检查是否有输入
                    if select.select([sys.stdin], [], [], 0.1) == ([], [], []):
                        continue
                        
                    char = sys.stdin.read(1)
                    if ord(char) == 27:  # ESC键
                        self.console.print("\n[yellow]⏸️  检测到 ESC 键，正在中断任务...[/yellow]")
                        if self._cancellation_source:
                            self._cancellation_source.cancel()
                        # 立即开始恢复终端状态
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
        
        # 立即强制恢复终端设置
        self._force_restore_terminal()
        
        # 额外等待一小段时间确保终端状态稳定
        import time
        time.sleep(0.1)
    
    def _force_restore_terminal(self):
        """强制恢复终端到正常状态"""
        try:
            # 方法1: 直接恢复到正常模式
            import subprocess
            subprocess.run(['stty', 'echo', 'icanon'], check=False, stderr=subprocess.DEVNULL)
            # 额外确保终端完全恢复
            subprocess.run(['stty', 'sane'], check=False, stderr=subprocess.DEVNULL)
        except:
            try:
                # 方法2: 使用系统命令重置终端
                os.system('stty sane 2>/dev/null')
            except:
                try:
                    # 方法3: 尝试使用termios直接设置
                    attrs = termios.tcgetattr(sys.stdin)
                    attrs[3] |= (termios.ECHO | termios.ICANON)  # 启用回显和标准输入处理
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, attrs)
                except:
                    pass
        
        # 额外步骤：发送终端重置序列
        try:
            # 发送ANSI重置序列
            sys.stdout.write('\033c')  # 完全重置终端
            sys.stdout.flush()
        except:
            pass
    
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
                # 如果直接恢复失败，使用强制恢复
                self._force_restore_terminal()
