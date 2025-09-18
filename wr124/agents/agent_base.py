from enum import Enum
import os
import asyncio
import traceback
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.agents import AssistantAgent
from typing import Any, Awaitable, Callable, List, Mapping, Sequence, AsyncGenerator, Union, Optional
from autogen_agentchat.messages import (
    BaseChatMessage, 
    BaseAgentEvent, 
    TextMessage,
    ModelClientStreamingChunkEvent, 
    StopMessage, 
    MemoryQueryEvent, 
    ToolCallExecutionEvent, 
    ToolCallSummaryMessage,
    ToolCallRequestEvent
)


from autogen_agentchat.base import ChatAgent, TaskResult, Team, TerminationCondition, Response
from autogen_agentchat.conditions import TextMentionTermination, ExternalTermination
from autogen_core import CancellationToken
from autogen_core.models import ChatCompletionClient
from autogen_core.tools import BaseTool
from autogen_core.memory import Memory, ListMemory, MemoryContent
from autogen_core import CancellationToken, ComponentBase, trace_create_agent_span, trace_invoke_agent_span
from autogen_core import CancellationToken
from autogen_core.model_context import UnboundedChatCompletionContext
from autogen_core.models import (
    FunctionExecutionResult,
    LLMMessage,
    RequestUsage,
    UserMessage,
    SystemMessage,
    AssistantMessage    
)

from rich.console import Console as RichConsole

from ..session.session_state_manager import SessionStateManager, SessionStateStatus
from .agent_param import AgentParam
# 处理相对导入问题 - 支持直接运行和作为模块导入
try:
    from .memory_recorder import MemoryRecorder
except ImportError:
    from wr124.agents.memory_recorder import MemoryRecorder

KEYWORD = "_I_HAVE_COMPLETED_"

STOP_PROMPT = f'''

# 停止条件
**This is VERY important**
When the assigned tasks are completed and there is no other work to execute, output the termination keyword.
the termination keyword is: `{KEYWORD}`

'''
NOTE_PROMPT = f'''
This is a note: It is not part of the task but can guide your work.
1. Remembering your task goals or to-do goals is very important as it can guide your direction and prevent you from deviating.
2. When you are unsure about the next step, you can use `todo_read` or `list_tasks` to understand the task progress.
3. After completing a task or to-do, remember to update the task status.
4. Once all tasks are completed, enter the termination keyword. Note: Only output it when all tasks are finished; otherwise, continue executing tasks.
5. if you encounter any issues or blockers, using the `search_agent` tool to look up internet resources can be a very effective way to address them.
'''

class STOP_REASON(str, Enum):
    COMPLETED = "任务成功完成"
    CANCELLED = "任务被用户取消"
    TIMEOUT = "任务超时"
    ERROR = "任务执行出错"
    MAX_ITERATIONS = "达到次数上限"
    EXTERNAL_TERMINATION = "外部终止信号"
    EXIT = "用户主动退出"
    INVALID_TASK = "无效任务"
    UNKNOWN = "未知原因"


class NoSystemUnboundedChatCompletionContext(UnboundedChatCompletionContext):
    """不包含系统消息的无界聊天上下文"""
    def remove_system_messages(self) -> None:
        """移除系统消息"""
        self._messages = [msg for msg in self._messages if not isinstance(msg, SystemMessage)]

class BaseAgent(AssistantAgent):
    component_provider_override = "BaseAgent"
    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        description: str = "",
        system_message: str = f"you are a helpful assistant, completing tasks as requested. {STOP_PROMPT}",
        tools: List[BaseTool[Any, Any] | Callable[..., Any] | Callable[..., Awaitable[Any]]] | None = None,
        reflect_on_tool_use: bool | None = None,
        memory: Sequence[Memory] | None = None,
        enable_memory_recording: bool = False,
        max_tool_iterations=40,
        max_tokens: int = 40000,
        max_compress_count: Optional[int] = None,
        hook_agents: Optional[List[AgentParam]] = None,
        compress_agent: Optional[AgentParam] = None,
        **kwargs,
    ) -> None:
       
        note = MemoryContent(content=NOTE_PROMPT, mime_type="text/plain")
        note_memory = ListMemory(memory_contents=[note])
        if memory:
            if isinstance(memory, list):  # 确保 memory 是 List 类型
                memory.append(note_memory)
            else:
                memory = list(memory) + [note_memory]  # 转换为 List 并添加元素
        else:
            memory = [note_memory]
        
        super().__init__(
            name,
            model_client,
            model_context=NoSystemUnboundedChatCompletionContext(),
            description=description,
            system_message=system_message,
            tools=tools,
            reflect_on_tool_use=reflect_on_tool_use,
            memory=memory,   
            max_tool_iterations=max_tool_iterations,         
            **kwargs,
        )
        self._temrminate_word = KEYWORD
        self._termination_condition = TextMentionTermination(self._temrminate_word)
        self._model_client = model_client
        self._max_tokens = max_tokens   # token
        self._min_tool_count_to_summary = 20


        self._max_compress_count = max_compress_count if max_compress_count is not None else 0  # 压缩次数
         # 压缩agent
        self._compress_agent_param = compress_agent
               
        # Rich console for beautiful output
        self._hook_agents = hook_agents if hook_agents is not None else []

        self._console = RichConsole()
        
        # 记忆记录功能
        self._enable_memory_recording = enable_memory_recording
        self._memory_recorder: Optional[MemoryRecorder] = None
        self._memory_queue: Optional[asyncio.Queue] = None
        self._memory_task: Optional[asyncio.Task] = None
        
        if self._enable_memory_recording:
            self._memory_recorder = MemoryRecorder(model_client, name)
            self._memory_queue = asyncio.Queue(maxsize=100)  # 限制队列大小
        self._session_manager: Optional[SessionStateManager] = None

    def register_session_manager(self, session_manager: SessionStateManager):
        self._session_manager = session_manager

    @property
    def tools(self):
        return self._tools

    async def run(
        self,
        *,
        task: str | BaseChatMessage | Sequence[BaseChatMessage] | None = None,
        cancellation_token: CancellationToken | None = None,
        output_task_messages: bool = True,
    ) -> TaskResult:
        result: TaskResult | None = None
        async for message in self.run_stream(
            task=task,
            cancellation_token=cancellation_token,
            output_task_messages=output_task_messages,
        ):
            if isinstance(message, TaskResult):
                result = message
        if result is not None:
            return result
        raise AssertionError("The stream should have returned the final result.")

    async def run_stream(
        self,
        *,
        task: str | BaseChatMessage | Sequence[BaseChatMessage] | None = None,
        cancellation_token: CancellationToken | None = None,
        output_task_messages: bool = True,
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None]:
    
        with trace_invoke_agent_span(agent_name=self.name, agent_description=self.description):
            if cancellation_token is None:
                cancellation_token = CancellationToken()
            
            # 启动记忆记录任务
            if self._enable_memory_recording and self._memory_recorder and self._memory_queue:
                self._memory_task = asyncio.create_task(
                    self._memory_recorder.start_recording(self._memory_queue, cancellation_token)
                )
            
            try:
                input_messages: List[BaseChatMessage] = []
                output_messages: List[BaseAgentEvent | BaseChatMessage] = []
                if task is None:
                    pass
                elif isinstance(task, str):
                    text_msg = TextMessage(content=task, source="user")
                    input_messages.append(text_msg)
                    if output_task_messages:
                        output_messages.append(text_msg)
                        yield text_msg
                        # 发送到记忆队列
                        self._add_to_memory_queue(text_msg)
                elif isinstance(task, BaseChatMessage):
                    input_messages.append(task)
                    if output_task_messages:
                        output_messages.append(task)
                        yield task
                        # 发送到记忆队列
                        self._add_to_memory_queue(task)
                else:
                    if not task:
                        raise ValueError("Task list cannot be empty.")
                    for msg in task:
                        if isinstance(msg, BaseChatMessage):
                            input_messages.append(msg)
                            if output_task_messages:
                                output_messages.append(msg)
                                yield msg
                                # 发送到记忆队列
                                self._add_to_memory_queue(msg)
                        else:
                            raise ValueError(f"Invalid message type in sequence: {type(msg)}")
                input_messages_bak = input_messages.copy()
                models_usage = RequestUsage(0,0)
                stop_reason: str = STOP_REASON.UNKNOWN
                completed = False
                trigger_summary = False
                skip_stop = False  # 结束关键词跳过
                compress_count = 0  # 压缩上下文次数，压缩上下文可以减少token使用，相当于重启任务（仅保留少数总结信息）。超过固定次数，任务还未完成，则退出。需要人工介入解决复杂难题
                tool_count = 0  # 统计一次性调用工具次数，工具调用次数大于 self._min_tool_count_to_summary，进行一次总结，规划下一步动作，不足时不做处理
                while True:
                    if cancellation_token.is_cancelled():
                        stop_reason = STOP_REASON.CANCELLED
                        break
                    if self._termination_condition.terminated or completed:
                        break
                    async for message in self.on_messages_stream(input_messages, cancellation_token):
                    
                        if isinstance(message, Response):
                            if trigger_summary:
                                trigger_summary = False
                                skip_stop = True # 如果上次是summary提示，则跳过终止条件检查（因为总结过程中可能输出 _I_HAVE_COMPLETED_ 字样），这个不是期望的， 其他时候都保持False
                            yield message.chat_message                            
                            output_messages.append(message.chat_message)
                            # 发送到记忆队列
                            self._add_to_memory_queue(message.chat_message)
                            if isinstance(message.chat_message, ToolCallSummaryMessage):
                                # 当max_tool_iterations设置>1 时，多次的工具调用后，做依次总结是有必要的。
                                if tool_count >= self._min_tool_count_to_summary:
                                    input_messages = [TextMessage(content="先总结以上工具调用结果，形成阶段性分析结论. 再描述后续须执行的动作以指导推进任务目标完成", source='user')]
                                    trigger_summary = True
                                else:
                                    input_messages = []
                            else:
                                input_messages = []
                            tool_count = 0
                            # 统计token使用情况
                            if message.chat_message.models_usage:
                                models_usage = message.chat_message.models_usage
                            
                            # 是否要跳过一次判断
                            if skip_stop:
                                skip_stop = False
                            else:
                                # 检查是否满足终止条件
                                stop_message = await self._termination_condition([message.chat_message])                            
                                if stop_message is not None:
                                    # Reset the termination conditions and turn count.
                                    await self._termination_condition.reset()
                                    completed = True
                                    stop_reason=STOP_REASON.COMPLETED
                                    break

                        else:
                            yield message
                            if isinstance(message, ModelClientStreamingChunkEvent):
                                # Skip the model client streaming chunk events.
                                continue
                            if isinstance(message,ToolCallRequestEvent):
                                tool_count += 1
                            output_messages.append(message)
                            # 发送到记忆队列
                            self._add_to_memory_queue(message)

                    # 如果output_messages 计算token数量超过最大限制，则需要进行摘要，并将摘要作为新的输入
                    if models_usage.prompt_tokens > self._max_tokens:
                        compress_count += 1
                        if compress_count > self._max_compress_count:
                            self._console.print(f"[yellow]⚠️  token压缩次数超过上限{self._max_compress_count}，停止[/yellow]")
                            stop_reason = STOP_REASON.MAX_ITERATIONS

                            break
                        summary = await self._compress_message(cancellation_token)
                        input_messages = input_messages_bak + summary
                        models_usage = RequestUsage(0,0)
                        await self.upload_state("compress history")                                                
                        await self._model_context.clear() # 清空模型上下文，以便进行新的输入               

                yield TaskResult(messages=output_messages, stop_reason=stop_reason)
            
            finally:
                await self._cleanup_memory_task()
                await self._hook_agents_run(cancellation_token)


    async def on_messages_stream(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
                                 )-> AsyncGenerator[Union[BaseAgentEvent, BaseChatMessage, Response], None]:
        """
        重载底层AssitantAgent的on_messages_stream方法, 主要添加工具调用失败后重试功能
        1. 处理消息流，添加异常处理和重试机制
        2. 最多重试5次，每次间隔递增的等待时间
        """
        max_retries = 3
        retry_delay = 1  # 初始延迟2秒
        
        attempt = 0
        while(attempt <= max_retries):       
            try:
                async for message in super().on_messages_stream(messages, cancellation_token):
                    if isinstance(message, MemoryQueryEvent) :
                        continue
                    if isinstance(message, ToolCallExecutionEvent):
                        attempt = 0
                        continue
                    yield message
                # 如果成功处理完所有消息，直接返回
                # self._model_context中添加进去的SystemMessage都给踢出来。避免SystemMessage在模型上下文中重复添加
                if isinstance(self._model_context, NoSystemUnboundedChatCompletionContext):
                    self._model_context.remove_system_messages()
                    
                return               
            except asyncio.CancelledError:
                # 重新抛出取消异常，让上层处理               
                raise
            
            except Exception as e:
                attempt += 1
                # 检查是否是MCP流式调用相关的异常（通常来自anyio库）
                exception_name = type(e).__name__
                if exception_name in ['BrokenResourceError', 'ClosedResourceError']:
                    # 这些异常通常表示流被中断，可能是由于ESC键中断
                    self._console.print(f"[yellow][{self.name}] MCP stream interrupted ({exception_name}), handling gracefully...[/yellow]")
                    # 如果是取消引起的，直接返回
                    if cancellation_token and cancellation_token.is_cancelled():
                        self._console.print(f"[cyan][{self.name}] Task was cancelled, stopping gracefully.[/cyan]")
                        return
                    # 对于流中断异常，不重试，直接返回
                    self._console.print(f"[yellow][{self.name}] Stream interrupted, ending task execution.[/yellow]")
                    return
                
                error_detail = traceback.format_exc()
                content = f"遇到一个错误，请确认工具调用参数格式都正确。问题如下:\n{str(e)}\n{error_detail}"
                messages = [TextMessage(content=content, source='user')]

                # 如果是最后一次尝试，抛出异常
                if attempt >= max_retries:
                    final_error_msg = f"[{self.name}] Failed after {max_retries + 1} attempts. Final error: {type(e).__name__}: {str(e)}\n{error_detail}"
                    # 重新抛出取消异常，让上层处理
                    raise Exception(final_error_msg) from e
                
                # 计算下次重试的延迟时间（指数退避）
                current_delay = retry_delay * (2 ** attempt)
                self._console.print(f"[{self.name}] Retrying in {current_delay} seconds...", style="red")
                await asyncio.sleep(current_delay)
                if cancellation_token and cancellation_token.is_cancelled():
                    return


    async def _hook_agents_run(self, cancellation_token: CancellationToken) -> List[BaseChatMessage]:
        """运行挂钩智能体，返回它们的输出消息列表"""
        all_hook_messages: List[BaseChatMessage] = []
        for agent_param in self._hook_agents:
            if agent_param.task is None:
                self._console.print(f"[yellow]⚠️  挂钩智能体 {agent_param.name} 未配置任务，跳过[/yellow]")
                continue
            try:
                hook_agent = AssistantAgent(
                    name=agent_param.name,
                    model_client=self._model_client,
                    description=agent_param.description,
                    system_message=agent_param.prompt,
                    tools=self._tools,
                    reflect_on_tool_use=False,
                    max_tool_iterations=agent_param.max_tool_iterations if agent_param.max_tool_iterations is not None else 5,
                )
                self._console.print(f"[cyan]🤖 Running hook agent: {agent_param.name}[/cyan]")
                response = await hook_agent.on_messages(messages=[TextMessage(content=agent_param.task,source='user')], cancellation_token=cancellation_token)
                all_hook_messages.append(response.chat_message)
            except Exception as e:
                self._console.print(f"[red]Error running hook agent {agent_param.name}: {e}[/red]")
        return all_hook_messages



    async def _compress_message(self, cancellation_token: CancellationToken | None = None,) -> List[BaseChatMessage]:
        if self._compress_agent_param is None:
            self._console.print(f"[yellow]⚠️  压缩Agent未配置，无法压缩上下文，跳过[/yellow]")
            return []

        if cancellation_token is None:
            cancellation_token = CancellationToken()

        filtered_tools = []
        
        for tool_name in self._compress_agent_param.tools:
            for tool in self._tools:
                if (hasattr(tool, 'name') and tool.name == tool_name) or \
                    (hasattr(tool, '__name__') and tool.__name__ == tool_name) or \
                    (hasattr(tool, 'schema') and tool.schema.get('name') == tool_name):
                    filtered_tools.append(tool)
                    break
        if len(filtered_tools) != len(self._compress_agent_param.tools):
            self._console.print(f"[yellow]⚠️  部分压缩Agent工具未找到，检查工具名称是否正确。期望工具: {self._compress_agent_param.tools}, 实际工具: {[tool.name if hasattr(tool, 'name') else (tool.__name__ if hasattr(tool, '__name__') else tool.schema.get('name') if hasattr(tool, 'schema') else str(tool)) for tool in filtered_tools]}[/yellow]")

        compress_agent = AssistantAgent(
            name=f'{self.name}_compressor',
            model_client=self._model_client,
            description=self._compress_agent_param.description,
            system_message=self._compress_agent_param.prompt,
            model_context=self._model_context,
            tools=filtered_tools,
            max_tool_iterations=self._compress_agent_param.max_tool_iterations if self._compress_agent_param.max_tool_iterations is not None else 5,
        )
        msg = TextMessage(
            content=self._compress_agent_param.task if self._compress_agent_param.task else "Please summarize the conversation following system prompt. first call `add_memory` to upload summary to database. add then output the summary to user",
            source="user",
        )

        res:Response = await compress_agent.on_messages([msg], cancellation_token)
        self._add_to_memory_queue(res.chat_message)
        summary = [res.chat_message]
        return summary

    def _add_to_memory_queue(self, message: BaseChatMessage | BaseAgentEvent) -> None:
        """将消息添加到记忆队列"""
        if not self._enable_memory_recording or not self._memory_queue:
            return
        
        try:
            self._memory_queue.put_nowait(message)
        except asyncio.QueueFull:
            # 队列满时丢弃最老的消息
            try:
                self._memory_queue.get_nowait()
                self._memory_queue.put_nowait(message)
            except asyncio.QueueEmpty:
                pass

    async def _cleanup_memory_task(self) -> None:
        """清理记忆任务"""
        if not self._memory_task or not self._memory_queue:
            return
        
        # 发送结束信号
        try:
            self._memory_queue.put_nowait(None)
        except asyncio.QueueFull:
            pass
        
        # 等待任务完成或超时
        try:
            await asyncio.wait_for(self._memory_task, timeout=3.0)
        except asyncio.TimeoutError:
            # 超时则取消任务
            self._memory_task.cancel()
            try:
                await self._memory_task
            except asyncio.CancelledError:
                pass

    async def upload_state(self, note: str):
        if self._session_manager:
            msgs = await self._model_context.get_messages()
            if len(msgs) < 5:
                return
            state = await self.save_state()
            await self._session_manager.upload_session_state(self.name, None, state, note)

    async def download_state(self):
        if self._session_manager:
            ret, state = await self._session_manager.restore_agent_session_state(self.name)
            if ret == SessionStateStatus.SUCCESS:
                if isinstance(state, dict):
                    await self.load_state(state)
                return
            else:
                ret, state = await self._session_manager.restore_latest_session_state(self.name)
                if ret == SessionStateStatus.SUCCESS:
                    if isinstance(state, dict):
                        await self.load_state(state)
                    return
                else:
                    return

if __name__ == "__main__":
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from autogen_agentchat.ui import Console
    from dotenv import load_dotenv
    import asyncio
    import os
    import sys
    from pathlib import Path
    from typing_extensions import Annotated
    load_dotenv()
    current_dir = os.getcwd()
    project_root = Path(current_dir).parent
    # 添加项目根目录到Python路径
    sys.path.insert(0, str(current_dir))
    sys.path.insert(0, str(project_root))

    def test(param:Annotated[str, "param"]) ->str:
        return 'aaa'
    model_client = OpenAIChatCompletionClient(model="gpt-4o")
    agent = BaseAgent(name="WorkerAgent", model_client=model_client, tools = [test])
    
    # Example usage
    async def main():
        await Console(agent.run_stream(task="What is the weather today?"))
        
    
    asyncio.run(main())