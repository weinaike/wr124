"""
遥测设置模块
负责OpenTelemetry的配置和初始化
"""
import uuid
import socket
import logging
from typing import Optional
from urllib.parse import urlparse
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.openai import OpenAIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


# 全局标记，确保OpenTelemetry组件只初始化一次
_global_initialized = False
_global_instrumentor_initialized = False


class TelemetrySetup:
    """遥测设置管理器"""
    
    def __init__(self, project_id: str, endpoint: str = "http://localhost:4317", enable_telemetry: bool = True):
        self.project_id = project_id
        self.endpoint = endpoint
        self.enable_telemetry = enable_telemetry
        self.tracer = None
        self._initialized = False
        self._connection_checked = False
        self._endpoint_available = False
        self.logger = logging.getLogger(__name__)
    
    def _check_endpoint_connection(self) -> bool:
        """
        检查端点连接是否可用
        
        Returns:
            True if endpoint is reachable, False otherwise
        """
        if self._connection_checked:
            return self._endpoint_available
        
        try:
            # 解析endpoint URL
            parsed = urlparse(self.endpoint)
            host = parsed.hostname or 'localhost'
            port = parsed.port or 4317
            
            # 尝试连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)  # 3秒超时
            result = sock.connect_ex((host, port))
            sock.close()
            
            self._endpoint_available = (result == 0)
            self._connection_checked = True
            
            if not self._endpoint_available:
                self.logger.warning(f"OpenTelemetry endpoint {self.endpoint} is not reachable. Telemetry will be disabled.")
            
            return self._endpoint_available
            
        except Exception as e:
            self.logger.warning(f"Failed to check OpenTelemetry endpoint {self.endpoint}: {e}. Telemetry will be disabled.")
            self._endpoint_available = False
            self._connection_checked = True
            return False
    
    def initialize(self) -> trace.Tracer:
        """
        初始化遥测设置
        
        Returns:
            配置好的追踪器
        """
        global _global_initialized, _global_instrumentor_initialized
        
        if self._initialized:
            if self.tracer is None:
                raise RuntimeError("Tracer is not initialized.")
            return self.tracer
        
        # 检查是否启用遥测
        if not self.enable_telemetry:
            self.logger.info("Telemetry is disabled by configuration.")
            # 创建一个基本的追踪器，不进行导出
            tracer_provider = TracerProvider(
                resource=Resource({"service.name": self.project_id})
            )
            trace.set_tracer_provider(tracer_provider)
            self.tracer = trace.get_tracer(self.project_id)
            self._initialized = True
            return self.tracer
        
        # 只有在全局未初始化时才设置TracerProvider
        if not _global_initialized:
            try:
                # 检查端点连接
                endpoint_available = self._check_endpoint_connection()
                
                # 设置追踪提供者
                tracer_provider = TracerProvider(
                    resource=Resource({"service.name": self.project_id})
                )
                
                if endpoint_available:
                    # 端点可用，使用OTLP导出器
                    try:
                        otel_exporter = OTLPSpanExporter(
                            endpoint=self.endpoint, 
                            insecure=True,
                            timeout=5  # 设置5秒超时
                        )
                        span_processor = BatchSpanProcessor(otel_exporter)
                        tracer_provider.add_span_processor(span_processor)
                        self.logger.info(f"OpenTelemetry OTLP exporter initialized with endpoint: {self.endpoint}")
                    except Exception as e:
                        self.logger.error(f"Failed to initialize OTLP exporter: {e}. Telemetry will be disabled.")
                else:
                    # 端点不可用，不添加任何导出器（静默模式）
                    self.logger.info("OpenTelemetry initialized in silent mode (no exporter).")
                
                # 检查是否已经有TracerProvider，如果没有才设置
                current_provider = trace.get_tracer_provider()
                if not isinstance(current_provider, TracerProvider):
                    trace.set_tracer_provider(tracer_provider)
                
                _global_initialized = True
            except Exception as e:
                # 如果TracerProvider已经设置，忽略错误
                if "not allowed" in str(e).lower() or "override" in str(e).lower():
                    _global_initialized = True
                else:
                    self.logger.error(f"Failed to initialize TracerProvider: {e}")
                    raise e
        
        # 只有在全局未初始化时才安装OpenAI仪表盘
        if not _global_instrumentor_initialized:
            try:
                OpenAIInstrumentor().instrument()
                _global_instrumentor_initialized = True
                self.logger.info("OpenAI instrumentation initialized.")
            except Exception as e:
                # 如果已经初始化过，忽略错误
                if "already instrumented" not in str(e).lower():
                    self.logger.warning(f"Failed to initialize OpenAI instrumentation: {e}")
                    # 不抛出异常，继续执行
        
        # 创建追踪器
        self.tracer = trace.get_tracer(self.project_id)
        self._initialized = True
        
        return self.tracer
    
    def create_session_span(self, session_id: Optional[str] = None):
        """
        创建会话级别的跟踪跨度
        
        Args:
            session_id: 会话ID，如果未提供将自动生成
            
        Returns:
            跟踪跨度上下文管理器
        """
        if not self._initialized or self.tracer is None:
            self.tracer = self.initialize()
        
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        if self.tracer is None:
            raise RuntimeError("Tracer is not initialized.")
        
        return self.tracer.start_as_current_span(name=session_id)
    
    def reset_connection_check(self):
        """
        重置连接检查状态，强制下次初始化时重新检查端点连接
        """
        self._connection_checked = False
        self._endpoint_available = False
    
    def is_endpoint_available(self) -> bool:
        """
        检查端点是否可用
        
        Returns:
            True if endpoint is available, False otherwise
        """
        if not self._connection_checked:
            self._check_endpoint_connection()
        return self._endpoint_available
