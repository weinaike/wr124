
from autogen_ext.tools.mcp import StdioMcpToolAdapter
from typing import List, Optional, Union, Callable, get_type_hints
from rich.console import Console as RichConsole
from pydantic import BaseModel, Field
import yaml
import inspect
import sys
import os
import subprocess


def ensure_terminal_ready_for_input():
    """确保终端准备好接收输入，特别是中文字符"""
    try:
        # 设置终端为标准模式
        subprocess.run(['stty', 'echo', 'icanon'], 
                     check=False, stderr=subprocess.DEVNULL, timeout=2)
        
        # 设置UTF-8编码
        os.environ['LANG'] = os.environ.get('LANG', 'en_US.UTF-8')
        os.environ['LC_ALL'] = os.environ.get('LC_ALL', 'en_US.UTF-8')
        
        # 重新配置标准输入输出的编码
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stdin, 'reconfigure'):
            sys.stdin.reconfigure(encoding='utf-8')
            
    except Exception:
        # 备用方案
        try:
            os.system('stty sane 2>/dev/null')
        except:
            pass


def safe_input(prompt: str) -> str:
    """安全的输入函数，确保中文字符正确处理"""
    ensure_terminal_ready_for_input()
    
    try:
        # 使用readline模块提供更好的输入体验
        import readline
        # 设置readline为UTF-8模式
        readline.set_startup_hook(lambda: readline.insert_text(''))
    except ImportError:
        pass
    
    try:
        return input(prompt).strip()
    except (UnicodeDecodeError, UnicodeEncodeError):
        # 如果遇到编码问题，尝试不同的处理方式
        print("检测到字符编码问题，请重新输入：")
        return input(prompt).strip()
    

async def default_user_input_callback() -> tuple[str, str | None]:
    """
    Default user input callback function for terminal interaction.
    Returns tuple (action, task) where:
    - action: 'continue' to continue with new task, 'exit' to exit
    - task: new task string if action is 'continue', None if action is 'exit'
    """
    try:
        # 确保终端状态正确
        ensure_terminal_ready_for_input()
        
        while True:
            print("\n" + "="*50)
            print("请选择下一步操作：")
            print("1. 输入新任务继续执行")
            print("2. 退出程序")
            print("="*50)
            
            user_input = safe_input("请选择 (1/2) 或直接输入任务: ")
            
            if user_input in ['1']:
                new_task = safe_input("请输入任务: ")
                if new_task:
                    return ('continue', new_task)
                else:
                    print("任务不能为空，请重新输入。")
                    continue
            elif user_input in ['2', 'exit', 'quit', '退出']:
                return ('exit', None)
            elif user_input.lower() in ['n', 'no', '否']:
                return ('exit', None)
            elif user_input.lower() in ['y', 'yes', '是']:
                new_task = safe_input("请输入任务: ")
                if new_task:
                    return ('continue', new_task)
                else:
                    print("任务不能为空，请重新输入。")
                    continue
            elif len(user_input) > 2:  # 假设直接输入的是新任务
                return ('continue', user_input)
            else:
                print("无效输入，请重新选择。")
                
    except (KeyboardInterrupt, EOFError):
        print("\n\n用户中断，退出程序。")
        return ('exit', None)
        return ('exit', None)

def print_tools(tools: List[StdioMcpToolAdapter|Callable]) -> None:
    """
    Print available MCP tools and their parameters in a formatted way.
    
    Args:
        tools: List containing StdioMcpToolAdapter objects or Callable functions
    """
    console = RichConsole()
    console.print("\n[bold blue]📦 Loaded Tools:[/bold blue]\n")

    if not tools:
        console.print("[yellow]No tools available[/yellow]")
        return

    # Separate MCP tools and function tools
    mcp_tools = []
    function_tools = []
    
    for tool in tools:
        if hasattr(tool, 'schema'):
            # StdioMcpToolAdapter
            mcp_tools.append(tool)
        elif callable(tool):
            # Function
            function_tools.append((getattr(tool, '__name__', str(tool)), tool))
        else:
            console.print(f"[yellow]⚠️ Skipping unsupported tool type: {type(tool)}[/yellow]")

    # Print MCP tools first
    if mcp_tools:
        _print_mcp_tools(console, mcp_tools)
    
    # Then print function tools
    if function_tools:
        _print_function_tools(console, function_tools)


def print_tools_info(tools_dict: dict, debug: bool = False) -> None:
    """
    Print tools information based on debug mode.
    
    Args:
        tools_dict: Dictionary of tools (typically from team.register_tools())
        debug: If True, show detailed tool information; if False, show only tool names
    """
    if debug:
        print_tools(list(tools_dict.values()))
    else:
        console = RichConsole()
        console.print('tools:', list(tools_dict.keys()))


def _print_mcp_tools(console: RichConsole, tools: List[StdioMcpToolAdapter]) -> None:
    """Print MCP tools with their schema information."""
    for tool in tools:
        # Tool name and description
        console.print(f"[bold green]🔧 {tool.schema.get('name', 'Unnamed Tool')}[/bold green]")
        if description := tool.schema.get('description'):
            console.print(f"[italic]{description}[/italic]\n")

        # Parameters section
        if params := tool.schema.get('parameters'):
            console.print("[yellow]Parameters:[/yellow]")
            if properties := params.get('properties', {}):
                required_params = params.get('required', [])
                for prop_name, prop_details in properties.items():
                    required_mark = "[red]*[/red]" if prop_name in required_params else ""
                    param_type = prop_details.get('type', 'any')
                    console.print(f"  • [cyan]{prop_name}{required_mark}[/cyan]: {param_type}")
                    if param_desc := prop_details.get('description'):
                        console.print(f"    [dim]{param_desc}[/dim]")
        console.print("─" * 60 + "\n")


def _print_function_tools(console: RichConsole, tool_items) -> None:
    """Print function-based tools with their signature and docstring information."""
    for tool_name, tool_func in tool_items:
        if not callable(tool_func):
            continue
            
        # Tool name and description
        console.print(f"[bold green]🔧 {tool_name}[/bold green]")
        
        # Get function docstring
        docstring = inspect.getdoc(tool_func)
        if docstring:
            # Extract first line as description
            first_line = docstring.split('\n')[0].strip()
            console.print(f"[italic]{first_line}[/italic]\n")

        # Get function signature and type hints
        try:
            sig = inspect.signature(tool_func)
            type_hints = get_type_hints(tool_func)
            
            if sig.parameters:
                console.print("[yellow]Parameters:[/yellow]")
                for param_name, param in sig.parameters.items():
                    # Determine if parameter is required
                    required_mark = "" if param.default != inspect.Parameter.empty else "[red]*[/red]"
                    
                    # Get parameter type
                    param_type = "any"
                    if param_name in type_hints:
                        param_type = str(type_hints[param_name]).replace("typing.", "")
                    elif param.annotation != inspect.Parameter.empty:
                        if hasattr(param.annotation, '__metadata__'):
                            # Handle Annotated types
                            param_type = str(param.annotation.__origin__.__name__ if hasattr(param.annotation, '__origin__') else param.annotation)
                        else:
                            param_type = str(param.annotation).replace("typing.", "")
                    
                    console.print(f"  • [cyan]{param_name}{required_mark}[/cyan]: {param_type}")
                    
                    # Extract parameter description from Annotated metadata
                    if hasattr(param.annotation, '__metadata__') and param.annotation.__metadata__:
                        param_desc = param.annotation.__metadata__[0]
                        console.print(f"    [dim]{param_desc}[/dim]")
                    
                    # Show default value if exists
                    if param.default != inspect.Parameter.empty:
                        default_val = repr(param.default) if param.default is not None else "None"
                        console.print(f"    [dim]Default: {default_val}[/dim]")
                        
        except Exception as e:
            console.print(f"  [dim]Could not parse signature: {e}[/dim]")
            
        console.print("─" * 60 + "\n")

