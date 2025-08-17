import asyncio
from fastmcp.client.transports import StreamableHttpTransport, StdioTransport
from fastmcp.client import Client
from mcp.types import CallToolResult
import json

# --- Configuration ---
PROJECT_ID = "default"
AUTH_TOKEN = "user-secret-token-for-alpha"
SERVER_URL = "http://127.0.0.1:4444/mcp"

# --- Client Setup ---

def get_mcp_client(project_id: str, auth_token: str) -> Client:
    """
    Creates and configures a FastMCP client to communicate with a specific
    project on the server.
    """
    print(f"Connecting to project: {project_id}")
    transport = StreamableHttpTransport(
        url=SERVER_URL,
        headers={
            "Authorization": f"Bearer {auth_token}",
            "X-Project-ID": project_id,
        }
    )
    return Client(transport)

def get_stdio_client() -> Client:
    transport = StdioTransport(command="npx", 
                               args=["-y","@adenot/mcp-google-search"]
                            )
    return Client(transport)

def get_result_data(result: CallToolResult):
    """Extracts the actual data from a tool call result."""
    if result and result.content:
        # First try to get structured data
        if hasattr(result, 'data') and result.data:
            return result.data
        
        # Then try text content, and parse as JSON if possible
        text_content = result.content[0].text
        try:
            # Try to parse as JSON in case it's a serialized dictionary
            import json
            return json.loads(text_content)
        except (json.JSONDecodeError, ValueError):
            # If it's not JSON, return as is
            return text_content
    return None

async def main():
    """
    An example workflow demonstrating how to use the multi-tenant client
    with the correct client.call_tool() method.
    """
    try:    
        client:Client = get_mcp_client(PROJECT_ID, AUTH_TOKEN)
        client2:Client = get_stdio_client()
        tools = await client2.list_tools()

        print(tools)

        print(f"✅ Connecting to server at {SERVER_URL}...")
    except Exception as e:
        print(f"❌ Could not connect to server at {SERVER_URL}: \n{e}")
        return

    async with client:
        # 2. Check if the server is healthy

        # health_result = await client.call_tool("health_check", {})
        
        # print(f"✅ Server health check: {health_result}")


        # 3. Use a project-specific tool: list tasks
        try:
            print("\nListing initial tasks...")
            tasks_result = await client.call_tool("list_tasks", {})
            tasks = get_result_data(tasks_result)
            
            if tasks and isinstance(tasks, list):
                for task in tasks:
                    print(f"  - Task {task.get('id')}: {task.get('name')}")
            else:
                print("  No tasks found in this project.")

            # # 4. Create a new task in our project
            # print("\nCreating a new task...")
            # new_task_payload = {
            #     "name": "Setup multi-tenant authentication",
            #     "description": "Extend the server to validate auth tokens.",
            # }
            # created_task_result = await client.call_tool("create_task", {"task_create": new_task_payload})
            # created_task = get_result_data(created_task_result)
            
            # if created_task:
            #     print(f"  ✅ Created task: {created_task.get('name')} (ID: {created_task.get('id')})")

            # 5. List tasks again to see the new one
            print("\nListing tasks again...")
            tasks_result_after_create = await client.call_tool("list_tasks", {})
            tasks_after = get_result_data(tasks_result_after_create)

            if tasks_after and isinstance(tasks_after, list):
                for task in tasks_after:
                    print(f"  - Task {task.get('id')}: {task.get('name')}")
            # 5. List tasks again to see the new one
            print("\nSplitting tasks again...")
            content = '{"operator":"user","tasks": "[\\n  {\\n    \\"name\\": \\"修正TodoRead工具实现\\",\\n    \\"description\\": \\"检查并修正TodoRead工具，确保符合指定的接口格式要求\\",\\n    \\"status\\": \\"pending\\",\\n    \\"dependencies\\": [],\\n    \\"implementation_guide\\": \\"检查todo_read.py文件，确保__call__方法不需要参数，返回正确的todo列表格式\\",\\n    \\"verification_criteria\\": \\"TodoRead工具能够正确读取并返回todo列表，符合接口规范\\"\\n  },\\n  {\\n    \\"name\\": \\"修正TodoWrite工具实现\\",\\n    \\"description\\": \\"修正TodoWrite工具，使其接受包含todos字段的参数对象，而不是直接接受todos数组\\",\\n    \\"status\\": \\"pending\\",\\n    \\"dependencies\\": [],\\n    \\"implementation_guide\\": \\"修改todo_write.py的__call__方法，使其接受包含todos字段的字典参数，符合JSON Schema要求\\",\\n    \\"verification_criteria\\": \\"TodoWrite工具能够正确处理包含todos字段的参数对象\\"\\n  },\\n  {\\n    \\"name\\": \\"验证工具接口兼容性\\",\\n    \\"description\\": \\"创建测试验证修正后的工具是否符合指定的接口格式要求\\",\\n    \\"status\\": \\"pending\\",\\n    \\"dependencies\\": [\\"修正TodoRead工具实现\\", \\"修正TodoWrite工具实现\\"],\\n    \\"implementation_guide\\": \\"创建测试脚本验证TodoRead和TodoWrite工具的接口格式是否符合要求\\",\\n    \\"verification_criteria\\": \\"两个工具的接口完全符合指定的JSON Schema格式\\"\\n  }\\n]", "update_mode": "clearAllTasks"}'
            param = json.loads(content)
            # print(param)
            print(json.loads(param['tasks']))
            with open("test.json", "w") as f:
                f.write(param['tasks'])
            split_tasks_result = await client.call_tool("split_tasks", param)
            tasks_after = get_result_data(split_tasks_result)
            # print(tasks_after)
            with open("test_out.json", "w") as f:
                f.write(json.dumps(tasks_after, ensure_ascii=False, indent=2))

            # if tasks_after and isinstance(tasks_after, list):
            #     for task in tasks_after:
            #         print(f"  - Task {task.get('id')}: {task.get('name')}")
            # # 6. Test todo_read and todo_write tools
            print("\nTesting todo_read and todo_write tools...")
            
# 7. Create a test task using split_tasks as create alternative
            print("\nCreating test task for todo testing...")
            test_tasks = [
                {
                    "name": "测试todo工具",
                    "description": "用于测试todo_read和todo_write工具的任务",
                    "status": "pending",
                    "priority": "high"
                }
            ]
            
            create_result = await client.call_tool("split_tasks", {
                "tasks_raw": json.dumps(test_tasks, ensure_ascii=False),
                "update_mode": "clearAllTasks"  
            })
            tasks_result = get_result_data(create_result)
            
            task_id = None
            if tasks_result and isinstance(tasks_result, list) and len(tasks_result) > 0:
                task_id = tasks_result[0].get('id')
                print(f"  ✅ Created test task with ID: {task_id}")
            elif tasks_after and isinstance(tasks_after, list) and len(tasks_after) > 0:
                task_id = tasks_after[0].get('id')
                print(f"  Using existing task ID: {task_id}")
            
            if not task_id:
                print("  No tasks available for todo testing")
            else:
                # Test todo_read first
                print("\nReading initial todos...")
                todo_read_result = await client.call_tool("todo_read", {"task_id": task_id, "project_id": PROJECT_ID})
                todos = get_result_data(todo_read_result)
                print(f"  Initial todos: {todos}")
                
                # Test todo_write with sample todos
                print("\nWriting new todos...")
                new_todos = [
                    {
                        "id": "todo_1",
                        "content": "Implement MCP todo tools",
                        "priority": "high",
                        "status": "pending"
                    },
                    {
                        "id": "todo_2", 
                        "content": "Test todo functionality",
                        "priority": "medium",
                        "status": "pending"
                    }
                ]
                todo_write_result = await client.call_tool("todo_write", {
                    "task_id": task_id,
                    "todos": new_todos,
                    "project_id": PROJECT_ID
                })
                write_result = get_result_data(todo_write_result)
                print(f"  Write result: {write_result}")
                
                # Test todo_read again to verify
                print("\nReading todos after write...")
                todo_read_result_after = await client.call_tool("todo_read", {"task_id": task_id, "project_id": PROJECT_ID})
                todos_after = get_result_data(todo_read_result_after)
                print(f"  Todos after write: {todos_after}")
                
                # Verify todos were written correctly
                if todos_after and len(todos_after) >= len(new_todos):
                    print("  ✅ Todo write/read test successful")
                else:
                    print("  ❌ Todo write/read test failed")

        except Exception as e:
            print(f"\n❌ An error occurred during tool execution: {e}")
            import traceback
            traceback.print_exc()
            print("  Ensure the server is running and the project ID is correct.")


if __name__ == "__main__":


    asyncio.run(main())


    
