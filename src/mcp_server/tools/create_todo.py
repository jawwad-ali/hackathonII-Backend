"""Create todo tool implementation for FastMCP database server.

This module implements the create_todo MCP tool that creates new todo items
in the PostgreSQL database using SQLModel and psycopg2.

The tool validates inputs using Pydantic schemas and returns MCP-compliant
responses to the AI agent.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from ..database import engine
from ..models import Todo, TodoStatus
from ..schemas import CreateTodoInput
from ..server import mcp


def create_todo(title: str, description: Optional[str] = None, _test_session: Optional[Session] = None) -> str:
    """Creates a new todo item in the database.

    This tool creates a new todo with the provided title and optional description.
    The todo is automatically assigned an active status and timestamps are
    auto-generated.

    Args:
        title: Todo title (required, max 200 chars, whitespace will be stripped)
        description: Optional todo description (max 2000 chars)
        _test_session: Internal parameter for dependency injection during testing

    Returns:
        str: Human-readable success message with the created todo details

    Raises:
        ValueError: If title is empty/whitespace-only or exceeds max length
        ValueError: If description exceeds max length
        Exception: If database operation fails

    Examples:
        >>> create_todo("Buy groceries")
        "Todo created successfully! ID: 1, Title: 'Buy groceries', Status: active"

        >>> create_todo("Call dentist", "Schedule annual checkup")
        "Todo created successfully! ID: 2, Title: 'Call dentist', Status: active"
    """
    # Validate input using Pydantic schema
    # This will raise ValueError if validation fails
    try:
        validated_input = CreateTodoInput(title=title, description=description)
    except Exception as e:
        # Re-raise validation errors with clear message
        raise ValueError(f"Validation error: {str(e)}")

    # Use provided test session or create new session from engine
    if _test_session is not None:
        # Test mode: use provided session directly (no context manager)
        session = _test_session
        try:
            # Create new Todo instance with validated data
            # Title is already stripped by CreateTodoInput validator
            todo = Todo(
                title=validated_input.title,
                description=validated_input.description,
                status=TodoStatus.ACTIVE,  # New todos are always active
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            # Add to session and commit to database
            session.add(todo)
            session.commit()
            session.refresh(todo)  # Refresh to get auto-generated ID

            # Return MCP-compliant response (FastMCP converts string to Content object)
            return (
                f"Todo created successfully! "
                f"ID: {todo.id}, "
                f"Title: '{todo.title}', "
                f"Status: {todo.status.value}"
            )

        except IntegrityError as e:
            # Rollback on integrity error (unique constraint, foreign key, etc.)
            session.rollback()
            raise ValueError(f"Database integrity error: {str(e.orig)}")
        except Exception as e:
            # Rollback on any other error
            session.rollback()
            raise Exception(f"Database error while creating todo: {str(e)}")

    else:
        # Production mode: use session-per-tool pattern with context manager
        with Session(engine) as session:
            try:
                # Create new Todo instance with validated data
                # Title is already stripped by CreateTodoInput validator
                todo = Todo(
                    title=validated_input.title,
                    description=validated_input.description,
                    status=TodoStatus.ACTIVE,  # New todos are always active
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )

                # Add to session and commit to database
                session.add(todo)
                session.commit()
                session.refresh(todo)  # Refresh to get auto-generated ID

                # Return MCP-compliant response (FastMCP converts string to Content object)
                return (
                    f"Todo created successfully! "
                    f"ID: {todo.id}, "
                    f"Title: '{todo.title}', "
                    f"Status: {todo.status.value}"
                )

            except IntegrityError as e:
                # Rollback on integrity error (unique constraint, foreign key, etc.)
                session.rollback()
                raise ValueError(f"Database integrity error: {str(e.orig)}")
            except Exception as e:
                # Rollback on any other error
                session.rollback()
                raise Exception(f"Database error while creating todo: {str(e)}")


# Create MCP tool wrapper that excludes test parameter
@mcp.tool
def create_todo_mcp(title: str, description: Optional[str] = None) -> str:
    """Creates a new todo item in the database.

    Args:
        title: Todo title (required, max 200 chars)
        description: Optional todo description (max 2000 chars)

    Returns:
        str: Success message with created todo details
    """
    return create_todo(title=title, description=description, _test_session=None)
