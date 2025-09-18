"""
遥测设置模块
负责OpenTelemetry的配置和初始化
"""
import uuid
from typing import Optional
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
    
    def __init__(self, project_id: str, endpoint: str = "http://localhost:4317"):
        self.project_id = project_id
        self.endpoint = endpoint
        self.tracer = None
        self._initialized = False
    
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
        
        # 只有在全局未初始化时才设置TracerProvider
        if not _global_initialized:
            try:
                # 设置OTLP导出器
                otel_exporter = OTLPSpanExporter(endpoint=self.endpoint, insecure=True)
                span_processor = BatchSpanProcessor(otel_exporter)
                
                # 设置追踪提供者
                tracer_provider = TracerProvider(
                    resource=Resource({"service.name": self.project_id})
                )
                tracer_provider.add_span_processor(span_processor)
                
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
                    raise e
        
        # 只有在全局未初始化时才安装OpenAI仪表盘
        if not _global_instrumentor_initialized:
            try:
                OpenAIInstrumentor().instrument()
                _global_instrumentor_initialized = True
            except Exception as e:
                # 如果已经初始化过，忽略错误
                if "already instrumented" not in str(e).lower():
                    raise e
        
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
