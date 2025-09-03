#!/usr/bin/env python3
"""
Debug script for DesktopCommanderMCP JSON Schema issues
"""
import asyncio
import json
from wr124.mcp import StdioServerParams, mcp_server_tools

async def debug_command_mcp():
    """Debug the command MCP server to find schema issues"""
    
    # Create the same server params as in config_manager.py
    server_params = StdioServerParams(
        command='node',
        args=["/home/wnk/code/DesktopCommanderMCP/dist/index.js"]
    )
    
    try:
        print("🔍 Starting MCP server debug...")
        tools = await mcp_server_tools(server_params)
        print(f"✅ Successfully got {len(tools)} tools")
        
        # Check each tool's schema for potential issues
        for i, tool in enumerate(tools):
            tool_name = tool.schema.get('name', f'Tool_{i}')
            print(f"\n🔧 Checking tool: {tool_name}")
            
            # Check inputSchema
            input_schema = tool.schema.get('inputSchema', {})
            if 'properties' in input_schema:
                for prop_name, prop_def in input_schema['properties'].items():
                    prop_type = prop_def.get('type')
                    if prop_type is None:
                        print(f"❌ FOUND ISSUE: Property '{prop_name}' has None type")
                        print(f"   Full property definition: {prop_def}")
                    elif prop_type == "null" or prop_type == []:
                        print(f"⚠️  Property '{prop_name}' has suspicious type: {prop_type}")
            
            # Print full schema for problematic tools
            if tool_name in ['give_feedback_to_desktop_commander', 'list_sessions', 'list_processes', 'get_usage_stats']:
                print(f"📋 Full schema for {tool_name}:")
                print(json.dumps(tool.schema, indent=2))
        
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_command_mcp())
