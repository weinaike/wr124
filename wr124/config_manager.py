"""
配置管理模块 - 重构版本
使用配置文件替代硬编码配置
"""
import os
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
import json
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelFamily, ModelInfo
from .session.session_state_manager import SessionParam
from .config.models import ModelConfig, WR124Config, MCPServerConfig, MCPServerType
from .mcp import StdioServerParams, StreamableHttpServerParams, SseServerParams



class ConfigManager:
    """配置管理器 - 基于配置文件"""
    
    def __init__(self, session_id: Optional[str],
                 env_file: Optional[str] = None, 
                 project_id: Optional[str] = None,
                 config_profile: Optional[str] = None):
        """
        Initialize configuration manager
        
        Args:
            session_id: Session ID
            env_file: Environment file path (optional)
            project_id: Project ID (optional)
            config_profile: Configuration profile name
        """
        self.project_id = project_id or self._get_default_project_id()
        self.env_file = env_file
        self.session_id = session_id       
        self.config_profile = config_profile
        
        # Load configuration from files
        self._load_environment()
        self._load_configuration()
        
        # Set environment variables for compatibility
        os.environ["SHRIMP_PROJECT_ID"] = self.project_id
        os.environ["SHRIMP_SESSION_ID"] = self.session_id or ""
        
    def _get_default_project_id(self) -> str:
        """获取默认项目ID（使用当前目录名）"""
        return Path.cwd().name
    
    def _load_environment(self) -> None:
        """加载环境变量"""
        # Use provided env_file or default path
        if self.env_file:
            env_path = Path(self.env_file).expanduser()
            if env_path.exists():
                load_dotenv(env_path, verbose=True)
        else:
            load_dotenv(verbose=True)
    
    def _load_configuration(self) -> None:
        """从配置文件加载配置"""
        if self.config_profile is None:
            # 相对于运行目录
            path1 = ".wr124.json"
            # 相对于用户主目录
            path2 = str(Path.home() / ".wr124.json")
            # 相对该文件
            path3 = str(Path(__file__).parent / "config" / ".wr124.json")
            if Path(path1).exists():
                self.config_profile = path1
                print(f"Using config profile: {self.config_profile}")
            elif Path(path2).exists():
                self.config_profile = path2
                print(f"Using config profile: {self.config_profile}")
            elif Path(path3).exists():
                self.config_profile = path3
                print(f"Using config profile: {self.config_profile}")

        with open(self.config_profile) as f:
            base_config = json.load(f)

        self.config = WR124Config(**base_config)
    
    def get_model_client(self, model: Optional[str] = None) -> OpenAIChatCompletionClient:
        """创建模型客户端"""
        model_config = ModelConfig(model=os.getenv("WR124_DEFAULT_MODEL", "glm-4.5"), 
                                   base_url=os.getenv("OPENAI_BASE_URL", None), 
                                   api_key=os.getenv("OPENAI_API_KEY", None))

        if self.config.model:          
            model_config = self.config.model
        
        if model:
            model_config.name = model
            
        return OpenAIChatCompletionClient(
            model=model_config.name,
            timeout=model_config.timeout,
            temperature=model_config.temperature,
            max_retries=model_config.max_retries,
            api_key=model_config.api_key,
            base_url=model_config.base_url,
            model_info=ModelInfo(
                vision=model_config.vision,
                function_calling=model_config.function_calling,
                json_output=model_config.json_output,
                family=model_config.family,
                structured_output=model_config.structured_output,
                multiple_system_messages=model_config.multiple_system_messages,
            )
        )
    
    def _convert_mcp_config(self, server_config: MCPServerConfig) -> Any:
        """Convert MCPServerConfig to specific MCP parameter object with type inference"""
        # Infer server type if not explicitly specified
        server_type = server_config.type or server_config.infer_server_type()
        
        if server_type == MCPServerType.STDIO:
            return StdioServerParams(
                command=server_config.command,
                args=server_config.args or [],
                read_timeout_seconds=server_config.read_timeout_seconds or 30,
                env=server_config.env or {}
            )
        elif server_type == MCPServerType.STREAMABLE_HTTP:
            return StreamableHttpServerParams(
                url=server_config.url,
                headers=server_config.headers,
                sse_read_timeout=server_config.sse_read_timeout or 600,
                timeout=server_config.timeout or 30
            )
        elif server_type == MCPServerType.SSE:
            return SseServerParams(
                url=server_config.url,
                headers=server_config.headers,
                sse_read_timeout=server_config.sse_read_timeout or 600,
                timeout=server_config.timeout or 30
            )
        else:
            raise ValueError(f"Unsupported MCP server type: {server_type}")
    
    def get_mcp_servers(self) -> Dict[str, Any]:
        """获取MCP服务器配置"""
        servers = {}
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
        
        for server_name, server_config in self.config.mcpServers.items():
            try:
                servers[server_name] = self._convert_mcp_config(server_config)
            except Exception as e:
                print(f"Warning: Failed to configure MCP server '{server_name}': {e}")
                continue
                
        return servers
    
    def get_session_server(self) -> Optional[SessionParam]:
        """获取会话服务器配置"""
        if self.config.sessionServer is None:
            return SessionParam(
            project_id=self.project_id,
            session_id=self.session_id,
            api_url="http://localhost/api",
            timeout=30
        )        
        api_config = self.config.sessionServer
        return SessionParam(
            project_id=self.project_id,
            session_id=self.session_id,
            api_url=api_config.url,
            timeout=api_config.timeout
        )
    
    @property
    def auth_token(self) -> str:
        """获取认证令牌"""
        return os.getenv("SHRIMP_AUTH_TOKEN", "")