import os
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.agents import AssistantAgent
from typing import Any, Awaitable, Callable, List, Mapping, Sequence, AsyncGenerator, Union
from autogen_agentchat.messages import BaseChatMessage, BaseAgentEvent, TextMessage,ModelClientStreamingChunkEvent, StopMessage
from autogen_agentchat.base import ChatAgent, TaskResult, Team, TerminationCondition, Response
from autogen_agentchat.conditions import TextMentionTermination, ExternalTermination
from autogen_core import CancellationToken
from autogen_core.models import ChatCompletionClient
from autogen_core.tools import BaseTool
from autogen_core.memory import Memory
from autogen_core import CancellationToken, ComponentBase, trace_create_agent_span, trace_invoke_agent_span
from autogen_core import CancellationToken
from autogen_core.models import (
    FunctionExecutionResult,
    LLMMessage,
    RequestUsage,
    UserMessage,
    AssistantMessage
)
# 处理相对导入问题 - 支持直接运行和作为模块导入
try:
    from .prompt_compress import SUMMARY_HISTORY_SYSTEM_TEMPLATE
except ImportError:
    # 当直接运行此文件时，使用绝对导入
    from wr124.agents.prompt_compress import SUMMARY_HISTORY_SYSTEM_TEMPLATE


STOP_PROMPT = '''

## 这一点非常重要
当然安排的任务已经完成，并且没有其他工作需要执行，输出结束关键词。
我们的结束关键词是：`TERMINATE`

这个关键词非常重要，可以避免你持续输出相同的内容
'''


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
        **kwargs,
    ) -> None:
        super().__init__(
            name,
            model_client,
            description=description,
            system_message=system_message,
            tools=tools,
            reflect_on_tool_use=reflect_on_tool_use,
            memory=memory,
            **kwargs,
        )
        self._temrminate_word = 'TERMINATE'
        self._termination_condition = TextMentionTermination(self._temrminate_word)
        self._model_client = model_client
        self._max_tokens = 100*1024   # 100K tokens
    
    @property
    def tools(self):
        return self._tools

    async def run(
        self,
        task: str | BaseChatMessage | Sequence[BaseChatMessage] | None = None,
        cancellation_token: CancellationToken | None = None,
        output_task_messages: bool = True,
    ) -> TaskResult:
        with trace_invoke_agent_span(agent_name=self.name, agent_description=self.description):
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
            elif isinstance(task, BaseChatMessage):
                input_messages.append(task)
                if output_task_messages:
                    output_messages.append(task)
                    yield task
            else:
                if not task:
                    raise ValueError("Task list cannot be empty.")
                for msg in task:
                    if isinstance(msg, BaseChatMessage):
                        input_messages.append(msg)
                        if output_task_messages:
                            output_messages.append(msg)
                            yield msg
                    else:
                        raise ValueError(f"Invalid message type in sequence: {type(msg)}")
                    
            models_usage = RequestUsage(0,0)
            stop_reason: StopMessage | None = None
            completed = False
            while True:
                if cancellation_token.is_cancelled():
                    stop_reason = "Cancelled by user"
                    break
                if self._termination_condition.terminated or completed:
                    break
                async for message in self.on_messages_stream(input_messages, cancellation_token):
                
                    if isinstance(message, Response):
                        yield message.chat_message
                        output_messages.append(message.chat_message)

                        # 统计token使用情况
                        if message.chat_message.models_usage:
                            models_usage = message.chat_message.models_usage
                        
                        # 检查是否满足终止条件
                        stop_message = await self._termination_condition([message.chat_message])
                        if stop_message is not None:
                            # Reset the termination conditions and turn count.
                            await self._termination_condition.reset()
                            completed = True
                            break
                    else:
                        yield message
                        if isinstance(message, ModelClientStreamingChunkEvent):
                            # Skip the model client streaming chunk events.
                            continue
                        output_messages.append(message)

                input_messages = []

                # 如果output_messages 计算token数量超过最大限制，则需要进行摘要，并将摘要作为新的输入
                if models_usage.prompt_tokens > self._max_tokens:
                    input_messages = await self._compress_message(cancellation_token)
                

            yield TaskResult(messages=output_messages, stop_reason=stop_reason)


    async def _compress_message(self, cancellation_token: CancellationToken | None = None,):
        compress_agent = AssistantAgent(
            name=f'{self.name}_compressor',
            model_client=self._model_client,
            description="A compressor agent for tasks.",
            system_message=SUMMARY_HISTORY_SYSTEM_TEMPLATE,
            model_context=self._model_context,
        )
        msg = TextMessage(
            content="The conversation history has exceeded the token limit. Please summarize the conversation.",
            source="user",
        )

        res:Response = await compress_agent.on_messages([msg], cancellation_token)
        summary = [res.chat_message]
        return summary


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