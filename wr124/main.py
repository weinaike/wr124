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
from typing import AsyncGenerator
import uuid
from rich.console import Console as RichConsole
from autogen_core import CancellationToken
from datetime import datetime


from .config_manager import ConfigManager
from .tool_manager import ToolManager
from .interactive_team import InteractiveTeam
from .agents.team_base import Team
from .telemetry_setup import TelemetrySetup, trace
from .util import print_tools_info
from .terminal_manager import TerminalManager  # 导入终端管理器
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import BaseChatMessage, BaseAgentEvent
from autogen_agentchat.base import TaskResult
from .filesystem import tool_mapping
from .session.session_state_manager import SessionStateManager, SessionParam
from .mcp import create_mcp_server_session, mcp_server_tools


async def run_team(args: argparse.Namespace) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None]:
    # 立即初始化终端管理器，确保终端状态被保存
    terminal_manager = TerminalManager.get_instance()      
    
    console = RichConsole()
    session_id = str(uuid.uuid4())
    if args.session_id:
        session_id = args.session_id

    # 处理 project_id：如果未提供，使用当前目录名
    if args.project_id is None:
        current_path = Path.cwd()
        args.project_id = current_path.name
        console.print(f"[dim]ℹ[/dim]  未指定 project_id，使用当前目录名: [bold cyan]{args.project_id}[/bold cyan]")
    
    try:
        # 初始化配置管理器
        config_manager = ConfigManager(session_id=session_id, 
                                       env_file=args.env_file, 
                                       project_id=args.project_id,
                                       config_profile=args.config_file)
        
        # 初始化遥测
        telemetry = TelemetrySetup(config_manager.project_id)
        tracer = telemetry.initialize()
        
        # 创建模型客户端        
        model_client = config_manager.get_model_client(openai=not args.claude)
        # 创建Team实例
        team = Team(model_client)        
        
        # 初始化工具管理器并注册工具
        tool_manager = ToolManager()
        mcp_servers = config_manager.get_mcp_servers()

        # 启动搜索智能体工具

        await team.set_enable_search_agent_tool()
        # 注册工具
        tools={}
        for name, parm in mcp_servers.items():
            tools = await tool_manager.register_tools(name, parm)
        print_tools_info(tools, debug=args.debug)
        console.print(f"[cyan]🔧 注册工具{len(tool_manager.get_all_tools())}...[/cyan]")
        team.register_tools(tool_manager.get_all_tools())
        
        # 第二步： 注册会话状态管理器
        parm = config_manager.get_session_server()
        if parm is not None:
            manager = SessionStateManager(parm)
            if manager.is_connected():
                team.register_state_manager(manager)

        # 第三步：根据参数设置主智能体
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
        
        # 第四步：
        if args.resume:
            team.set_resume(True)

        # 如果需要交互模式，创建InteractiveTeam
        if args.interactive or args.task is None:
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
            with tracer.start_as_current_span(name=config_manager.session_id):
                async for message in execution_team.run_stream(
                    task=args.task,
                    cancellation_token=cancellation_token
                ):
                    yield message

        finally:
            # 清理工具管理器中的会话
            await tool_manager.clear()
            # 清理键盘监听器并恢复终端状态（仅对InteractiveTeam）
            if isinstance(execution_team, InteractiveTeam):
                execution_team.stop_keyboard_listener()
            # 使用终端管理器恢复终端状态
            terminal_manager.restore_terminal()
   
    except Exception as e:
        console.print(f"[red]程序执行出错: {e}[/red]")
        import traceback
        if args.debug:
            console.print("[red]详细错误信息:[/red]")
            console.print(traceback.format_exc())
        # 确保即使出错也恢复终端状态
        terminal_manager.restore_terminal()
        raise

def run():
    """命令行脚本入口点"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="运行Agent，执行指定任务。")
    parser.add_argument("-t", "--task", type=str, help="要执行的任务（如未提供，将启用交互模式）")
    parser.add_argument("-p", "--project_id", type=str, help="项目ID（如未提供，使用当前目录名）")
    parser.add_argument("-e", "--env_file", type=str, help="环境变量文件路径")
    parser.add_argument("-i", "--interactive", action="store_true", help="在任务完成后启用交互式用户输入")
    parser.add_argument("-d", "--debug", action="store_true", help="启用调试模式")
    parser.add_argument("-a", "--agent", type=str, help="Agent配置文件路径（支持markdown格式）")
    parser.add_argument("-r", "--resume", action="store_true", help="是否从上次中断的地方恢复")
    parser.add_argument("-s", "--session_id", type=str, help="会话ID")
    parser.add_argument("-c", "--config_file", type=str, help="配置文件中的配置档案名称")
    parser.add_argument("--claude", action="store_true", help="使用Claude模型（默认使用OpenAI模型）")
    args = parser.parse_args()    

    # 环境变量文件查询逻辑：配置 -> 启动目录的.env -> 用户目录下的.env -> 空
    if args.env_file is None:
        # 检查当前工作目录下是否有 .env 文件
        current_dir_env = Path.cwd() / ".env"
        if current_dir_env.exists():
            args.env_file = str(current_dir_env)
        else:
            # 检查用户主目录下是否有 .env 文件
            user_dir_env = Path.home() / ".env"
            if user_dir_env.exists():
                args.env_file = str(user_dir_env)
            else:
                # 都不存在则保持为空
                args.env_file = None

    # 默认模式：直接使用Console处理
    async def console_run():
        await Console(run_team(args))
    asyncio.run(console_run())

if __name__ == "__main__":
    run()
