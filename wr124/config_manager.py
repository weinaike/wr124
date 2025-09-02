"""
配置管理模块
负责处理环境变量、模型配置、服务器配置等
"""
import os
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from autogen_ext.tools.mcp import StdioServerParams, StreamableHttpServerParams, SseServerParams
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelFamily, ModelInfo
from .session.session_state_manager import SessionParam

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, session_id: Optional[str],
                 env_file: Optional[str] = None, 
                 project_id: Optional[str] = None):
        self.project_id = project_id or self._get_default_project_id()
        self.env_file = env_file or "./script/.env"
        self.session_id = session_id
        self._load_environment()
        os.environ["SHRIMP_PROJECT_ID"] = self.project_id  # 设置环境变量以供其他模块使用
        os.environ["SHRIMP_SESSION_ID"] = self.session_id or ""
        
    def _get_default_project_id(self) -> str:
        """获取默认项目ID（使用当前目录名）"""
        return Path.cwd().name
    
    def _load_environment(self) -> None:
        """加载环境变量"""
        env_path = Path(self.env_file).expanduser()
        if env_path.exists():
            load_dotenv(env_path, verbose=True)
    
    def get_model_client(self, model: str = "glm-4.5") -> OpenAIChatCompletionClient:
        """创建模型客户端"""
        return OpenAIChatCompletionClient(
            model=model,
            model_info=ModelInfo(
                vision=False,
                function_calling=True,
                json_output=True,
                family=ModelFamily.GPT_4O,
                structured_output=True,
                multiple_system_messages=True,
            )
        )
    
    def get_mcp_servers(self) -> Dict[str, Any]:
        """获取MCP服务器配置"""
        servers = {}
        
        # 任务管理服务器
        servers['task'] = StreamableHttpServerParams(
            url="http://localhost/mcp",
            headers={
                "Authorization": os.getenv("SHRIMP_AUTH_TOKEN", ""), 
                "X-Project-ID": self.project_id,
                "X-Session-ID": self.session_id,
            },
            sse_read_timeout=600,
            timeout=600
        )
        
        # 基础工具服务器
        servers['base_tools'] = StreamableHttpServerParams(
            url="http://localhost:8080/mcp",
            sse_read_timeout=600,
        )
        
        servers['search'] = StdioServerParams(
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

        # # Shrimp任务管理器
        # servers['shrimp'] = StdioServerParams(
        #     command='npx',
        #     args=["-y", "mcp-shrimp-task-manager"],
        #     read_timeout_seconds=600
        # )
        
        servers['command'] = StdioServerParams(
            command='node',
            args=["/home/wnk/code/DesktopCommanderMCP/dist/index.js"],
            read_timeout_seconds=600
        )

        servers['docker'] = StdioServerParams(
            command='docker',
            args=["exec", "-i", "cppbuild", "node", "/usr/src/app/dist/index.js"],
            read_timeout_seconds=600
        )

        return servers
    
    def get_api_server(self):
        server = SessionParam(
            project_id=self.project_id,
            session_id=self.session_id,
            api_url="http://localhost/api",
            timeout=30
        )
        return server

    
    @property
    def auth_token(self) -> str:
        """获取认证令牌"""
        return os.getenv("SHRIMP_AUTH_TOKEN", "")
