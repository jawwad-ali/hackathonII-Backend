"""
MCP Tool Definitions for Todo Management

This module documents the expected MCP tool schemas provided by the todo_server.
These tools are automatically discovered and registered with the TodoAgent via
the OpenAI Agents SDK when the agent is initialized with mcp_servers=["todo_server"].

The actual tool implementations reside in the external FastMCP server
(todo_server.py), which handles PostgreSQL + SQLModel CRUD operations.

This file serves as reference documentation for:
- Understanding available MCP tools
- Validating tool schemas during development
- Testing tool invocations
- Onboarding new developers
"""

from typing import TypedDict, Optional, List, Literal


# Type definitions for MCP tool schemas

class CreateTodoInput(TypedDict, total=False):
    """
    Input schema for create_todo MCP tool.

    Creates a new todo item with the specified attributes.

    Required Fields:
        title: The main task description (1-500 characters)

    Optional Fields:
        description: Extended task details (max 2000 characters)
        due_date: ISO 8601 datetime string (e.g., "2025-12-22T15:00:00")
        priority: Task urgency level (low, medium, high)
        tags: Comma-separated list of tags/categories
        status: Initial status (default: "pending")

    Example:
        {
            "title": "Buy eggs",
            "description": "Get a dozen organic eggs from the store",
            "due_date": "2025-12-22T15:00:00",
            "priority": "medium",
            "tags": "shopping,groceries"
        }
    """
    title: str
    description: Optional[str]
    due_date: Optional[str]
    priority: Optional[Literal["low", "medium", "high"]]
    tags: Optional[str]
    status: Optional[Literal["pending", "in_progress", "completed", "cancelled"]]


class CreateTodoOutput(TypedDict):
    """
    Output schema for create_todo MCP tool.

    Returns the created todo item with assigned ID and timestamps.

    Fields:
        id: Auto-generated unique identifier
        title: Task title
        description: Task details (nullable)
        due_date: ISO 8601 datetime (nullable)
        priority: Task priority
        tags: Comma-separated tags (nullable)
        status: Current status
        created_at: Creation timestamp (ISO 8601)
        updated_at: Last update timestamp (ISO 8601)

    Example:
        {
            "id": 123,
            "title": "Buy eggs",
            "description": "Get a dozen organic eggs from the store",
            "due_date": "2025-12-22T15:00:00",
            "priority": "medium",
            "tags": "shopping,groceries",
            "status": "pending",
            "created_at": "2025-12-21T10:30:00",
            "updated_at": "2025-12-21T10:30:00"
        }
    """
    id: int
    title: str
    description: Optional[str]
    due_date: Optional[str]
    priority: str
    tags: Optional[str]
    status: str
    created_at: str
    updated_at: str


class ListTodosInput(TypedDict, total=False):
    """
    Input schema for list_todos MCP tool.

    Retrieves todo items with optional filters.

    Optional Fields:
        status: Filter by status (pending, in_progress, completed, cancelled)
        priority: Filter by priority (low, medium, high)
        due_date_filter: Filter by due date (today, tomorrow, this_week, overdue)
        tags: Filter by tags (comma-separated)
        limit: Maximum number of results (default: 100, max: 500)
        offset: Pagination offset (default: 0)

    Example:
        {
            "status": "pending",
            "priority": "high",
            "due_date_filter": "today",
            "limit": 50
        }
    """
    status: Optional[Literal["pending", "in_progress", "completed", "cancelled"]]
    priority: Optional[Literal["low", "medium", "high"]]
    due_date_filter: Optional[Literal["today", "tomorrow", "this_week", "overdue"]]
    tags: Optional[str]
    limit: Optional[int]
    offset: Optional[int]


class ListTodosOutput(TypedDict):
    """
    Output schema for list_todos MCP tool.

    Returns a list of todo items matching the filter criteria.

    Fields:
        todos: List of todo items (see CreateTodoOutput for item schema)
        total: Total count of matching items (before pagination)
        limit: Applied limit
        offset: Applied offset

    Example:
        {
            "todos": [
                {
                    "id": 123,
                    "title": "Buy eggs",
                    "description": "Get a dozen organic eggs",
                    "due_date": "2025-12-22T15:00:00",
                    "priority": "medium",
                    "tags": "shopping",
                    "status": "pending",
                    "created_at": "2025-12-21T10:30:00",
                    "updated_at": "2025-12-21T10:30:00"
                }
            ],
            "total": 1,
            "limit": 100,
            "offset": 0
        }
    """
    todos: List[CreateTodoOutput]
    total: int
    limit: int
    offset: int


class UpdateTodoInput(TypedDict, total=False):
    """
    Input schema for update_todo MCP tool.

    Updates an existing todo item by ID.

    Required Fields:
        todo_id: Unique identifier of the todo to update

    Optional Fields:
        title: Updated task title
        description: Updated task details
        due_date: Updated due date (ISO 8601)
        priority: Updated priority
        tags: Updated tags (comma-separated)
        status: Updated status

    Example:
        {
            "todo_id": 123,
            "status": "completed"
        }
    """
    todo_id: int
    title: Optional[str]
    description: Optional[str]
    due_date: Optional[str]
    priority: Optional[Literal["low", "medium", "high"]]
    tags: Optional[str]
    status: Optional[Literal["pending", "in_progress", "completed", "cancelled"]]


class UpdateTodoOutput(TypedDict):
    """
    Output schema for update_todo MCP tool.

    Returns the updated todo item with new timestamp.

    Fields: Same as CreateTodoOutput with updated_at reflecting the update time.

    Example:
        {
            "id": 123,
            "title": "Buy eggs",
            "description": "Get a dozen organic eggs from the store",
            "due_date": "2025-12-22T15:00:00",
            "priority": "medium",
            "tags": "shopping,groceries",
            "status": "completed",
            "created_at": "2025-12-21T10:30:00",
            "updated_at": "2025-12-21T16:45:00"
        }
    """
    id: int
    title: str
    description: Optional[str]
    due_date: Optional[str]
    priority: str
    tags: Optional[str]
    status: str
    created_at: str
    updated_at: str


class DeleteTodoInput(TypedDict):
    """
    Input schema for delete_todo MCP tool.

    Deletes a todo item by ID.

    Required Fields:
        todo_id: Unique identifier of the todo to delete

    Example:
        {
            "todo_id": 123
        }
    """
    todo_id: int


class DeleteTodoOutput(TypedDict):
    """
    Output schema for delete_todo MCP tool.

    Returns confirmation of deletion.

    Fields:
        success: Whether the deletion was successful
        message: Human-readable confirmation message
        deleted_id: ID of the deleted todo

    Example:
        {
            "success": true,
            "message": "Todo item 123 deleted successfully",
            "deleted_id": 123
        }
    """
    success: bool
    message: str
    deleted_id: int


# MCP Tool Registry
# This dictionary provides quick reference to all available MCP tools

MCP_TOOLS = {
    "create_todo": {
        "name": "create_todo",
        "description": "Create a new todo item with title, description, due date, priority, and tags",
        "input_schema": CreateTodoInput,
        "output_schema": CreateTodoOutput,
        "examples": [
            {
                "input": {
                    "title": "Buy eggs",
                    "due_date": "2025-12-22T15:00:00",
                    "priority": "medium"
                },
                "description": "Create a simple todo with title and due date"
            },
            {
                "input": {
                    "title": "Finish project report",
                    "description": "Complete the Q4 sales analysis report",
                    "due_date": "2025-12-25T17:00:00",
                    "priority": "high",
                    "tags": "work,urgent"
                },
                "description": "Create a detailed todo with all fields"
            }
        ]
    },
    "list_todos": {
        "name": "list_todos",
        "description": "List todo items with optional filters for status, priority, due date, and tags",
        "input_schema": ListTodosInput,
        "output_schema": ListTodosOutput,
        "examples": [
            {
                "input": {},
                "description": "List all todos (default: pending, limit 100)"
            },
            {
                "input": {
                    "status": "pending",
                    "due_date_filter": "today"
                },
                "description": "List pending todos due today"
            },
            {
                "input": {
                    "priority": "high",
                    "limit": 10
                },
                "description": "List first 10 high-priority todos"
            }
        ]
    },
    "update_todo": {
        "name": "update_todo",
        "description": "Update an existing todo item by ID with new values",
        "input_schema": UpdateTodoInput,
        "output_schema": UpdateTodoOutput,
        "examples": [
            {
                "input": {
                    "todo_id": 123,
                    "status": "completed"
                },
                "description": "Mark a todo as completed"
            },
            {
                "input": {
                    "todo_id": 456,
                    "title": "Buy eggs and milk",
                    "priority": "high"
                },
                "description": "Update title and priority"
            }
        ]
    },
    "delete_todo": {
        "name": "delete_todo",
        "description": "Delete a todo item by ID (permanent, requires confirmation for mass deletions)",
        "input_schema": DeleteTodoInput,
        "output_schema": DeleteTodoOutput,
        "examples": [
            {
                "input": {
                    "todo_id": 123
                },
                "description": "Delete a single todo item"
            }
        ]
    }
}


def get_tool_schema(tool_name: str) -> dict:
    """
    Get the schema definition for a specific MCP tool.

    Args:
        tool_name: Name of the tool (create_todo, list_todos, update_todo, delete_todo)

    Returns:
        dict: Tool schema with name, description, input/output schemas, and examples

    Raises:
        KeyError: If tool_name is not found in MCP_TOOLS

    Example:
        >>> schema = get_tool_schema("create_todo")
        >>> print(schema["description"])
        Create a new todo item with title, description, due date, priority, and tags
    """
    return MCP_TOOLS[tool_name]


def list_available_tools() -> List[str]:
    """
    List all available MCP tool names.

    Returns:
        List[str]: Names of all MCP tools provided by todo_server

    Example:
        >>> tools = list_available_tools()
        >>> print(tools)
        ['create_todo', 'list_todos', 'update_todo', 'delete_todo']
    """
    return list(MCP_TOOLS.keys())


# Expected tool count for validation
EXPECTED_TOOL_COUNT = 4

# Tool categories for documentation
TOOL_CATEGORIES = {
    "CRUD Operations": ["create_todo", "list_todos", "update_todo", "delete_todo"],
    "Create": ["create_todo"],
    "Read": ["list_todos"],
    "Update": ["update_todo"],
    "Delete": ["delete_todo"]
}
