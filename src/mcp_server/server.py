"""FastMCP server entry point for Todo database operations.

This module creates and configures the FastMCP server instance,
handles database initialization on startup, and manages the server lifecycle.
"""

from fastmcp import FastMCP

from .database import create_db_and_tables

# Import models to ensure they are registered with SQLModel metadata
from .models import Todo, TodoStatus  # noqa: F401

# Create FastMCP server instance
mcp = FastMCP(
    name="TodoDatabaseServer",
    description="MCP database server for Todo management with CRUD operations"
)


@mcp.lifespan
async def lifespan():
    """Server lifespan context manager for initialization and cleanup.

    This function is called when the MCP server starts and stops.
    It handles database table creation on startup and cleanup on shutdown.

    Yields:
        None: Control back to the server after initialization
    """
    # Startup: Create database tables if they don't exist
    print("Initializing database...")
    try:
        create_db_and_tables()
        print("Database initialized successfully. Tables created.")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

    # Yield control to the server
    yield

    # Shutdown: Cleanup (currently no cleanup needed)
    print("Shutting down database server...")


# Tool implementations will be imported and registered here
# from .tools.create_todo import create_todo
# from .tools.list_todos import list_todos
# from .tools.update_todo import update_todo
# from .tools.delete_todo import delete_todo
# from .tools.search_todos import search_todos


def main() -> None:
    """Main entry point for running the MCP server.

    This function runs the FastMCP server using stdio transport
    (standard input/output), which is the default MCP protocol.

    Usage:
        python -m src.mcp_server.server
        # Or using uvx:
        uvx fastmcp run src/mcp_server/server.py
    """
    import asyncio
    asyncio.run(mcp.run_async(transport="stdio"))


if __name__ == "__main__":
    main()
