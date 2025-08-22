"""
Run Agent 脚本 - CLI入口和程序启动控制
负责命令行参数解析、配置管理、各模块协调
"""
import argparse
import os
import sys
import asyncio
from pathlib import Path
import uuid
from rich.console import Console as RichConsole
from autogen_core import CancellationToken

# 添加项目根目录到Python路径
current_dir = os.getcwd()
sys.path.insert(0, str(current_dir))

from wr124.config_manager import ConfigManager
from wr124.tool_manager import ToolManager
from wr124.interaction_handler import InteractionHandler
from wr124.telemetry_setup import TelemetrySetup
from wr124.agents.team_base import Team
from wr124.util import print_tools_info
from wr124.terminal_manager import TerminalManager  # 导入终端管理器
from autogen_agentchat.ui import Console
from wr124.filesystem import tool_mapping


class AgentRunner:
    """Agent 运行器 - 协调各个模块"""
    
    def __init__(self, args):
        self.args = args
        self.console = RichConsole()
        
        # 立即初始化终端管理器，确保终端状态被保存
        self.terminal_manager = TerminalManager.get_instance()
        
        # 初始化各个管理器
        self.config_manager = ConfigManager(
            env_file=args.env_file,
            project_id=args.project_id
        )
        self.tool_manager = ToolManager()
        self.interaction_handler = InteractionHandler()
        self.telemetry_setup = TelemetrySetup(self.config_manager.project_id)
        
        # 创建团队
        model_client = self.config_manager.get_model_client()
        self.team = Team(model_client)
    
    async def setup_tools(self) -> None:
        """设置工具"""
        # 获取MCP服务器配置
        mcp_servers = self.config_manager.get_mcp_servers()
        
        # 注册各种工具
        # tools = await self.tool_manager.register_tools(tool_mapping)
        tools = await self.tool_manager.register_tools(mcp_servers['base_tools'])
        tools = await self.tool_manager.register_tools(mcp_servers['task'])
        
        # 显示工具信息
        if self.args.debug:
            print_tools_info(tools, debug=True)
        
        # 使用工具初始化团队
        all_tools = self.tool_manager.get_all_tools()
        self.team.initialize_with_tools(tools=all_tools)
    
    async def setup_interaction(self, cancellation_token: CancellationToken) -> None:
        """设置交互模式"""
        if self.args.interactive:
            self.interaction_handler.enable_interactive_mode(use_default_callback=True)
        
        # 设置键盘监听器
        await self.interaction_handler.setup_keyboard_listener(cancellation_token)
    
    async def run(self) -> None:
        """运行主程序"""
        try:
            # 初始化遥测
            tracer = self.telemetry_setup.initialize()
            
            # 设置工具
            await self.setup_tools()
            
            # 创建取消令牌
            cancellation_token = CancellationToken()
            
            # 设置交互模式
            await self.setup_interaction(cancellation_token)
            
            # 处理初始任务
            initial_task = await self._get_initial_task()
            if initial_task is None:
                self.console.print("[yellow]没有任务要执行，退出程序。[/yellow]")
                return
            
            # 执行主循环
            await self._run_main_loop(initial_task, cancellation_token, tracer)
            
        finally:
            # 清理资源
            self.interaction_handler.stop_keyboard_listener()
    
    async def _get_initial_task(self) -> str | None:
        """获取初始任务"""
        if self.args.task:
            return self.args.task
        
        # 如果没有提供任务，使用交互处理器获取
        return await self.interaction_handler.get_initial_task(None)
    
    async def _run_main_loop(self, initial_task: str, cancellation_token: CancellationToken, tracer) -> None:
        """运行主循环"""
        current_task = initial_task
        task_was_cancelled = False
        current_cancellation_token = cancellation_token
        
        while True:
            # 检查是否有取消令牌且已被取消
            if current_cancellation_token and current_cancellation_token.is_cancelled():
                task_was_cancelled = True
                self.console.print("\n[yellow]⏸️  检测到任务中断信号[/yellow]")
            else:
                # 执行当前任务
                session_id = uuid.uuid4()
                with tracer.start_as_current_span(name=str(session_id)):
                    await Console(self.team.run_stream(
                        task=current_task,
                        cancellation_token=current_cancellation_token
                    ))
                
                # 检查是否在执行过程中被取消
                if current_cancellation_token and current_cancellation_token.is_cancelled():
                    task_was_cancelled = True
            
            # 处理任务中断或完成后的逻辑
            if task_was_cancelled:
                self.interaction_handler.handle_task_interruption()
                task_was_cancelled = False
            elif not self.interaction_handler.is_interactive:
                self.console.print("\n[yellow]任务完成，自动退出。[/yellow]")
                return
            
            # 交互模式：询问用户下一步操作
            action, next_task = await self.interaction_handler.handle_interactive_next()
            
            if action == 'exit':
                self.console.print("\n[green]用户选择退出程序。[/green]")
                return
            elif action == 'continue' and next_task:
                current_task = next_task
                # 为新任务创建新的取消令牌并更新交互处理器
                if current_cancellation_token:
                    current_cancellation_token = CancellationToken()
                    self.interaction_handler.update_cancellation_token(current_cancellation_token)
                continue
            else:
                self.console.print("\n[red]处理用户输入失败，退出程序。[/red]")
                return


async def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="运行Agent，执行指定任务。")
    parser.add_argument("-t", "--task", type=str, help="要执行的任务（如未提供，将启用交互模式）")
    parser.add_argument("-p", "--project_id", type=str, help="项目ID（如未提供，使用当前目录名）")
    parser.add_argument("-e", "--env_file", type=str, default="./script/.env", help="环境变量文件路径")
    parser.add_argument("-i", "--interactive", action="store_true", help="在任务完成后启用交互式用户输入")
    parser.add_argument("-d", "--debug", action="store_true", help="启用调试模式")
    args = parser.parse_args()
    
    # 处理 project_id：如果未提供，使用当前目录名
    if args.project_id is None:
        current_path = Path.cwd()
        args.project_id = current_path.name
        console = RichConsole()
        console.print(f"[dim]ℹ[/dim]  未指定 project_id，使用当前目录名: [bold cyan]{args.project_id}[/bold cyan]")
    
    # 创建并运行Agent
    runner = AgentRunner(args)
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
