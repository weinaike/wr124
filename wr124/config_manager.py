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


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, session_id: Optional[str],
                 env_file: Optional[str] = None, 
                 project_id: Optional[str] = None):
        self.project_id = project_id or self._get_default_project_id()
        self.env_file = env_file or "./script/.env"
        self.session_id = session_id
        self._load_environment()
        
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
        
        # Shrimp任务管理器
        servers['shrimp'] = StdioServerParams(
            command='npx',
            args=["-y", "mcp-shrimp-task-manager"],
            read_timeout_seconds=600
        )
        
        servers['command'] = StdioServerParams(
            command='node',
            args=["/home/wnk/code/DesktopCommanderMCP/dist/index.js"],
            read_timeout_seconds=600
        )

        servers['docker'] = StdioServerParams(
            command='docker',
            args=["exec", "-i", "cppbuild", "node", "//usr/src/app/dist/index.js"],
            read_timeout_seconds=600
        )



        return servers
    
    @property
    def auth_token(self) -> str:
        """获取认证令牌"""
        return os.getenv("SHRIMP_AUTH_TOKEN", "")
