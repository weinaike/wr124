"""
配置管理模块 - 重构版本
使用配置文件替代硬编码配置
"""
import os
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv
import json
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelInfo
from .session.session_state_manager import SessionParam
from .mcp import StdioServerParams, StreamableHttpServerParams, SseServerParams



class MCPServerType(str, Enum):
    """MCP Server types"""
    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable_http"
    SSE = "sse"


class ModelConfig(BaseModel):
    """Model configuration"""
    model_config = {"arbitrary_types_allowed": True}
    
    name: str = Field(default="glm-4.5", description="Model name")
    timeout: int = Field(default=600, description="Request timeout in seconds")
    temperature: float = Field(default=0.6, description="Model temperature")
    max_retries: int = Field(default=1, description="Maximum retry attempts")
    api_key: Optional[str] = Field(default=None, description="API key for the model")
    base_url: Optional[str] = Field(default=None, description="Base URL for the model API")
    vision: bool = Field(default=False, description="Whether model supports vision")
    function_calling: bool = Field(default=True, description="Whether model supports function calling")
    json_output: bool = Field(default=True, description="Whether model supports JSON output")
    family: str = Field(default="gpt-4o", description="Model family")
    structured_output: bool = Field(default=True, description="Whether model supports structured output")
    multiple_system_messages: bool = Field(default=True, description="Whether model supports multiple system messages")


class MCPServerConfig(BaseModel):
    """MCP Server configuration - Claude Code compatible format"""
    command: Optional[str] = Field(default=None, description="Command for stdio types")
    args: Optional[List[str]] = Field(default=None, description="Command arguments")
    env: Optional[Dict[str, str]] = Field(default=None, description="Environment variables")
    type: Optional[MCPServerType] = Field(default=None, description="Server type (optional)")
    url: Optional[str] = Field(default=None, description="Server URL for HTTP types")
    headers: Optional[Dict[str, str]] = Field(default=None, description="HTTP headers")
    sse_read_timeout: Optional[int] = Field(default=None, description="SSE read timeout")
    read_timeout_seconds: Optional[int] = Field(default=None, description="Read timeout in seconds")
    timeout: Optional[int] = Field(default=None, description="General timeout")

    @validator('url')
    def validate_url_for_http_types(cls, v, values):
        server_type = values.get('type')
        if server_type in [MCPServerType.STREAMABLE_HTTP, MCPServerType.SSE] and not v:
            raise ValueError("URL is required for HTTP server types")
        return v

    @validator('command')
    def validate_command_for_stdio_types(cls, v, values):
        server_type = values.get('type')
        if server_type == MCPServerType.STDIO and not v:
            raise ValueError("Command is required for stdio server types")
        return v

    def infer_server_type(self) -> MCPServerType:
        """Infer server type based on configuration"""
        if self.command:
            return MCPServerType.STDIO
        elif self.url:
            if self.url.startswith(('http://', 'https://')):
                # Check if it's SSE by looking at URL patterns or explicit type
                if self.type == MCPServerType.SSE or '/sse' in self.url or self.sse_read_timeout:
                    return MCPServerType.SSE
                return MCPServerType.STREAMABLE_HTTP
        return MCPServerType.STDIO  # Default fallback


class APIServerConfig(BaseModel):
    """API Server configuration"""
    url: str = Field(description="API server URL")
    timeout: int = Field(default=30, description="Request timeout in seconds")


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )


class WR124Config(BaseModel):
    """Main WR124 configuration"""
    model: Optional[ModelConfig] = Field(default=None)
    mcpServers: Optional[Dict[str, MCPServerConfig]] = Field(default_factory=dict)
    sessionServer: Optional[APIServerConfig] = Field(default=None)
    logging: Optional[LoggingConfig] = Field(default_factory=LoggingConfig)
    allowedMcpServers: Optional[List[str]] = Field(default_factory=list)


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
            if Path(path1).exists():
                self.config_profile = path1
                print(f"Using config profile: {self.config_profile}")
            elif Path(path2).exists():
                self.config_profile = path2
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
            if server_name not in self.config.allowedMcpServers:
                print(f"Warning: MCP server '{server_name}' is not in allowedMcpServers, skipping.")
                continue
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