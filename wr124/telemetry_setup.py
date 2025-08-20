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
        if self._initialized:
            return self.tracer
        
        # 设置OTLP导出器
        otel_exporter = OTLPSpanExporter(endpoint=self.endpoint, insecure=True)
        span_processor = BatchSpanProcessor(otel_exporter)
        
        # 设置追踪提供者
        tracer_provider = TracerProvider(
            resource=Resource({"service.name": self.project_id})
        )
        tracer_provider.add_span_processor(span_processor)
        trace.set_tracer_provider(tracer_provider)
        
        # 安装OpenAI库的仪表盘
        OpenAIInstrumentor().instrument()
        
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
        if not self._initialized:
            self.initialize()
        
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        return self.tracer.start_as_current_span(name=session_id)
