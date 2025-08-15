

import argparse
import os
import sys
import asyncio
from pathlib import Path
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
from autogen_agentchat.ui import Console
from dotenv import load_dotenv
import asyncio
from rich.console import Console as RichConsole


from .filesystem import tool_mapping

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

class Team:
    def __init__(self, model:str):
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

    async def initialize(self):
        """Initialize MCP tools and main agent - must be called before use"""
        self._main_agent = self._create_agent(self._model_client, None, None)

    async def register_mcp_tools(self, param: Union[StdioServerParams, StreamableHttpServerParams, SseServerParams]):
        tools = await mcp_server_tools(param)
        print_tools(tools)
        for tool in tools:
            tool_name = tool.schema.get('name')
            # 验证工具名称是否为有效字符串
            if not isinstance(tool_name, str) or not tool_name.strip():
                console = RichConsole()
                console.print(f"[red]⚠️  Warning: Skipping tool with invalid name: {tool_name} (type: {type(tool_name)})[/red]")
                continue
            self._tools[tool_name] = tool

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

    async def run_stream(
        self,
        *,
        task: str | BaseChatMessage | Sequence[BaseChatMessage] | None = None,
        cancellation_token: CancellationToken | None = None,
        output_task_messages: bool = True,
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None]:
        if self._main_agent is None:
            await self.initialize()
        task = task + '\n**所有任务完成后，输入结束关键词。注意：仅当所有任务结束才输出，其他情况继续执行任务。**'
        async for msg in self._main_agent.run_stream(task=task,
                     cancellation_token=cancellation_token,
                     output_task_messages=output_task_messages):
            yield msg