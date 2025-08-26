"""
Team Base 模块 - 智能体管理与任务执行
负责Agent的创建、工具管理、任务执行流程管理
"""
from typing import AsyncGenerator, Mapping, Sequence, Optional, List, Union, Dict, Any, Tuple
import asyncio
import os
from pathlib import Path

from autogen_core import CancellationToken
from autogen_core.models import ChatCompletionClient, ModelInfo, ModelFamily
from autogen_agentchat.messages import BaseChatMessage, BaseAgentEvent, TextMessage
from autogen_agentchat.base import TaskResult
from autogen_agentchat.tools import AgentTool
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from rich.console import Console as RichConsole
from pydantic import BaseModel, Field
import yaml
from .agent_base import BaseAgent, STOP_PROMPT
from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools
from ..session import SessionStateManager, SessionStateStatus



class AgentParam(BaseModel):
    name: str = Field(..., description="The name of the agent")
    description: str = Field(..., description="A brief description of the agent")
    prompt: str = Field(..., description="The prompt to initiate the agent's behavior")
    model: Optional[str] = Field(None, description="The model used by the agent")
    color: Optional[str] = Field(None, description="The color associated with the agent")
    tools: List[str] = Field([], description="A list of tools available to the agent")



def parse_agent_markdown(file_path: str) -> AgentParam:
    """
    Parse an agent markdown file and convert it to a simplified dictionary.
    
    Args:
        file_path: Path to the markdown file
        
    Returns:
        Dictionary with fields: name, description, model, color, tools, prompt
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split content into frontmatter and body
    parts = content.split('---', 2)
    
    if len(parts) < 3:
        raise ValueError("Invalid markdown format: missing frontmatter")
    
    # Parse frontmatter (YAML)
    frontmatter_text = parts[1].strip()
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML frontmatter: {e}")
    
    # Parse body content (everything after frontmatter becomes prompt)
    prompt = parts[2].strip()
    
    # Parse tools from frontmatter
    tools_str = frontmatter.get('tools', None)
    if isinstance(tools_str, str):
        # Split by comma and clean up whitespace
        tools = [tool.strip() for tool in tools_str.split(',') if tool.strip()]
    elif isinstance(tools_str, list):
        tools = tools_str
    else:
        tools = []

    # 处理名称，确保是有效的Python标识符
    name = frontmatter.get('name', '')
    # 将连字符替换为下划线，确保名称符合Python标识符规则
    name = name.replace('-', '_')

    result = AgentParam(
        name=name,
        description=frontmatter.get('description', ''),
        model=frontmatter.get('model', None),
        color=frontmatter.get('color', None),
        tools=tools,
        prompt=prompt
    )

    return result


class Team:
    """
    团队管理器 - 负责智能体管理、工具管理与任务执行
    """
    
    def __init__(self, model_client: ChatCompletionClient):        
        self._model_client = model_client
        self._main_agent: Optional[BaseAgent] = None
        self._console = RichConsole()
        self._default_agent_config = None
        self._available_tools = []  # 存储所有可用工具
        self._session_state_manager = None
        self._load_default_config()
        self._resume = False

    def set_resume(self, resume: bool) -> None:
        """
        设置是否从上次中断的地方恢复

        Args:
            resume: 是否恢复
        """
        self._resume = resume

    def register_state_manager(self, manager: SessionStateManager) -> None:
        """
        注册状态管理器到智能体

        Args:
            manager: 要注册的状态管理器
        """
        self._session_state_manager = manager
        self._console.print(f"[green]✓ 启动会话管理: {manager.session_id}[/green]")

    async def set_enable_search_agent_tool(self):
        param = StdioServerParams(
            command='npx',
            args=["-y", "@adenot/mcp-google-search"],
            read_timeout_seconds=30, 
            env={
                "GOOGLE_API_KEY": os.environ.get("GOOGLE_API_KEY", ""),
                "GOOGLE_SEARCH_ENGINE_ID": os.environ.get("GOOGLE_SEARCH_ENGINE_ID", ""),
                # "HTTP_PROXY": "http://127.0.0.1:7890",
                # "HTTPS_PROXY": "http://127.0.0.1:7890"
            }
        )
        tools = await mcp_server_tools(param)
        config_path = Path(__file__).parent / "preset_agents" / "search_agent.md"
        agent_param = parse_agent_markdown(config_path)
        agent = AssistantAgent(
            name=agent_param.name,
            model_client=self._model_client,
            description=agent_param.description,
            system_message=agent_param.prompt,
            tools=tools,
            max_tool_iterations=20,
        )
        tool = AgentTool(agent, return_value_as_last_message=True)
        self._available_tools.append(tool)
        return tool

    def _load_default_config(self) -> None:
        """加载默认的智能体配置"""
        try:
            # 默认使用 general_assistant.md
            default_config_path = Path(__file__).parent / "preset_agents" / "general_assistant.md"
            if default_config_path.exists():
                self._default_agent_config = parse_agent_markdown(str(default_config_path))
                self._console.print(f"[dim]✓ 加载默认智能体配置: {self._default_agent_config.name}[/dim]")
            else:
                # 如果文件不存在，使用硬编码的默认配置
                self._default_agent_config = AgentParam(
                    name="general_assistant",
                    description="A general purpose assistant",
                    prompt="You are a helpful assistant. Please be concise and helpful.",
                    tools=[]
                )
                self._console.print("[dim]✓ 使用硬编码的默认智能体配置[/dim]")
        except Exception as e:
            # 异常处理：使用最基本的配置
            self._default_agent_config = AgentParam(
                name="fallback_assistant",
                description="Fallback assistant configuration",
                prompt="You are a helpful assistant.",
                tools=[]
            )
            self._console.print(f"[yellow]⚠️  加载默认配置失败，使用备用配置: {e}[/yellow]")
    
    def register_tools(self, tools: List) -> None:
        """
        注册工具到Team（必须在设置智能体之前调用）
        
        Args:
            tools: 工具列表
        """
        self._available_tools.extend(tools)
        self._console.print(f"[green]✓ 有效工具 {len(self._available_tools)} 个[/green]")
    
    def _filter_tools_by_names(self, tool_names: List[str]) -> List:
        """
        根据工具名称筛选工具
        
        Args:
            tool_names: 工具名称列表
            
        Returns:
            筛选后的工具列表
        """
        if len(tool_names) == 0:
            # 如果未指定工具，返回所有可用工具
            return self._available_tools.copy()
        
        filtered_tools = []
        missing_tools = []
        
        for tool_name in tool_names:
            found = False
            for tool in self._available_tools:
                # 检查工具名称匹配
                if (hasattr(tool, 'name') and tool.name == tool_name) or \
                   (hasattr(tool, '__name__') and tool.__name__ == tool_name) or \
                   (hasattr(tool, 'schema') and tool.schema.get('name') == tool_name):
                    filtered_tools.append(tool)
                    found = True
                    break
            
            if not found:
                missing_tools.append(tool_name)
        
        if missing_tools:
            self._console.print(f"[yellow]⚠️  以下工具未找到: {', '.join(missing_tools)}[/yellow]")
        
        return filtered_tools
    
    def _create_agent_from_param(self, agent_param: AgentParam) -> BaseAgent:
        """
        根据AgentParam创建Agent实例
        
        Args:
            agent_param: AgentParam对象，包含agent配置信息
            tools: 工具列表，如果为None则使用筛选后的工具
            
        Returns:
            BaseAgent实例
        """
        # 构建系统提示词
        system_prompt = f"{agent_param.prompt}\n{STOP_PROMPT}"
        
        tools = self._filter_tools_by_names(agent_param.tools)
        if agent_param.model:
            self._model_client = OpenAIChatCompletionClient(
                model=agent_param.model,
                model_info=ModelInfo(
                    vision=False,
                    function_calling=True,
                    json_output=True,
                    family=ModelFamily.GPT_4O,
                    structured_output=True,
                )
            )
        # 创建agent
        agent = BaseAgent(
            name=agent_param.name,
            model_client=self._model_client,
            description=agent_param.description,
            system_message=system_prompt,
            tools=tools,
            reflect_on_tool_use=False,
            max_tool_iterations=20
        )
        
        # 设置颜色属性
        if agent_param.color:
            setattr(agent, 'color', agent_param.color)
        
        return agent
    
    def set_main_agent(self, agent_param: Optional[AgentParam] = None) -> None:
        """
        设置主智能体（工具会根据agent_param.tools字段自动筛选）
        
        Args:
            agent_param: 智能体参数，如果为None则使用默认配置
        """
        if agent_param is None:
            agent_param = self._default_agent_config
        
        # 创建智能体，工具会在_create_agent_from_param中自动筛选
        self._main_agent = self._create_agent_from_param(agent_param)
        
        tools_count = len(self._main_agent.tools) if self._main_agent.tools else 0
        self._console.print(f"[green]✓ 主智能体已设置: {agent_param.name}，配置了 {tools_count} 个工具[/green]")
    
    def set_main_agent_from_config(self, config_path: str) -> None:
        """
        从配置文件设置主智能体
        
        Args:
            config_path: 配置文件路径
        """
        if not Path(config_path).exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        agent_param = parse_agent_markdown(config_path)
        self.set_main_agent(agent_param)
        self._console.print(f"[green]✓ 从配置文件加载主智能体: {config_path}[/green]")

    def register_agent_tool(self, config_path: str) -> AgentTool:
        """
        注册智能体工具

        Args:
            config_path: 工具配置文件路径

        Returns:
            注册的AgentTool实例
        """
        if not Path(config_path).exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        agent_param = parse_agent_markdown(config_path)
        agent = self._create_agent_from_param(agent_param)
        tool = AgentTool(agent, return_value_as_last_message=True)
        self._available_tools.append(tool)
        return tool

    
    async def execute_task(
        self, 
        task: str, 
        cancellation_token: CancellationToken | None = None,
        output_task_messages: bool = True
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None]:
        """
        执行单个任务
        
        Args:
            task: 要执行的任务
            cancellation_token: 取消令牌
            output_task_messages: 是否输出任务消息
        """
        if not self._main_agent:
            raise RuntimeError("Agent not initialized. Call set_main_agent() first.")
        if self._resume and self._session_state_manager:
            ret, state = await self._session_state_manager.restore_agent_session_state(self._main_agent.name)
            if ret == SessionStateStatus.SUCCESS:
                await self._main_agent.load_state(state)  
        try:
            async for msg in self._main_agent.run_stream(
                task=task,
                cancellation_token=cancellation_token,
                output_task_messages=output_task_messages
            ):
                yield msg
        except asyncio.CancelledError:
            # 任务被取消，生成取消消息
            self._console.print("[yellow]⏸️  任务已被中断[/yellow]")
            yield TextMessage(content="任务执行被用户中断", source="system")
            return
        except Exception as e:
            # 处理其他可能的异常
            # 检查是否是重试失败后的包装异常
            error_msg = str(e)
            if "Failed after" in error_msg and "attempts" in error_msg:
                # 这是来自底层重试机制的异常，提取原始错误信息
                self._console.print(f"[red]⚠️  任务执行失败（已重试）: {error_msg}[/red]")
            else:
                self._console.print(f"[red]⚠️  任务执行时发生异常: {e}[/red]")
            yield TextMessage(content=f"任务执行异常: {str(e)}", source="system")
            return
        finally:
            component = self._main_agent.dump_component()
            state = await self._main_agent.save_state()
            if self._session_state_manager:
                await self._session_state_manager.upload_session_state(
                        agent_name=self._main_agent.name,
                        agent=component,
                        state=state,
                        task=task,
                    )
    
    def create_exit_task_result(self, reason: str) -> TaskResult:
        """创建退出时的 TaskResult"""
        exit_message = TextMessage(content=f"程序退出：{reason}", source="system")
        return TaskResult(messages=[exit_message], stop_reason="Exit")
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        获取当前主智能体的信息
        
        Returns:
            包含智能体基本信息的字典
        """
        if not self._main_agent:
            return {"status": "Agent not initialized"}
        
        return {
            "name": self._main_agent.name,
            "description": self._main_agent.description,
            "color": getattr(self._main_agent, 'color', None),
            "tools_count": len(self._main_agent.tools) if self._main_agent.tools else 0,
            "status": "initialized"
        }
    
    def get_tools_info(self) -> Dict[str, Any]:
        """
        获取当前主智能体的工具信息
        
        Returns:
            包含工具信息的字典
        """
        if not self._main_agent:
            return {"status": "Agent not initialized", "tools": []}
        
        tools_info = []
        if hasattr(self._main_agent, 'tools') and self._main_agent.tools:
            for tool in self._main_agent.tools:
                tool_info = {
                    "name": getattr(tool, 'name', str(tool)),
                    "type": type(tool).__name__
                }
                if hasattr(tool, 'schema'):
                    tool_info["schema"] = tool.schema
                tools_info.append(tool_info)
        
        return {
            "status": "initialized",
            "tools_count": len(tools_info),
            "tools": tools_info,
            "available_tools_count": len(self._available_tools)
        }
    
    async def run_stream(
        self,
        task: str | BaseChatMessage | Sequence[BaseChatMessage],
        cancellation_token: CancellationToken | None = None,
        output_task_messages: bool = True,
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None]:
        """
        运行任务流（非交互模式）
        
        Args:
            task: 要执行的任务
            cancellation_token: 取消令牌
            output_task_messages: 是否输出任务消息
        """
        # 确保主智能体已初始化
        if not self._main_agent:
            self._console.print("[yellow]⚠️  主智能体未设置，使用默认配置[/yellow]")
            self.set_main_agent()
        
        # 将任务转换为字符串
        if isinstance(task, str):
            task_str = task
        elif isinstance(task, BaseChatMessage):
            task_str = str(task.content) if hasattr(task, 'content') else str(task)
        elif isinstance(task, Sequence):
            task_str = ' '.join(str(t) for t in task)
        else:
            task_str = str(task)
        
        # 执行任务
        async for msg in self.execute_task(
            task=task_str,
            cancellation_token=cancellation_token,
            output_task_messages=output_task_messages
        ):
            yield msg
