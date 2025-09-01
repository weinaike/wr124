"""
会话状态管理模块
负责会话状态的上传、下载、存储和恢复
"""

from typing import Any, Dict, List, Mapping, Optional, Tuple
from datetime import datetime
from enum import Enum

from autogen_core import ComponentModel
from pydantic import BaseModel
from rich.console import Console as RichConsole
import aiohttp
import urllib.request

class SessionStateStatus(str, Enum):
    """会话状态状态枚举"""
    SUCCESS = "success"
    FAILED = "failed"
    DISABLED = "disabled"
    TIMEOUT = "timeout"
    NO_CLIENT = "no_client"

class SessionParam(BaseModel):
    project_id: str
    session_id: str
    api_url: str
    timeout: int

class SessionStateManager:
    """
    会话状态管理器
    处理会话状态的上传、下载和管理功能
    """
    
    def __init__(self, prm: SessionParam):
        """
        初始化会话状态管理器
        
        Args:
            session_id: 会话ID
        """
        self.session_id = prm.session_id
        self.console = RichConsole()
        
        # 从环境变量获取配置
        self.api_url = prm.api_url
        self.project_id = prm.project_id
        self.timeout = prm.timeout
        self.enabled = False
        if self.health_check():
            self.enabled = True
            self.console.print(f"[dim]✓ 会话管理服务正常: {self.session_id}[/dim]")
    
    def health_check(self):          
        url = f"{self.api_url}/health"
        req = urllib.request.Request(url)        
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            if response.status == 200:
                return True
            else:
                return False


    async def upload_session_state(
        self, 
        agent_name: str,
        agent: Optional[ComponentModel],
        state: Mapping[str, Any],
        task: str, 
    ) -> Tuple[SessionStateStatus, Optional[str]]:
        """
        上传会话状态到API
        
        Args:
            agent: 智能体配置
            state: 智能体状态数据
            task: 执行的任务内容


        Returns:
            Tuple[状态码, 文档ID或错误信息]
        """
        if not self.enabled:
            return SessionStateStatus.DISABLED, "会话状态上传已禁用"
        
        try:
            if agent:
                agent_document_data = {
                    "name": agent_name,
                    "description": f"{agent_name}_{self.session_id}",
                    "document_type": "agent_component_model",
                    "content": agent.model_dump(),
                    "session_id": self.session_id,
                    "tags": ["agent", "component_model"],
                    "is_public": False
                }
                status , txt = await self._upload_document(agent_document_data)
                if status != SessionStateStatus.SUCCESS:
                    self.console.print(f"[yellow]⚠️  会话状态上传失败: {txt}[/yellow]")
                
            # 创建JSON文档请求数据
            session_document_data = {
                "name": agent_name,
                "description": f"{agent_name}_session_state_{self.session_id}\ntask:{self._create_description(task)}",
                "document_type": "session_state",
                "content": state,
                "session_id": self.session_id,
                "tags": ["session_state", "agent_state"],
                "is_public": False
            }
            # 尝试上传
            return await self._upload_document(session_document_data)
            
        except Exception as e:
            self.console.print(f"[yellow]⚠️  会话状态上传异常: {str(e)}[/yellow]")
            return SessionStateStatus.FAILED, str(e)
    
    async def download_session_states(
        self,
        limit: int = 10,
        agent_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Tuple[SessionStateStatus, List[Dict[str, Any]]]:
        """
        下载会话状态历史
        
        Args:
            limit: 限制数量
            agent_name: 按智能体名称过滤
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Tuple[状态码, 会话状态列表]
        """
        if not self.enabled:
            return SessionStateStatus.DISABLED, []
        
        try:
            # 构建查询参数
            params = {
                "session_id": self.session_id,
                "limit": limit,
                "tags": ["session_state"],  # 修正为数组格式
                "sort_by": "updated_at",  # 添加排序字段
                "sort_order": -1  # 降序排列，获取最新的
            }
            
            if agent_name:
                params["name_pattern"] = agent_name  # 修正参数名
            if start_date:
                params["created_after"] = start_date  # 使用 API 支持的参数名
            if end_date:
                params["created_before"] = end_date  # 使用 API 支持的参数名
            
            return await self._download_documents(params)
            
        except Exception as e:
            self.console.print(f"[yellow]⚠️  会话状态下载异常: {str(e)}[/yellow]")
            return SessionStateStatus.FAILED, []
    
    async def restore_session_state(
        self, 
        document_id: str
    ) -> Tuple[SessionStateStatus, Optional[Dict[str, Any]]]:
        """
        恢复特定的会话状态
        通过文档ID恢复指定的会话状态数据
        
        Args:
            document_id: 要恢复的文档ID
            
        Returns:
            Tuple[状态码, 会话状态数据]
        """
        if not self.enabled:
            return SessionStateStatus.DISABLED, None
        
        try:
            # 直接通过文档ID获取特定的会话状态
            status, document = await self._download_document(document_id)
            if status == SessionStateStatus.SUCCESS and document:
                # 验证这是一个会话状态文档
                if document.get('document_type') == 'session_state' and document.get('session_id') == self.session_id:
                    self.console.print(f"[green]✓ 恢复会话状态文档: {document_id}[/green]")
                    return SessionStateStatus.SUCCESS, document.get('content', {})
                else:
                    self.console.print(f"[yellow]⚠️  文档 {document_id} 不是有效的会话状态文档[/yellow]")
                    return SessionStateStatus.FAILED, None
            else:
                self.console.print(f"[yellow]⚠️  未找到文档: {document_id}[/yellow]")
                return SessionStateStatus.FAILED, None
            
        except Exception as e:
            self.console.print(f"[yellow]⚠️  会话状态恢复异常: {str(e)}[/yellow]")
            return SessionStateStatus.FAILED, None

    async def restore_agent_session_state(
        self, 
        agent_name: str
    ) -> Tuple[SessionStateStatus, Optional[Dict[str, Any]]]:
        """
        恢复特定智能体的最新会话状态
        通过API获取指定session_id和agent_name的session_state数据，选择最新的数据来恢复会话状态
        
        Args:
            agent_name: 智能体名称
            
        Returns:
            Tuple[状态码, 会话状态数据]
        """
        if not self.enabled:
            return SessionStateStatus.DISABLED, None
        
        try:
            # 构建查询参数，获取指定agent的session_state数据
            params = {
                "session_id": self.session_id,
                "document_type": "session_state",
                "limit": 1,  # 只获取最新的一条
                "sort_by": "created_at",  # API 使用 sort_by 而不是 sort
                "sort_order": -1  # API 使用 sort_order，-1 表示降序
            }
            
            # 如果指定了agent_name，添加到查询条件
            if agent_name:
                params["name_pattern"] = agent_name  # API 使用 name_pattern 而不是 name
            
            # 获取session_state数据
            status, documents = await self._download_documents(params)
            if status == SessionStateStatus.SUCCESS and documents:
                latest_document = documents[0]
                self.console.print(f"[green]✓ 恢复智能体 '{agent_name}' 的会话状态: {latest_document.get('_id', 'unknown')}[/green]")
                return SessionStateStatus.SUCCESS, latest_document.get('content', {})
            else:
                self.console.print(f"[yellow]⚠️  未找到智能体 '{agent_name}' 的会话状态记录[/yellow]")
                return SessionStateStatus.FAILED, None
            
        except Exception as e:
            self.console.print(f"[yellow]⚠️  智能体会话状态恢复异常: {str(e)}[/yellow]")
            return SessionStateStatus.FAILED, None

    async def restore_latest_session_state(self) -> Tuple[SessionStateStatus, Optional[Dict[str, Any]]]:
        """
        恢复当前会话的最新会话状态
        
        Returns:
            Tuple[状态码, 最新的会话状态数据]
        """
        if not self.enabled:
            return SessionStateStatus.DISABLED, None
        
        try:
            # 构建查询参数，获取当前会话的最新session_state数据
            params = {
                "session_id": self.session_id,
                "document_type": "session_state",
                "tags": ["session_state"],
                "limit": 1,  # 只获取最新的一条
                "sort_by": "created_at",  # 按创建时间排序
                "sort_order": -1  # 降序，获取最新的
            }
            
            # 获取最新的会话状态数据
            status, documents = await self._download_documents(params)
            if status == SessionStateStatus.SUCCESS and documents:
                latest_document = documents[0]
                self.console.print(f"[green]✓ 恢复最新会话状态: {latest_document.get('_id', 'unknown')}[/green]")
                return SessionStateStatus.SUCCESS, latest_document.get('content', {})
            else:
                self.console.print("[yellow]⚠️  未找到会话状态记录[/yellow]")
                return SessionStateStatus.FAILED, None
        except Exception as e:
            self.console.print(f"[yellow]⚠️  恢复最新会话状态异常: {str(e)}[/yellow]")
            return SessionStateStatus.FAILED, None

    async def list_available_session_states(
        self,
        limit: int = 10,
        agent_name: Optional[str] = None
    ) -> Tuple[SessionStateStatus, List[Dict[str, Any]]]:
        """
        列出可用的会话状态记录
        用于选择要恢复的会话状态
        
        Args:
            limit: 限制数量
            agent_name: 按智能体名称过滤
            
        Returns:
            Tuple[状态码, 会话状态列表(包含基本信息)]
        """
        if not self.enabled:
            return SessionStateStatus.DISABLED, []
        
        try:
            # 构建查询参数
            params = {
                "session_id": self.session_id,
                "document_type": "session_state",
                "tags": ["session_state"],
                "limit": limit,
                "sort_by": "created_at",
                "sort_order": -1  # 降序，最新的在前
            }
            
            if agent_name:
                params["name_pattern"] = agent_name
            
            # 获取会话状态列表
            status, documents = await self._download_documents(params)
            if status == SessionStateStatus.SUCCESS:
                # 提取关键信息
                session_list = []
                for doc in documents:
                    session_info = {
                        "id": doc.get("_id"),
                        "name": doc.get("name"),
                        "description": doc.get("description"),
                        "created_at": doc.get("created_at"),
                        "updated_at": doc.get("updated_at"),
                        "tags": doc.get("tags", [])
                    }
                    session_list.append(session_info)
                
                self.console.print(f"[green]✓ 找到 {len(session_list)} 个会话状态记录[/green]")
                return SessionStateStatus.SUCCESS, session_list
            else:
                return status, []
            
        except Exception as e:
            self.console.print(f"[yellow]⚠️  获取会话状态列表异常: {str(e)}[/yellow]")
            return SessionStateStatus.FAILED, []
    
   
    def _create_description(self, task: str) -> str:
        """创建文档描述"""
        if len(task) > 50:
            return f"智能体会话状态 - {task[:50]}..."
        return f"智能体会话状态 - {task}"
    
    async def _upload_document(self, document_data: dict) -> Tuple[SessionStateStatus, Optional[str]]:
        """
        上传文档数据
        
        Args:
            document_data: 文档数据
            
        Returns:
            Tuple[状态码, 文档ID或错误信息]
        """
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "X-Project-ID": self.project_id
            }
            
            async with session.post(
                f"{self.api_url}/{self.project_id}/json-documents",
                json=document_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    document_id = result.get('_id', 'unknown')  
                    document_type = result.get('document_type', '')                  
                    self.console.print(f"[green]✓ {document_type}已上传: {document_id}[/green]")
                    return SessionStateStatus.SUCCESS, document_id
                else:
                    error_text = await response.text()
                    self.console.print(f"[yellow]⚠️  状态上传失败 (HTTP {response.status}): {error_text}[/yellow]")
                    return SessionStateStatus.FAILED, error_text                  

    
    async def _download_documents(self, params: dict) -> Tuple[SessionStateStatus, List[Dict[str, Any]]]:
        """
        从API下载文档列表
        
        Args:
            params: 查询参数
            
        Returns:
            Tuple[状态码, 文档列表]
        """

        # 尝试使用 aiohttp（推荐）
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "X-Project-ID": self.project_id
            }
            
            async with session.get(
                f"{self.api_url}/{self.project_id}/json-documents",
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    documents = result.get('data', []) if isinstance(result, dict) else result
                    return SessionStateStatus.SUCCESS, documents
                else:
                    error_text = await response.text()
                    self.console.print(f"[yellow]⚠️  文档下载失败 (HTTP {response.status}): {error_text}[/yellow]")
                    return SessionStateStatus.FAILED, []

    
    async def _download_document(self, document_id: str) -> Tuple[SessionStateStatus, Optional[Dict[str, Any]]]:
        """
        从API下载单个文档
        
        Args:
            document_id: 文档ID
            
        Returns:
            Tuple[状态码, 文档数据]
        """
        # 尝试使用 aiohttp（推荐）
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "X-Project-ID": self.project_id
            }
            
            async with session.get(
                f"{self.api_url}/{self.project_id}/json-documents/{document_id}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return SessionStateStatus.SUCCESS, result
                else:
                    error_text = await response.text()
                    self.console.print(f"[yellow]⚠️  文档下载失败 (HTTP {response.status}): {error_text}[/yellow]")
                    return SessionStateStatus.FAILED, None
                        
        
    