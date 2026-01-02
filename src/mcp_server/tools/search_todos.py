"""Search todos tool implementation for FastMCP database server.

This module implements the search_todos MCP tool that searches for todos by keyword
in title or description fields. Only returns active todos (excludes completed/archived).

The search is case-insensitive and uses ILIKE pattern matching for flexible keyword searches.

SQL Injection Prevention:
- Input validation and sanitization on keyword parameter
- Length limits to prevent resource exhaustion
- Parameterized queries via SQLAlchemy (automatic escaping)
- Wildcard character escaping for ILIKE pattern matching
"""

import re
from typing import Optional

from sqlmodel import Session, select, or_

from src.mcp_server.database import engine
from src.mcp_server.models import Todo, TodoStatus
from src.mcp_server.server import mcp


def _sanitize_search_keyword(keyword: str) -> str:
    """Sanitize and validate search keyword to prevent SQL injection.

    This function provides defense-in-depth protection against SQL injection
    attacks, even though SQLAlchemy's parameterized queries already provide
    automatic escaping.

    Args:
        keyword: Raw search keyword from user input

    Returns:
        str: Sanitized keyword safe for use in SQL queries

    Raises:
        ValueError: If keyword is invalid or contains malicious patterns

    Security measures:
    1. Length validation (max 100 chars) to prevent resource exhaustion
    2. Rejects empty or whitespace-only keywords
    3. Escapes SQL wildcard characters (%, _) to treat them literally
    4. Validates against SQL injection patterns (single quotes, semicolons, etc.)
    5. Removes null bytes and control characters
    """
    # 1. Validate keyword is not None
    if keyword is None:
        raise ValueError("Search keyword cannot be None")

    # 2. Validate keyword is a string
    if not isinstance(keyword, str):
        raise ValueError(f"Search keyword must be a string, got {type(keyword).__name__}")

    # 3. Strip whitespace
    keyword = keyword.strip()

    # 4. Reject empty or whitespace-only keywords
    if not keyword:
        raise ValueError("Search keyword cannot be empty or whitespace-only")

    # 5. Length validation (max 100 chars to prevent resource exhaustion)
    if len(keyword) > 100:
        raise ValueError("Search keyword exceeds maximum length of 100 characters")

    # 6. Remove null bytes and control characters
    # These can be used in injection attacks
    keyword = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', keyword)

    # 7. Detect and reject common SQL injection patterns
    # Note: SQLAlchemy parameterization already prevents injection,
    # but we add this as defense-in-depth
    dangerous_patterns = [
        r"--",           # SQL comments
        r"/\*",          # Multi-line comments
        r"\*/",          # Multi-line comments
        r";",            # Statement terminators
        r"\bOR\b",       # OR keyword (case-insensitive)
        r"\bAND\b",      # AND keyword
        r"\bUNION\b",    # UNION queries
        r"\bSELECT\b",   # SELECT statements
        r"\bDROP\b",     # DROP statements
        r"\bDELETE\b",   # DELETE statements
        r"\bINSERT\b",   # INSERT statements
        r"\bUPDATE\b",   # UPDATE statements
        r"\bEXEC\b",     # EXEC statements
        r"\bEXECUTE\b",  # EXECUTE statements
        r"\\x[0-9a-fA-F]{2}",  # Hex-encoded characters
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, keyword, re.IGNORECASE):
            raise ValueError(
                f"Search keyword contains potentially malicious pattern: {pattern}"
            )

    # 8. Escape SQL wildcard characters (%, _) so they're treated literally
    # In ILIKE/LIKE queries, % matches any sequence, _ matches any single char
    # We escape them so users can search for literal % or _ characters
    keyword = keyword.replace('%', r'\%')
    keyword = keyword.replace('_', r'\_')

    return keyword


def _search_todos_impl(keyword: str, _test_session: Optional[Session] = None) -> str:
    """Internal implementation of search_todos with test session support.

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
    # Sanitize and validate keyword to prevent SQL injection
    # This provides defense-in-depth even though SQLAlchemy uses parameterized queries
    try:
        sanitized_keyword = _sanitize_search_keyword(keyword)
    except ValueError as e:
        raise ValueError(f"Invalid search keyword: {str(e)}")

    # Use provided test session or create new session from engine
    if _test_session is not None:
        # Test mode: use provided session directly (no context manager)
        session = _test_session
        try:
            # Build search query: keyword in title OR description, AND status is active
            # Use ILIKE for case-insensitive pattern matching
            # Note: sanitized_keyword already has SQL wildcards escaped
            search_pattern = f"%{sanitized_keyword}%"
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
                return f"Found 0 todos matching '{sanitized_keyword}'. No results."

            # Format response with all todo details
            count = len(todos)
            response_lines = [f"Found {count} todo{'s' if count != 1 else ''} matching '{sanitized_keyword}':"]

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
                # Note: sanitized_keyword already has SQL wildcards escaped
                search_pattern = f"%{sanitized_keyword}%"
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
                    return f"Found 0 todos matching '{sanitized_keyword}'. No results."

                # Format response with all todo details
                count = len(todos)
                response_lines = [f"Found {count} todo{'s' if count != 1 else ''} matching '{sanitized_keyword}':"]

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
def search_todos(keyword: str) -> str:
    """Searches active todos by keyword in title or description.

    Performs case-insensitive search across title and description fields.
    Returns only todos with status='active', excluding completed and archived items.

    Args:
        keyword: Search keyword (case-insensitive, searches title and description)

    Returns:
        str: Summary and list of matching todos with details
    """
    return _search_todos_impl(keyword=keyword, _test_session=None)
