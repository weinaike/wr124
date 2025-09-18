"""
终端管理器 - 负责终端状态的保存和恢复
解决程序异常退出时的终端状态恢复问题
"""
import sys
import termios
import signal
import atexit
import os
from typing import Optional
from rich.console import Console as RichConsole


class TerminalManager:
    """终端管理器，负责保存和恢复终端设置"""
    
    _instance: Optional['TerminalManager'] = None
    _initialized = False
    
    def __new__(cls) -> 'TerminalManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if TerminalManager._initialized:
            return
            
        self.console = RichConsole()
        self._original_settings: Optional[list] = None
        self._signal_handlers_installed = False
        
        # 立即保存原始终端设置
        self._save_original_settings()
        
        # 安装信号处理器和退出处理器
        self._install_handlers()
        
        TerminalManager._initialized = True
    
    def _save_original_settings(self) -> None:
        """保存程序启动时的原始终端设置"""
        try:
            self._original_settings = termios.tcgetattr(sys.stdin)
        except Exception as e:
            # 如果无法保存设置，至少记录一下
            pass
    
    def _install_handlers(self) -> None:
        """安装信号处理器和退出处理器"""
        if self._signal_handlers_installed:
            return
            
        try:
            # 安装信号处理器
            signal.signal(signal.SIGINT, self._signal_handler)   # Ctrl+C
            signal.signal(signal.SIGTERM, self._signal_handler)  # 终止信号
            
            # 安装退出处理器
            atexit.register(self.restore_terminal)
            
            self._signal_handlers_installed = True
        except Exception:
            # 在某些环境中可能无法安装信号处理器
            pass
    
    def _signal_handler(self, signum: int, frame) -> None:
        """信号处理器"""
        self.restore_terminal()
        
        # 如果是 Ctrl+C，显示友好的退出信息
        if signum == signal.SIGINT:
            self.console.print("\n[yellow]程序被用户中断，正在清理...[/yellow]")
        else:
            self.console.print(f"\n[yellow]收到终止信号 {signum}，正在清理...[/yellow]")
        
        # 恢复默认信号处理器并重新发送信号
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)
    
    def restore_terminal(self) -> None:
        """恢复终端到原始状态"""
        if self._original_settings is None:
            # 如果没有保存的设置，使用通用的恢复方法
            self._force_restore_terminal()
            return
        
        try:
            # 恢复到保存的原始设置
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._original_settings)
        except Exception:
            # 如果恢复失败，使用强制恢复
            self._force_restore_terminal()
    
    def _force_restore_terminal(self) -> None:
        """强制恢复终端到正常状态"""
        try:
            # 方法1: 使用stty命令
            import subprocess
            subprocess.run(['stty', 'echo', 'icanon'], 
                         check=False, stderr=subprocess.DEVNULL)
            subprocess.run(['stty', 'sane'], 
                         check=False, stderr=subprocess.DEVNULL)
        except:
            try:
                # 方法2: 直接使用系统命令
                os.system('stty sane 2>/dev/null')
            except:
                try:
                    # 方法3: 使用termios直接设置
                    attrs = termios.tcgetattr(sys.stdin)
                    attrs[3] |= (termios.ECHO | termios.ICANON)
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, attrs)
                except:
                    pass
        
        # 发送终端重置序列
        try:
            sys.stdout.write('\033[0m')  # 重置终端属性
            sys.stdout.flush()
        except:
            pass
    
    def ensure_terminal_ready_for_input(self) -> None:
        """确保终端准备好接收正常输入"""
        try:
            import subprocess
            # 确保终端处于标准输入模式
            subprocess.run(['stty', 'echo', 'icanon'], 
                         check=False, stderr=subprocess.DEVNULL)
                
        except Exception:
            pass
    
    @classmethod
    def get_instance(cls) -> 'TerminalManager':
        """获取终端管理器实例"""
        if cls._instance is None:
            cls._instance = TerminalManager()
        return cls._instance
