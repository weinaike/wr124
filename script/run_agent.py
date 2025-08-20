"""
Run Agent 脚本 - 重构版本
CLI入口和程序启动控制，专注于配置和协调
支持AgentParam配置文件和传统参数
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
from wr124.interactive_team import InteractiveTeam
from wr124.agents.team_base import Team
from wr124.telemetry_setup import TelemetrySetup
from wr124.util import print_tools_info
from autogen_agentchat.ui import Console
from wr124.filesystem import tool_mapping


def ensure_clean_terminal():
    """确保终端处于干净状态"""
    try:
        import subprocess
        subprocess.run(['stty', 'echo', 'icanon'], 
                     check=False, stderr=subprocess.DEVNULL)
    except:
        pass


async def main():
    """主函数 - 重构版本，支持AgentParam配置"""
    # 确保终端处于正确状态
    ensure_clean_terminal()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="运行Agent，执行指定任务。")
    parser.add_argument("-t", "--task", type=str, help="要执行的任务（如未提供，将启用交互模式）")
    parser.add_argument("-p", "--project_id", type=str, help="项目ID（如未提供，使用当前目录名）")
    parser.add_argument("-e", "--env_file", type=str, default="./script/.env", help="环境变量文件路径")
    parser.add_argument("-i", "--interactive", action="store_true", help="在任务完成后启用交互式用户输入")
    parser.add_argument("-d", "--debug", action="store_true", help="启用调试模式")
    parser.add_argument("-a", "--agent", type=str, help="Agent配置文件路径（支持markdown格式）")
    args = parser.parse_args()
    
    console = RichConsole()
    
    # 处理 project_id：如果未提供，使用当前目录名
    if args.project_id is None:
        current_path = Path.cwd()
        args.project_id = current_path.name
        console.print(f"[dim]ℹ[/dim]  未指定 project_id，使用当前目录名: [bold cyan]{args.project_id}[/bold cyan]")
    
    try:
        # 初始化配置管理器
        config_manager = ConfigManager(env_file=args.env_file, project_id=args.project_id)
        
        # 初始化遥测
        telemetry = TelemetrySetup(config_manager.project_id)
        tracer = telemetry.initialize()
        
        # 初始化工具管理器并注册工具
        tool_manager = ToolManager()
        mcp_servers = config_manager.get_mcp_servers()
        
        # 注册工具
        # tools = await tool_manager.register_tools(tool_mapping)
        tools = await tool_manager.register_tools(mcp_servers['base_tools'])
        tools = await tool_manager.register_tools(mcp_servers['task'])
        
        if args.debug:
            print_tools_info(tools, debug=True)
        
        # 创建模型客户端
        model_client = config_manager.get_model_client()
        
        # 创建Team实例
        team = Team(model_client)
        
        # 第一步：注册工具到Team
        console.print("[cyan]🔧 注册工具...[/cyan]")
        team.register_tools(tool_manager.get_all_tools())
        
        # 第二步：根据参数设置主智能体
        if args.agent:
            # 使用外部配置文件
            agent_config_path = Path(args.agent)
            if not agent_config_path.exists():
                console.print(f"[red]错误: Agent配置文件不存在: {args.agent}[/red]")
                return
            
            console.print(f"[cyan]📋 使用外部Agent配置文件: {args.agent}[/cyan]")
            team.set_main_agent_from_config(str(agent_config_path))            
        else:
            # 使用默认配置（general_assistant.md）
            console.print("[cyan]📋 使用默认Agent配置（general_assistant.md）[/cyan]")
            team.set_main_agent()  # 使用默认配置
        
        # 如果需要交互模式，创建InteractiveTeam
        if not args.interactive or args.task is None:
            console.print("[yellow]📱 启用交互模式[/yellow]")
            interactive_team = InteractiveTeam(team)
            interactive_team.enable_interactive_mode(use_default_callback=True)
            execution_team = interactive_team
        else:
            execution_team = team
        
        # 创建取消令牌
        cancellation_token = CancellationToken()
        
        try:
            # 执行任务
            session_id = uuid.uuid4()
            with tracer.start_as_current_span(name=str(session_id)):
                await Console(execution_team.run_stream(
                    task=args.task,
                    cancellation_token=cancellation_token
                ))
        finally:
            # 清理键盘监听器并恢复终端状态（仅对InteractiveTeam）
            if hasattr(execution_team, 'stop_keyboard_listener'):
                execution_team.stop_keyboard_listener()
            ensure_clean_terminal()
            
    except Exception as e:
        console.print(f"[red]程序执行出错: {e}[/red]")
        import traceback
        if args.debug:
            console.print("[red]详细错误信息:[/red]")
            console.print(traceback.format_exc())
        # 确保即使出错也恢复终端状态
        ensure_clean_terminal()
        raise


if __name__ == "__main__":
    asyncio.run(main())
