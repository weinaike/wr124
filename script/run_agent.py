import argparse
import os
import sys
import asyncio
from pathlib import Path
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.openai import OpenAIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


current_dir = os.getcwd()
# 添加项目根目录到Python路径
sys.path.insert(0, str(current_dir))

# Apply monkey patch for normalize_name issue
# sys.path.insert(0, '/home/wnk/code/wr124')
# from fix_normalize_name import apply_normalize_name_patch
# apply_normalize_name_patch()

from wr124.team_base import Team
from wr124.agent_base import BaseAgent


from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelFamily, ModelInfo
from autogen_ext.tools.mcp import StdioServerParams, StreamableHttpServerParams, SseServerParams
from autogen_agentchat.ui import Console
from dotenv import load_dotenv
import asyncio

from autogen_ext.tools.mcp import StdioServerParams, StreamableHttpServerParams, SseServerParams, mcp_server_tools, StdioMcpToolAdapter
from wr124.filesystem import tool_mapping

# Example usage
async def main(task:str = "What is the weather today?", project_id:str = "default"):


    # Set up telemetry span exporter.
    otel_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
    span_processor = BatchSpanProcessor(otel_exporter)

    # Set up telemetry trace provider.
    tracer_provider = TracerProvider(resource=Resource({"service.name": project_id}))
    tracer_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(tracer_provider)

    # Instrument the OpenAI Python library
    OpenAIInstrumentor().instrument()
    # we will get reference this tracer later using its service name
    # tracer = trace.get_tracer("autogen-test-agentchat")
    tracer = trace.get_tracer(project_id)

    print("Testing basic agent operation...")
    # Create team with MCP tools
    command_mcp_server = StreamableHttpServerParams(
        url="http://localhost/mcp",
        headers={"Authorization": "Bearer YOUR_ACCESS_TOKEN", "X-Project-ID": project_id},
        sse_read_timeout = 3600,  # 设置SSE读取超时时间为1小时
    ) 

    team = Team(model="glm-4.5")#"kimi-k2-0711-preview"
    await team.register_mcp_tools(command_mcp_server)

    with tracer.start_as_current_span("run_team"):
        await Console(team.run_stream(task=task))

if __name__ == "__main__":
    # Run the main function
    load_dotenv("/home/wnk/code/wr124/script/.env")
    print(os.environ)    
    
    task = "请问你有多少工具可用"
    asyncio.run(main(task=task))