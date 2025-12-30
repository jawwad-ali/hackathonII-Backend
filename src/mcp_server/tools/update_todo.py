"""Update todo tool implementation for FastMCP database server.

This module implements the update_todo MCP tool that updates existing todo items
in the PostgreSQL database using SQLModel and psycopg2.

The tool supports partial updates (updating only selected fields) and validates
inputs using Pydantic schemas. Returns MCP-compliant responses to the AI agent.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from ..database import engine
from ..models import Todo, TodoStatus
from ..schemas import UpdateTodoInput
from ..server import mcp


def update_todo(
    id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    _test_session: Optional[Session] = None
) -> str:
    """Updates an existing todo item in the database.

    This tool supports partial updates - you can update only the fields you specify.
    All other fields remain unchanged. The updated_at timestamp is automatically
    updated on every modification.

    Args:
        id: Todo ID to update (required)
        title: New title (optional, max 200 chars, whitespace will be stripped)
        description: New description (optional, max 2000 chars, use empty string to clear)
        status: New status (optional, must be "active", "completed", or "archived")
        _test_session: Internal parameter for dependency injection during testing

    Returns:
        str: Human-readable success message with the updated todo details

    Raises:
        ValueError: If todo with given ID doesn't exist
        ValueError: If title is empty/whitespace-only or exceeds max length
        ValueError: If description exceeds max length
        ValueError: If status is not a valid enum value
        Exception: If database operation fails

    Examples:
        >>> update_todo(1, title="Buy groceries and cook dinner")
        "Todo updated successfully! ID: 1, Title: 'Buy groceries and cook dinner', Status: active"

        >>> update_todo(1, status="completed")
        "Todo updated successfully! ID: 1, Title: 'Buy groceries', Status: completed"

        >>> update_todo(1, title="New title", description="New description", status="archived")
        "Todo updated successfully! ID: 1, Title: 'New title', Status: archived"
    """
    # Convert string status to TodoStatus enum if provided
    status_enum = None
    if status is not None:
        try:
            status_enum = TodoStatus(status)
        except ValueError:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of: active, completed, archived"
            )

    # Validate input using Pydantic schema
    # This will raise ValueError if validation fails
    try:
        validated_input = UpdateTodoInput(
            id=id,
            title=title,
            description=description,
            status=status_enum
        )
    except Exception as e:
        # Re-raise validation errors with clear message
        raise ValueError(f"Validation error: {str(e)}")

    # Use provided test session or create new session from engine
    if _test_session is not None:
        # Test mode: use provided session directly (no context manager)
        session = _test_session
        try:
            # Retrieve existing todo by ID
            statement = select(Todo).where(Todo.id == validated_input.id)
            result = session.exec(statement)
            todo = result.first()

            # Check if todo exists
            if todo is None:
                raise ValueError(f"Todo with ID {validated_input.id} not found")

            # Update only the fields that were provided (partial update)
            if validated_input.title is not None:
                todo.title = validated_input.title

            if validated_input.description is not None:
                todo.description = validated_input.description

            if validated_input.status is not None:
                todo.status = validated_input.status

            # Always update the updated_at timestamp
            todo.updated_at = datetime.now(timezone.utc)

            # Commit changes to database
            session.add(todo)
            session.commit()
            session.refresh(todo)  # Refresh to get updated values

            # Return MCP-compliant response (FastMCP converts string to Content object)
            return (
                f"Todo updated successfully! "
                f"ID: {todo.id}, "
                f"Title: '{todo.title}', "
                f"Status: {todo.status.value}"
            )

        except ValueError:
            # Re-raise ValueError (validation errors, not found errors)
            raise
        except Exception as e:
            # Rollback on any other error
            session.rollback()
            raise Exception(f"Database error while updating todo: {str(e)}")

    else:
        # Production mode: use session-per-tool pattern with context manager
        with Session(engine) as session:
            try:
                # Retrieve existing todo by ID
                statement = select(Todo).where(Todo.id == validated_input.id)
                result = session.exec(statement)
                todo = result.first()

                # Check if todo exists
                if todo is None:
                    raise ValueError(f"Todo with ID {validated_input.id} not found")

                # Update only the fields that were provided (partial update)
                if validated_input.title is not None:
                    todo.title = validated_input.title

                if validated_input.description is not None:
                    todo.description = validated_input.description

                if validated_input.status is not None:
                    todo.status = validated_input.status

                # Always update the updated_at timestamp
                todo.updated_at = datetime.now(timezone.utc)

                # Commit changes to database
                session.add(todo)
                session.commit()
                session.refresh(todo)  # Refresh to get updated values

                # Return MCP-compliant response (FastMCP converts string to Content object)
                return (
                    f"Todo updated successfully! "
                    f"ID: {todo.id}, "
                    f"Title: '{todo.title}', "
                    f"Status: {todo.status.value}"
                )

            except ValueError:
                # Re-raise ValueError (validation errors, not found errors)
                raise
            except Exception as e:
                # Rollback on any other error
                session.rollback()
                raise Exception(f"Database error while updating todo: {str(e)}")


# Create MCP tool wrapper that excludes test parameter
@mcp.tool
def update_todo_mcp(
    id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None
) -> str:
    """Updates an existing todo item in the database.

    Supports partial updates - only specified fields are updated.
    The updated_at timestamp is automatically updated.

    Args:
        id: Todo ID to update (required)
        title: New title (optional, max 200 chars)
        description: New description (optional, max 2000 chars)
        status: New status (optional: "active", "completed", or "archived")

    Returns:
        str: Success message with updated todo details
    """
    return update_todo(
        id=id,
        title=title,
        description=description,
        status=status,
        _test_session=None
    )
