"""List todos tool implementation for FastMCP database server.

This module implements the list_todos MCP tool that retrieves all active todo items
from the PostgreSQL database using SQLModel and psycopg2.

The tool filters by status (active only) and returns MCP-compliant responses
to the AI agent.
"""

from typing import Optional

from sqlmodel import Session, select

from ..database import engine
from ..models import Todo, TodoStatus
from ..server import mcp


def list_todos(_test_session: Optional[Session] = None) -> str:
    """Retrieves all active todos from the database.

    This tool queries the database for todos with status='active', excluding
    completed and archived todos. Returns a formatted list with all todo details.

    Args:
        _test_session: Internal parameter for dependency injection during testing

    Returns:
        str: Human-readable summary with list of active todos

    Examples:
        >>> list_todos()
        "Found 2 active todos:
        [1] Buy groceries (active) - Created: 2025-12-29
        [2] Call dentist (active) - Created: 2025-12-29"

        >>> list_todos()  # When database is empty
        "Found 0 active todos. The list is empty."
    """
    # Use provided test session or create new session from engine
    if _test_session is not None:
        # Test mode: use provided session directly (no context manager)
        session = _test_session
        try:
            # Query database for active todos only
            statement = select(Todo).where(Todo.status == TodoStatus.ACTIVE)
            result = session.exec(statement)
            todos = result.all()

            # Handle empty result
            if not todos:
                return "Found 0 active todos. The list is empty."

            # Format response with all todo details
            count = len(todos)
            response_lines = [f"Found {count} active todo{'s' if count != 1 else ''}:"]

            for todo in todos:
                # Format each todo with ID, title, description (if exists), status, created_at
                todo_line = f"[{todo.id}] {todo.title}"
                if todo.description:
                    todo_line += f" - {todo.description}"
                todo_line += f" ({todo.status.value})"
                todo_line += f" - Created: {todo.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                response_lines.append(todo_line)

            return "\n".join(response_lines)

        except Exception as e:
            raise Exception(f"Database error while listing todos: {str(e)}")

    else:
        # Production mode: use session-per-tool pattern with context manager
        with Session(engine) as session:
            try:
                # Query database for active todos only
                statement = select(Todo).where(Todo.status == TodoStatus.ACTIVE)
                result = session.exec(statement)
                todos = result.all()

                # Handle empty result
                if not todos:
                    return "Found 0 active todos. The list is empty."

                # Format response with all todo details
                count = len(todos)
                response_lines = [f"Found {count} active todo{'s' if count != 1 else ''}:"]

                for todo in todos:
                    # Format each todo with ID, title, description (if exists), status, created_at
                    todo_line = f"[{todo.id}] {todo.title}"
                    if todo.description:
                        todo_line += f" - {todo.description}"
                    todo_line += f" ({todo.status.value})"
                    todo_line += f" - Created: {todo.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    response_lines.append(todo_line)

                return "\n".join(response_lines)

            except Exception as e:
                raise Exception(f"Database error while listing todos: {str(e)}")


# Create MCP tool wrapper that excludes test parameter
@mcp.tool
def list_todos_mcp() -> str:
    """Retrieves all active todos from the database.

    Returns only todos with status='active', excluding completed and archived items.

    Returns:
        str: Summary and list of active todos with details
    """
    return list_todos(_test_session=None)
