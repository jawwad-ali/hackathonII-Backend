"""Delete todo tool implementation for FastMCP database server.

This module implements the delete_todo MCP tool that permanently removes todo items
from the PostgreSQL database using SQLModel and psycopg2 (hard delete).

The tool validates that the todo exists before deletion and provides clear error
messages for non-existent IDs. Returns MCP-compliant responses to the AI agent.
"""

from typing import Optional

from sqlmodel import Session, select

from ..database import engine
from ..models import Todo
from ..server import mcp


def delete_todo(id: int, _test_session: Optional[Session] = None) -> str:
    """Permanently deletes a todo from the database (hard delete).

    This tool performs a hard delete, completely removing the todo from the database.
    The todo cannot be recovered after deletion. Raises an error if the todo ID
    doesn't exist.

    Args:
        id: Todo ID to delete (required)
        _test_session: Internal parameter for dependency injection during testing

    Returns:
        str: Human-readable confirmation message with deleted todo ID

    Raises:
        ValueError: If todo with given ID doesn't exist
        Exception: If database operation fails

    Examples:
        >>> delete_todo(1)
        "Todo deleted successfully! ID: 1 has been permanently removed."

        >>> delete_todo(99999)
        ValueError: Todo with ID 99999 not found
    """
    # Use provided test session or create new session from engine
    if _test_session is not None:
        # Test mode: use provided session directly (no context manager)
        session = _test_session
        try:
            # Retrieve existing todo by ID
            statement = select(Todo).where(Todo.id == id)
            result = session.exec(statement)
            todo = result.first()

            # Check if todo exists - raise error BEFORE attempting delete
            if todo is None:
                raise ValueError(f"Todo with ID {id} not found")

            # Store todo details for confirmation message
            todo_id = todo.id

            # Perform hard delete
            session.delete(todo)
            session.commit()

            # Return MCP-compliant response (FastMCP converts string to Content object)
            return f"Todo deleted successfully! ID: {todo_id} has been permanently removed."

        except ValueError:
            # Re-raise ValueError (not found errors)
            raise
        except Exception as e:
            # Rollback on any other error
            session.rollback()
            raise Exception(f"Database error while deleting todo: {str(e)}")

    else:
        # Production mode: use session-per-tool pattern with context manager
        with Session(engine) as session:
            try:
                # Retrieve existing todo by ID
                statement = select(Todo).where(Todo.id == id)
                result = session.exec(statement)
                todo = result.first()

                # Check if todo exists - raise error BEFORE attempting delete
                if todo is None:
                    raise ValueError(f"Todo with ID {id} not found")

                # Store todo details for confirmation message
                todo_id = todo.id

                # Perform hard delete
                session.delete(todo)
                session.commit()

                # Return MCP-compliant response (FastMCP converts string to Content object)
                return f"Todo deleted successfully! ID: {todo_id} has been permanently removed."

            except ValueError:
                # Re-raise ValueError (not found errors)
                raise
            except Exception as e:
                # Rollback on any other error
                session.rollback()
                raise Exception(f"Database error while deleting todo: {str(e)}")


# Create MCP tool wrapper that excludes test parameter
@mcp.tool
def delete_todo_mcp(id: int) -> str:
    """Permanently deletes a todo by ID (hard delete).

    Removes the todo completely from the database. Cannot be recovered after deletion.
    Raises an error if the todo ID doesn't exist.

    Args:
        id: Todo ID to delete

    Returns:
        str: Confirmation message with deleted todo ID

    Raises:
        ValueError: If todo with given ID doesn't exist
    """
    return delete_todo(id=id, _test_session=None)
