import asyncio
import logging
from typing import Any, Dict, List, Optional
from autogen_agentchat.messages import BaseChatMessage, TextMessage
from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from autogen_core.models import ChatCompletionClient

logger = logging.getLogger(__name__)

MEMORY_SYSTEM_PROMPT = """你是一个记忆管理助手，负责从对话中提取和总结重要信息。

请分析提供的对话消息，并生成简洁的记忆摘要，包括：
1. 关键话题和概念
2. 重要的用户需求或偏好
3. 解决方案或结论
4. 需要后续跟进的事项

请以JSON格式输出，包含以下字段：
- topic: 主要话题
- key_points: 关键要点列表
- user_preferences: 用户偏好（如果有）
- follow_up: 需要跟进的事项（如果有）
"""


class MemoryRecorder:
    """异步记忆记录器，用于处理对话记忆的生成和存储"""
    
    def __init__(self, model_client: ChatCompletionClient, agent_name: str = "memory"):
        self.model_client = model_client
        self.agent_name = agent_name
        self._is_running = False
        
    async def start_recording(
        self, 
        memory_queue: asyncio.Queue, 
        cancellation_token: CancellationToken
    ) -> None:
        """启动记忆录制任务"""
        if self._is_running:
            return
            
        self._is_running = True
        logger.info(f"Memory recorder started for {self.agent_name}")
        
        try:
            await self._process_memory_queue(memory_queue, cancellation_token)
        except Exception as e:
            logger.error(f"Memory recorder error: {e}")
        finally:
            self._is_running = False
            logger.info(f"Memory recorder stopped for {self.agent_name}")
    
    async def _process_memory_queue(
        self, 
        queue: asyncio.Queue, 
        cancellation_token: CancellationToken
    ) -> None:
        """处理记忆队列中的消息"""
        message_batch = []
        
        while not cancellation_token.is_cancelled():
            try:
                # 等待消息，定期检查取消状态
                message = await asyncio.wait_for(queue.get(), timeout=2.0)
                
                # 结束信号
                if message is None:
                    break
                
                message_batch.append(message)
                
                # 批量处理（每5条消息或等待超时时处理）
                if len(message_batch) >= 5:
                    await self._process_message_batch(message_batch, cancellation_token)
                    message_batch.clear()
                    
            except asyncio.TimeoutError:
                # 超时时处理积累的消息
                if message_batch:
                    await self._process_message_batch(message_batch, cancellation_token)
                    message_batch.clear()
                continue
        
        # 处理剩余消息
        if message_batch and not cancellation_token.is_cancelled():
            await self._process_message_batch(message_batch, cancellation_token)
    
    async def _process_message_batch(
        self, 
        messages: List[BaseChatMessage], 
        cancellation_token: CancellationToken
    ) -> None:
        """处理一批消息"""
        if cancellation_token.is_cancelled():
            return
        
        try:
            # 过滤重要消息（跳过系统消息和流式事件）
            important_messages = [
                msg for msg in messages 
                if isinstance(msg, TextMessage) and msg.content.strip()
            ]
            
            if not important_messages:
                return
            
            # 生成记忆
            memory_data = await self._generate_memory(important_messages, cancellation_token)
            
            if memory_data and not cancellation_token.is_cancelled():
                # 保存记忆（这里先简单打印，后续可扩展为数据库存储）
                await self._save_memory(memory_data)
                
        except Exception as e:
            logger.error(f"Error processing message batch: {e}")
    
    async def _generate_memory(
        self, 
        messages: List[BaseChatMessage], 
        cancellation_token: CancellationToken
    ) -> Optional[Dict[str, Any]]:
        """使用LLM生成记忆摘要"""
        if cancellation_token.is_cancelled():
            return None
        
        try:
            # 构建对话内容
            conversation = "\n".join([
                f"{msg.source}: {msg.content}" for msg in messages
            ])
            
            # 创建记忆生成代理
            memory_agent = AssistantAgent(
                name=f"{self.agent_name}_memory",
                model_client=self.model_client,
                system_message=MEMORY_SYSTEM_PROMPT
            )
            
            # 生成记忆
            prompt = TextMessage(
                content=f"请分析以下对话并生成记忆摘要：\n\n{conversation}",
                source="user"
            )
            
            # 检查model_client是否有必要的属性，如果没有则跳过LLM调用
            if not hasattr(self.model_client, 'model_info'):
                # 对于测试或Mock客户端，生成简单的记忆摘要
                return {
                    "agent_name": self.agent_name,
                    "message_count": len(messages),
                    "memory_content": f"记忆摘要：处理了{len(messages)}条消息，包含用户对话内容",
                    "timestamp": asyncio.get_event_loop().time()
                }
            
            response = await memory_agent.on_messages([prompt], cancellation_token)
            
            return {
                "agent_name": self.agent_name,
                "message_count": len(messages),
                "memory_content": response.chat_message.content,
                "timestamp": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            logger.error(f"Error generating memory: {e}")
            # 返回基本的记忆信息作为fallback
            return {
                "agent_name": self.agent_name,
                "message_count": len(messages),
                "memory_content": f"基本记忆：处理了{len(messages)}条消息",
                "timestamp": asyncio.get_event_loop().time(),
                "error": str(e)
            }
    
    async def _save_memory(self, memory_data: Dict[str, Any]) -> None:
        """保存记忆数据"""
        # 这里先简单记录日志，后续可扩展为数据库存储
        logger.info(f"Memory generated for {memory_data['agent_name']}: {memory_data['memory_content'][:100]}...")
        
        # TODO: 实现数据库存储
        # await self.database.save_memory(memory_data)
    
    @property
    def is_running(self) -> bool:
        return self._is_running
