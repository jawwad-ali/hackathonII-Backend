"""Debug script to check if MCP tools are registered."""
from src.mcp_server.server import mcp

print(f"MCP instance: {mcp}")
print(f"MCP name: {mcp.name}")

# Check registered tools via tool manager
print("\n=== REGISTERED TOOLS ===")
tool_manager = mcp._tool_manager
print(f"Tool manager: {tool_manager}")

# Check internal tools dict
if hasattr(tool_manager, '_tools'):
    print(f"Number of tools (_tools): {len(tool_manager._tools)}")
    for name, tool in tool_manager._tools.items():
        print(f"  - {name}: {tool}")
elif hasattr(tool_manager, 'tools'):
    print(f"Number of tools (tools): {len(tool_manager.tools)}")
    for name, tool in tool_manager.tools.items():
        print(f"  - {name}: {tool}")
else:
    print("Tool manager attributes:")
    for attr in dir(tool_manager):
        if not attr.startswith('__'):
            print(f"  {attr}")
