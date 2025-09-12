"""
Configuration data models using Pydantic
"""
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
from autogen_core.models import ModelFamily, ModelInfo

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