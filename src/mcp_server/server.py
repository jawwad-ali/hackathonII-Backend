"""FastMCP server entry point for Todo database operations.

This module creates and configures the FastMCP server instance,
handles database initialization on startup, and manages the server lifecycle.
"""

import sys

from fastmcp import FastMCP

from src.mcp_server.database import create_db_and_tables

# Import models to ensure they are registered with SQLModel metadata
from src.mcp_server.models import Todo, TodoStatus  # noqa: F401

# Create FastMCP server instance
mcp = FastMCP("TodoDatabaseServer")

# When launched via `python -m src.mcp_server.server`, Python executes this module as
# `__main__`, but our tool modules import `src.mcp_server.server` to access `mcp`.
# Alias the module name to prevent a second import (which would create a second MCP
# server instance and result in missing/empty tool registration).
if __name__ == "__main__":
    sys.modules.setdefault("src.mcp_server.server", sys.modules[__name__])

# Import tool implementations to register them via @mcp.tool decorators
# Import directly from tool modules (not via __init__.py) to ensure decorators execute
import src.mcp_server.tools.create_todo  # noqa: F401
import src.mcp_server.tools.list_todos  # noqa: F401
import src.mcp_server.tools.update_todo  # noqa: F401
import src.mcp_server.tools.search_todos  # noqa: F401
import src.mcp_server.tools.delete_todo  # noqa: F401

# Note: Database initialization is deferred to avoid blocking MCP handshake
# Tables are created lazily on first tool call

# Debug: Print registered tools count
print(f"[MCP Server Debug] Tools imported. Registered: {len(mcp._tool_manager._tools)}", file=sys.stderr)
print(f"[MCP Server Debug] Tool names: {list(mcp._tool_manager._tools.keys())}", file=sys.stderr)


def main() -> None:
    """Main entry point for running the MCP server.

    This function runs the FastMCP server using stdio transport
    (standard input/output), which is the default MCP protocol.

    Database initialization is DEFERRED to avoid blocking the MCP handshake.
    Tables are created lazily on first tool call.

    Usage:
        python -m src.mcp_server.server
    """
    # Tools are imported at module level (see line 19), not here
    # This ensures @mcp.tool decorators execute during module import

    # No database initialization here - deferred to first tool call
    # This allows MCP server to respond to handshake quickly (<5s timeout)

    mcp.run()  # Uses stdio transport by default


if __name__ == "__main__":
    main()
