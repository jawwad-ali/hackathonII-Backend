"""FastMCP server entry point for Todo database operations.

This module creates and configures the FastMCP server instance,
handles database initialization on startup, and manages the server lifecycle.
"""

from fastmcp import FastMCP

from .database import create_db_and_tables

# Import models to ensure they are registered with SQLModel metadata
from .models import Todo, TodoStatus  # noqa: F401

# Create FastMCP server instance
mcp = FastMCP("TodoDatabaseServer")

# Initialize database tables on module load
# This ensures tables exist before any tools are called
try:
    create_db_and_tables()
    print("Database initialized successfully. Tables created.")
except Exception as e:
    print(f"Error initializing database: {e}")
    raise


# Tool implementations are imported at the bottom to avoid circular imports
# They self-register using the @mcp.tool decorator when imported


def main() -> None:
    """Main entry point for running the MCP server.

    This function runs the FastMCP server using stdio transport
    (standard input/output), which is the default MCP protocol.

    Usage:
        python -m src.mcp_server.server
        # Or using uvx:
        uvx fastmcp run src/mcp_server/server.py
    """
    # Import tools here to register them (avoids circular import at module level)
    from .tools import create_todo  # noqa: F401

    mcp.run()  # Uses stdio transport by default


if __name__ == "__main__":
    main()
