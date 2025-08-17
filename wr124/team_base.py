


from typing import AsyncGenerator, Awaitable, Callable, List, Union, Any, Sequence

from wr124.agent_base import BaseAgent, STOP_PROMPT
from wr124.prompt_mcp_system import GENERAL_PROMPT
from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from autogen_agentchat.messages import BaseChatMessage, BaseAgentEvent, TextMessage,ModelClientStreamingChunkEvent, StopMessage
from autogen_agentchat.base import ChatAgent, TaskResult, Team, TerminationCondition, Response
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelFamily, ModelInfo, ChatCompletionClient
from autogen_ext.tools.mcp import StdioServerParams, StreamableHttpServerParams, SseServerParams, mcp_server_tools, StdioMcpToolAdapter
from rich.console import Console as RichConsole
from .util import default_user_input_callback, print_tools

from .filesystem import tool_mapping
class Team:
    def __init__(self, model: str):
        self._model_client = OpenAIChatCompletionClient(model=model, model_info=ModelInfo(
            vision=False,
            function_calling=True,
            json_output=True,
            family=ModelFamily.GPT_4O,
            structured_output=True,
        ))

        self._tools: dict[str, Any] = tool_mapping
        self._sub_agents = []
        self._main_agent = None
        self._interactive = False
        self._user_input_callback: Callable[[], Awaitable[tuple[str, str | None]]] | None = None
        
        # 如果启用交互模式，自动设置默认回调
        if self._interactive:
            self._user_input_callback = default_user_input_callback

    async def initialize(self):
        """Initialize MCP tools and main agent - must be called before use"""
        self._main_agent = self._create_agent(self._model_client, None, None)

    def register_user_input_callback(self, callback: Callable[[], Awaitable[tuple[str, str | None]]]):
        """
        Register a callback function for user input interaction.
        The callback should return tuple (action, task) where:
        - action: 'continue' to continue with new task, 'exit' to exit
        - task: new task string if action is 'continue', None if action is 'exit'
        """
        self._user_input_callback = callback        

    def enable_interactive_mode(self, use_default_callback: bool = True):
        """
        Enable interactive mode.
        If use_default_callback is True, uses the built-in default callback.
        """
        self._interactive = True
        if use_default_callback:
            self._user_input_callback = default_user_input_callback

    def disable_interactive_mode(self):
        """
        Disable interactive mode.
        """
        self._interactive = False
        self._user_input_callback = None

    @property
    def is_interactive(self) -> bool:
        """
        Check if interactive mode is enabled.
        """
        return self._interactive and self._user_input_callback is not None

    async def register_mcp_tools(self, param: Union[StdioServerParams, StreamableHttpServerParams, SseServerParams]):
        tools = await mcp_server_tools(param)        
        for tool in tools:
            tool_name = tool.schema.get('name')
            # 验证工具名称是否为有效字符串
            if not isinstance(tool_name, str) or not tool_name.strip():
                console = RichConsole()
                console.print(f"[red]⚠️  Warning: Skipping tool with invalid name: {tool_name} (type: {type(tool_name)})[/red]")
                continue
            self._tools[tool_name] = tool
        return tools

    def _create_agent(self, model_client: ChatCompletionClient, tools = None, prompt = None, name = None):
        use_tools = []
        use_prompt = f"{GENERAL_PROMPT}{STOP_PROMPT}"
        use_name = 'WorkerAgent'
        if tools is None:
            for k, v in self._tools.items():
                use_tools.append(v)            
        else:
            for tool_name in tools:
                if tool_name in self._tools:
                    use_tools.append(self._tools[tool_name])
                else:
                    raise ValueError(f"Tool '{tool_name}' not found in registered tools.")

        if prompt:
            use_prompt = f"{prompt}{STOP_PROMPT}"

        agent = BaseAgent(
            name=use_name,
            model_client=model_client,
            description="A worker agent for tasks.",
            system_message=use_prompt,
            tools=use_tools,
        )
        return agent

    def _create_exit_task_result(self, reason: str) -> TaskResult:
        """创建退出时的 TaskResult"""
        exit_message = TextMessage(content=f"程序退出：{reason}", source="system")
        return TaskResult(messages=[exit_message], stop_reason="Exit")
    
    async def _get_initial_task(self, task: str | BaseChatMessage | Sequence[BaseChatMessage] | None) -> str | None:
        """获取初始任务，处理交互模式下的用户输入"""
        console = RichConsole()
        
        if task is not None:
            return task
        
        if not self.is_interactive:
            console.print("\n[cyan]提醒：未提供任务，默认启动交互模式。[/cyan]")
            self.enable_interactive_mode(True)
        else:            
            console.print("\n[cyan]欢迎使用 wr124 交互模式！[/cyan]")
        try:
            action, first_task = await self._user_input_callback()
            if action == 'exit':
                console.print("\n[yellow]用户选择退出。[/yellow]")
                return None
            elif action == 'continue' and first_task:
                return first_task
            else:
                console.print("\n[red]无效输入，退出程序。[/red]")
                return None
        except Exception as e:
            console.print(f"\n[red]获取用户输入时发生错误: {e}，退出程序。[/red]")
            return None
    
    async def _execute_task(self, task: str, cancellation_token: CancellationToken | None, output_task_messages: bool
                            ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None]:
        """执行单个任务"""
        task_with_prompt = str(task) + '\n**所有任务完成后，输入结束关键词。注意：仅当所有任务结束才输出，其他情况继续执行任务。**'
        
        async for msg in self._main_agent.run_stream(
            task=task_with_prompt,
            cancellation_token=cancellation_token,
            output_task_messages=output_task_messages
        ):
            yield msg
    
    async def _handle_interactive_next(self) -> tuple[str, str | None]:
        """处理交互模式下的下一步操作"""
        console = RichConsole()
        try:
            action, next_task = await self._user_input_callback()
            if action == 'exit':
                console.print("\n[green]用户选择退出程序。[/green]")
                return 'exit', None
            elif action == 'continue' and next_task:
                console.print(f"\n[blue]开始执行新任务: {next_task}[/blue]")
                return 'continue', next_task
            else:
                console.print("\n[red]无效的回调返回值，退出程序。[/red]")
                return 'error', None
        except Exception as e:
            console.print(f"\n[red]处理用户输入时发生错误: {e}，退出程序。[/red]")
            return 'error', None

    async def run_stream(
        self,
        *,
        task: str | BaseChatMessage | Sequence[BaseChatMessage] | None = None,
        cancellation_token: CancellationToken | None = None,
        output_task_messages: bool = True,
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None]:
        if self._main_agent is None:
            await self.initialize()
        
        console = RichConsole()
        
        # 获取初始任务
        current_task = await self._get_initial_task(task)
        if current_task is None:
            yield self._create_exit_task_result("无有效任务")
            return
        
        # 主循环：执行任务和处理交互
        while True:
            # 执行当前任务
            async for msg in self._execute_task(current_task, cancellation_token, output_task_messages):
                yield msg
            
            # 任务完成后的处理
            if not self.is_interactive:
                console.print("\n[yellow]任务完成，自动退出。[/yellow]")
                yield self._create_exit_task_result("任务完成")
                return
            
            # 交互模式：询问用户下一步操作
            action, next_task = await self._handle_interactive_next()
            
            if action == 'exit':
                yield self._create_exit_task_result("用户选择退出")
                return
            elif action == 'continue' and next_task:
                current_task = next_task
                continue
            else:
                yield self._create_exit_task_result("处理用户输入失败")
                return