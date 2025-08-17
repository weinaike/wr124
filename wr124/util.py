
from autogen_ext.tools.mcp import StdioMcpToolAdapter
from typing import List
from rich.console import Console as RichConsole

async def default_user_input_callback() -> tuple[str, str | None]:
    """
    Default user input callback function for terminal interaction.
    Returns tuple (action, task) where:
    - action: 'continue' to continue with new task, 'exit' to exit
    - task: new task string if action is 'continue', None if action is 'exit'
    """
    try:
        while True:
            print("\n" + "="*50)
            print("请选择下一步操作：")
            print("1. 输入新任务继续执行")
            print("2. 退出程序")
            print("="*50)
            
            user_input = input("请选择 (1/2) 或直接输入任务: ").strip()
            
            if user_input in ['1']:
                new_task = input("请输入任务: ").strip()
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
                new_task = input("请输入任务: ").strip()
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

def print_tools(tools: List[StdioMcpToolAdapter]) -> None:
    """Print available MCP tools and their parameters in a formatted way."""
    console = RichConsole()
    console.print("\n[bold blue]📦 Loaded MCP Tools:[/bold blue]\n")

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

