import argparse
import os
import sys
import asyncio
from pathlib import Path

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
async def main(task:str = "What is the weather today?"):
    print("Testing basic agent operation...")
    # Create team with MCP tools
    command_mcp_server = StreamableHttpServerParams(
        url="http://localhost:4444/mcp",
        headers={"Authorization": "Bearer YOUR_ACCESS_TOKEN", "X-Project-ID": "default"},
        sse_read_timeout = 3600,  # 设置SSE读取超时时间为1小时
    )
    
    tools = list(tool_mapping.values())

    team = Team(model="glm-4.5", mcp_tools=[command_mcp_server])#"kimi-k2-0711-preview"
    # agent = BaseAgent(name="WorkerAgent", model_client=model_client, tools=tools)

    await Console(team.run_stream(task=task))

if __name__ == "__main__":
    # Run the main function
    load_dotenv("/home/wnk/code/wr124/script/.env")
    print(os.environ)
    task = '''
  格努以下工具的描述，编写实际实现的方法。 即实现两个工具， TodoRead 和 TodoWrite。 用python实现，代码写入到/home/wnk/code/wr124/todo目录下
  todo清单要求在工具内部实现持久化同步。 查询目录下的已有实现， 进行修正， 注意，要求接口函数符合一下格式要求。且两者要统一考虑，数据共享。

  "TodoRead": {
    "description": "Use this tool to read the current to-do list for the session. ",
    "parameters": {
      "$schema": &quot;http://json-schema.org/draft-07/schema#",
      "additionalProperties": false,
      "description": "No input is required, leave this field blank. NOTE that we do not require a dummy object, placeholder string or a key like \"input\" or \"empty\". LEAVE IT BLANK.",
      "properties": {},
      "type": "object"
    }
  },
  "TodoWrite": {
    "description": "Use this tool to create and manage a structured task list for your current coding session. \n",
    "parameters": {
      "$schema": &quot;http://json-schema.org/draft-07/schema#",
      "additionalProperties": false,
      "properties": {
        "todos": {
          "description": "The updated todo list",
          "items": {
            "additionalProperties": false,
            "properties": {
              "content": {
                "minLength": 1,
                "type": "string"
              },
              "id": {
                "type": "string"
              },
              "priority": {
                "enum": ["high", "medium", "low"],
                "type": "string"
              },
              "status": {
                "enum": ["pending", "in_progress", "completed"],
                "type": "string"
              }
            },
            "required": ["content", "status", "priority", "id"],
            "type": "object"
          },
          "type": "array"
        }
      },
      "required": ["todos"],
      "type": "object"
    }
  },


'''

    task = "重点测试 query_memories 工具"
    asyncio.run(main(task=task))