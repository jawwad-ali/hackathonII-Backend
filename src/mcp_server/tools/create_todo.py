"""Create todo tool implementation for FastMCP database server.

This module implements the create_todo MCP tool that creates new todo items
in the PostgreSQL database using SQLModel and psycopg2.

The tool validates inputs using Pydantic schemas and returns MCP-compliant
responses to the AI agent.
"""

from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from src.mcp_server.database import engine
from src.mcp_server.models import Todo, TodoStatus, TodoPriority
from src.mcp_server.schemas import CreateTodoInput
from src.mcp_server.server import mcp


def _create_todo_impl(
    title: str,
    description: Optional[str] = None,
    due_date: Optional[datetime] = None,
    priority: TodoPriority = TodoPriority.MEDIUM,
    tags: Optional[List[str]] = None,
    _test_session: Optional[Session] = None
) -> str:
    """Internal implementation of create_todo with test session support.

    This tool creates a new todo with the provided details.
    The todo is automatically assigned an active status and timestamps are
    auto-generated.

    Args:
        title: Todo title (required, max 200 chars, whitespace will be stripped)
        description: Optional todo description (max 2000 chars)
        due_date: Optional due date/time (ISO 8601 datetime, UTC)
        priority: Priority level (low/medium/high, default: medium)
        tags: Optional list of category tags
        _test_session: Internal parameter for dependency injection during testing

    Returns:
        str: Human-readable success message with the created todo details

    Raises:
        ValueError: If title is empty/whitespace-only or exceeds max length
        ValueError: If description exceeds max length
        ValueError: If tags contain invalid values
        Exception: If database operation fails

    Examples:
        >>> create_todo("Buy groceries")
        "Todo created successfully! ID: 1, Title: 'Buy groceries', Status: active, Priority: medium"

        >>> create_todo("Call dentist", "Schedule annual checkup", priority="high")
        "Todo created successfully! ID: 2, Title: 'Call dentist', Status: active, Priority: high"
    """
    # Validate input using Pydantic schema
    # This will raise ValueError if validation fails
    try:
        validated_input = CreateTodoInput(
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            tags=tags
        )
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
                due_date=validated_input.due_date,
                priority=validated_input.priority,
                tags=validated_input.tags,
                status=TodoStatus.ACTIVE,  # New todos are always active
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            # Add to session and commit to database
            session.add(todo)
            session.commit()
            session.refresh(todo)  # Refresh to get auto-generated ID

            # Build success message with all relevant details
            response_parts = [
                f"Todo created successfully!",
                f"ID: {todo.id}",
                f"Title: '{todo.title}'",
                f"Status: {todo.status.value}",
                f"Priority: {todo.priority.value}"
            ]

            if todo.due_date:
                response_parts.append(f"Due: {todo.due_date.isoformat()}")

            if todo.tags:
                tags_str = ", ".join(todo.tags)
                response_parts.append(f"Tags: {tags_str}")

            return ", ".join(response_parts)

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
                    due_date=validated_input.due_date,
                    priority=validated_input.priority,
                    tags=validated_input.tags,
                    status=TodoStatus.ACTIVE,  # New todos are always active
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )

                # Add to session and commit to database
                session.add(todo)
                session.commit()
                session.refresh(todo)  # Refresh to get auto-generated ID

                # Build success message with all relevant details
                response_parts = [
                    f"Todo created successfully!",
                    f"ID: {todo.id}",
                    f"Title: '{todo.title}'",
                    f"Status: {todo.status.value}",
                    f"Priority: {todo.priority.value}"
                ]

                if todo.due_date:
                    response_parts.append(f"Due: {todo.due_date.isoformat()}")

                if todo.tags:
                    tags_str = ", ".join(todo.tags)
                    response_parts.append(f"Tags: {tags_str}")

                return ", ".join(response_parts)

            except IntegrityError as e:
                # Rollback on integrity error (unique constraint, foreign key, etc.)
                session.rollback()
                raise ValueError(f"Database integrity error: {str(e.orig)}")
            except Exception as e:
                # Rollback on any other error
                session.rollback()
                raise Exception(f"Database error while creating todo: {str(e)}")


# MCP tool wrapper that calls internal implementation without test parameter
@mcp.tool
def create_todo(
    title: str,
    description: Optional[str] = None,
    due_date: Optional[datetime] = None,
    priority: str = "medium",
    tags: Optional[List[str]] = None
) -> str:
    """Creates a new todo item in the database.

    Args:
        title: Todo title (required, max 200 chars)
        description: Optional todo description (max 2000 chars)
        due_date: Optional due date/time (ISO 8601 datetime string, UTC)
        priority: Priority level - "low", "medium" (default), or "high"
        tags: Optional list of category tags (e.g., ["work", "urgent"])

    Returns:
        str: Success message with created todo details including ID, title, status, priority, due date, and tags
    """
    # Convert string priority to enum
    priority_enum = TodoPriority(priority.lower())

    return _create_todo_impl(
        title=title,
        description=description,
        due_date=due_date,
        priority=priority_enum,
        tags=tags,
        _test_session=None
    )
