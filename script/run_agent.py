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
from rich.console import Console as RichConsole


current_dir = os.getcwd()
# 添加项目根目录到Python路径
sys.path.insert(0, str(current_dir))

# Apply monkey patch for normalize_name issue
# sys.path.insert(0, '/home/wnk/code/wr124')
# from fix_normalize_name import apply_normalize_name_patch
# apply_normalize_name_patch()

from wr124.team_base import Team
from wr124.agent_base import BaseAgent
from wr124.util import print_tools

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelFamily, ModelInfo
from autogen_ext.tools.mcp import StdioServerParams, StreamableHttpServerParams, SseServerParams
from autogen_agentchat.ui import Console
from dotenv import load_dotenv
import asyncio

from autogen_ext.tools.mcp import StdioServerParams, StreamableHttpServerParams, SseServerParams, mcp_server_tools, StdioMcpToolAdapter
from wr124.filesystem import tool_mapping

async def main(task: str | None, project_id: str, enable_user_input: bool = False, debug = False):

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


    # Create team with MCP tools
    command_mcp_server = StreamableHttpServerParams(
        url="http://localhost/mcp",
        headers={"Authorization": os.getenv("SHRIMP_AUTH_TOKEN", ""), "X-Project-ID": project_id},
        sse_read_timeout = 3600,  # 设置SSE读取超时时间为1小时
    ) 

    team = Team(model="glm-4.5")
    if enable_user_input:
        team.enable_interactive_mode(use_default_callback=True)
    tools = await team.register_mcp_tools(command_mcp_server)
    if debug:
        print_tools(tools)

    with tracer.start_as_current_span("run_team"):
        await Console(team.run_stream(task=task))

if __name__ == "__main__":
    # Run the main function
    parser = argparse.ArgumentParser(description="Run agent with specified task and project ID.")
    parser.add_argument("-t", "--task", type=str, help="Task to run (if not provided, interactive mode will be enabled)")
    parser.add_argument("-p", "--project_id", type=str, help="Project ID (if not provided, uses current directory name)")
    parser.add_argument("-e", "--env_file", type=str, default="./script/.env", help="Path to .env file")
    parser.add_argument("-i", "--interactive", action="store_true", help="Enable interactive user input after task completion")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    # 处理 project_id：如果未提供，使用当前目录名
    if args.project_id is None:
        current_path = Path.cwd()
        args.project_id = current_path.name
        console = RichConsole()
        console.print(f"[dim]ℹ[/dim]  未指定 project_id，使用当前目录名: [bold cyan]{args.project_id}[/bold cyan]")

    load_dotenv(Path(args.env_file).expanduser(), verbose=True)
    print(os.environ)

    asyncio.run(main(task=args.task, 
                     project_id=args.project_id, 
                     enable_user_input=args.interactive,
                     debug=args.debug))