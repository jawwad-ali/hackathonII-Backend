"""Search todos tool implementation for FastMCP database server.

This module implements the search_todos MCP tool that searches for todos by keyword
in title or description fields. Only returns active todos (excludes completed/archived).

The search is case-insensitive and uses ILIKE pattern matching for flexible keyword searches.
"""

from typing import Optional

from sqlmodel import Session, select, or_

from ..database import engine
from ..models import Todo, TodoStatus
from ..server import mcp


def search_todos(keyword: str, _test_session: Optional[Session] = None) -> str:
    """Searches active todos by keyword in title or description.

    This tool performs case-insensitive keyword matching across both title and
    description fields, returning only active todos that match. Completed and
    archived todos are excluded from results.

    Args:
        keyword: Search keyword (case-insensitive, searches title and description)
        _test_session: Internal parameter for dependency injection during testing

    Returns:
        str: Human-readable summary with list of matching todos

    Examples:
        >>> search_todos("grocery")
        "Found 2 todos matching 'grocery':
        [1] Buy groceries - Weekly shopping (active) - Created: 2025-12-29
        [3] Plan grocery delivery - Setup delivery project (active) - Created: 2025-12-29"

        >>> search_todos("nonexistent")
        "Found 0 todos matching 'nonexistent'. No results."
    """
    # Use provided test session or create new session from engine
    if _test_session is not None:
        # Test mode: use provided session directly (no context manager)
        session = _test_session
        try:
            # Build search query: keyword in title OR description, AND status is active
            # Use ILIKE for case-insensitive pattern matching
            search_pattern = f"%{keyword}%"
            statement = select(Todo).where(
                or_(
                    Todo.title.ilike(search_pattern),
                    Todo.description.ilike(search_pattern)
                ),
                Todo.status == TodoStatus.ACTIVE
            )

            result = session.exec(statement)
            todos = result.all()

            # Handle empty result
            if not todos:
                return f"Found 0 todos matching '{keyword}'. No results."

            # Format response with all todo details
            count = len(todos)
            response_lines = [f"Found {count} todo{'s' if count != 1 else ''} matching '{keyword}':"]

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
            raise Exception(f"Database error while searching todos: {str(e)}")

    else:
        # Production mode: use session-per-tool pattern with context manager
        with Session(engine) as session:
            try:
                # Build search query: keyword in title OR description, AND status is active
                # Use ILIKE for case-insensitive pattern matching
                search_pattern = f"%{keyword}%"
                statement = select(Todo).where(
                    or_(
                        Todo.title.ilike(search_pattern),
                        Todo.description.ilike(search_pattern)
                    ),
                    Todo.status == TodoStatus.ACTIVE
                )

                result = session.exec(statement)
                todos = result.all()

                # Handle empty result
                if not todos:
                    return f"Found 0 todos matching '{keyword}'. No results."

                # Format response with all todo details
                count = len(todos)
                response_lines = [f"Found {count} todo{'s' if count != 1 else ''} matching '{keyword}':"]

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
                raise Exception(f"Database error while searching todos: {str(e)}")


# Create MCP tool wrapper that excludes test parameter
@mcp.tool
def search_todos_mcp(keyword: str) -> str:
    """Searches active todos by keyword in title or description.

    Performs case-insensitive search across title and description fields.
    Returns only todos with status='active', excluding completed and archived items.

    Args:
        keyword: Search keyword (case-insensitive, searches title and description)

    Returns:
        str: Summary and list of matching todos with details
    """
    return search_todos(keyword=keyword, _test_session=None)
