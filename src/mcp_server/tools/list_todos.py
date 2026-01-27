"""List todos tool implementation for FastMCP database server.

This module implements the list_todos MCP tool that retrieves todo items
from the PostgreSQL database using SQLModel with optional filtering.

The tool supports filtering by status, priority, and pagination.
"""

import json
import re
from typing import Any, Dict, List, Optional, Union

from sqlmodel import Session, select

from src.mcp_server.database import engine
from src.mcp_server.models import Todo, TodoStatus, TodoPriority
from src.mcp_server.server import mcp


def _normalize_status(status: Optional[str]) -> Optional[str]:
    if status is None:
        return None
    normalized = status.strip().lower()
    if normalized in ("all", "any"):
        return "all"
    if (
        "active" in normalized
        or "pending" in normalized
        or "open" in normalized
        or "in progress" in normalized
    ):
        return "active"
    if "complete" in normalized or "done" in normalized or "finish" in normalized:
        return "completed"
    if "archiv" in normalized or "cancel" in normalized:
        return "archived"
    return None


def _normalize_priority_token(token: str) -> Optional[str]:
    normalized = token.strip().lower()
    if normalized in ("high", "urgent", "important"):
        return "high"
    if normalized in ("medium", "normal", "default"):
        return "medium"
    if normalized in ("low", "later", "someday"):
        return "low"
    return None


def _normalize_priority_list(priority: Optional[Union[str, List[str]]]) -> Optional[List[str]]:
    if priority is None:
        return None

    tokens: List[str]
    if isinstance(priority, list):
        tokens = [item.strip() for item in priority if isinstance(item, str)]
    else:
        cleaned = priority.lower()
        cleaned = cleaned.replace("priorities", "").replace("priority", "")
        cleaned = cleaned.replace("tasks", "").replace("task", "")
        cleaned = cleaned.replace("todos", "").replace("todo", "")
        tokens = re.split(r"\s*(?:,|/|\bor\b|\band\b)\s*", cleaned)

    normalized_values: List[str] = []
    for token in tokens:
        if not token:
            continue
        mapped = _normalize_priority_token(token)
        if mapped is None:
            return None
        if mapped not in normalized_values:
            normalized_values.append(mapped)

    return normalized_values if normalized_values else None


def _serialize_todo(todo: Todo) -> Dict[str, Any]:
    return {
        "id": todo.id,
        "title": todo.title,
        "description": todo.description,
        "due_date": todo.due_date.isoformat() if todo.due_date else None,
        "priority": todo.priority.value,
        "tags": todo.tags,
        "status": todo.status.value,
        "created_at": todo.created_at.isoformat(),
        "updated_at": todo.updated_at.isoformat(),
    }


def _list_todos_impl(
    status: Optional[str] = None,
    priority: Optional[Union[str, List[str]]] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    _test_session: Optional[Session] = None
) -> str:
    """Internal implementation of list_todos with test session support.

    Queries the database for todos with optional filters. By default (no filters),
    returns only active todos for backward compatibility.

    Args:
        status: Filter by status - "active", "completed", "archived", or "all" (optional)
        priority: Filter by priority - "low", "medium", or "high" (optional, supports multiple)
        limit: Maximum number of results to return (optional)
        offset: Number of results to skip for pagination (optional)
        _test_session: Internal parameter for dependency injection during testing

    Returns:
        dict: Structured list of filtered todos, or error message

    Examples:
        >>> list_todos()
        "Found 2 active todos:
        [1] Buy groceries (medium priority, active) - Created: 2025-12-29"

        >>> list_todos(priority="high")
        "Found 1 active todo with priority=high:
        [5] Finish report (high priority, active) - Created: 2025-12-29"

        >>> list_todos(status="completed")
        "Found 3 completed todos:
        [2] Call dentist (medium priority, completed) - Created: 2025-12-28"

        >>> list_todos(status="active", priority="high")
        "Found 0 active todos with priority=high. The list is empty."
    """
    # Build query with validation
    def build_query():
        """Build dynamic SQL query with filters and validation."""
        statement = select(Todo)
        filters_applied = []

        # Status filter (default: active for backward compatibility)
        if status is None:
            statement = statement.where(Todo.status == TodoStatus.ACTIVE)
            filters_applied.append("status=active")
        else:
            normalized_status = _normalize_status(status)
            if normalized_status is None:
                return None, (
                    f"Error: Invalid status '{status}'. "
                    "Valid values: active, completed, archived, all"
                )
            if normalized_status == "all":
                filters_applied.append("status=all")
            else:
                status_enum = TodoStatus[normalized_status.upper()]
                statement = statement.where(Todo.status == status_enum)
                filters_applied.append(f"status={normalized_status}")

        # Priority filter (optional, AND logic)
        if priority:
            normalized_priorities = _normalize_priority_list(priority)
            if normalized_priorities is None:
                return None, (
                    f"Error: Invalid priority '{priority}'. "
                    "Valid values: low, medium, high"
                )
            priority_enums = [TodoPriority[value.upper()] for value in normalized_priorities]
            if len(priority_enums) == 1:
                statement = statement.where(Todo.priority == priority_enums[0])
                filters_applied.append(f"priority={normalized_priorities[0]}")
            else:
                statement = statement.where(Todo.priority.in_(priority_enums))
                filters_applied.append(
                    f"priority in ({', '.join(normalized_priorities)})"
                )

        # Pagination
        if limit is not None:
            statement = statement.limit(limit)
        if offset is not None:
            statement = statement.offset(offset)

        return statement, filters_applied

    # Use provided test session or create new session from engine
    if _test_session is not None:
        # Test mode: use provided session directly (no context manager)
        session = _test_session
        try:
            # Build query with filters
            statement, result_or_error = build_query()
            if statement is None:
                return result_or_error  # Return error message

            # Execute query
            result = session.exec(statement)
            todos = result.all()

            serialized = [_serialize_todo(todo) for todo in todos]
            total = len(serialized)
            # Return JSON string (MCP tools should return strings for compatibility)
            return json.dumps({
                "todos": serialized,
                "total": total,
                "limit": limit if limit is not None else total,
                "offset": offset or 0,
            }, default=str)

        except Exception as e:
            raise Exception(f"Database error while listing todos: {str(e)}")

    else:
        # Production mode: use session-per-tool pattern with context manager
        with Session(engine) as session:
            try:
                # Build query with filters
                statement, result_or_error = build_query()
                if statement is None:
                    return result_or_error  # Return error message

                # Execute query
                result = session.exec(statement)
                todos = result.all()

                serialized = [_serialize_todo(todo) for todo in todos]
                total = len(serialized)
                # Return JSON string (MCP tools should return strings for compatibility)
                return json.dumps({
                    "todos": serialized,
                    "total": total,
                    "limit": limit if limit is not None else total,
                    "offset": offset or 0,
                }, default=str)

            except Exception as e:
                raise Exception(f"Database error while listing todos: {str(e)}")


# MCP tool wrapper that calls internal implementation
@mcp.tool
def list_todos(
    status: Optional[str] = None,
    priority: Optional[Union[str, List[str]]] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> str:
    """Retrieves todos from the database with optional filters.

    By default (no filters), returns only active todos for backward compatibility.
    Supports filtering by status, priority, and pagination.

    Args:
        status: Filter by status - "active", "completed", "archived", or "all" (optional)
        priority: Filter by priority - "low", "medium", or "high" (optional, supports multiple)
        limit: Maximum number of results to return (optional)
        offset: Number of results to skip for pagination (optional)

    Returns:
        dict: Structured list of filtered todos, or error message

    Examples:
        list_todos() - Returns all active todos
        list_todos(priority="high") - Returns high priority active todos
        list_todos(status="completed") - Returns completed todos
        list_todos(status="active", priority="high") - Returns active high priority todos
    """
    return _list_todos_impl(
        status=status,
        priority=priority,
        limit=limit,
        offset=offset,
        _test_session=None
    )
