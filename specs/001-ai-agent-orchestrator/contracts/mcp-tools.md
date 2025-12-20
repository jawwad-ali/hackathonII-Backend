# MCP Tool Contracts

**Feature**: 001-ai-agent-orchestrator
**External Dependency**: FastMCP Server (separate service)

This document defines the expected tool interfaces that the orchestrator discovers from the external MCP server. These tools are **not implemented in this repository** - they are provided by the FastMCP server running PostgreSQL + SQLModel.

## Tool Discovery

The orchestrator uses `agents_mcp` to automatically discover available tools from the configured MCP server at runtime.

**Configuration** (mcp_agent.config.yaml):
```yaml
mcp:
  servers:
    todo_server:
      command: "uvx"
      args: ["fastmcp", "run", "path/to/todo_server.py"]
```

## Expected MCP Tools

### 1. create_todo

**Purpose**: Create a new todo item

**Tool Schema**:
```json
{
  "name": "create_todo",
  "description": "Create a new todo item with optional due date, priority, and tags",
  "parameters": {
    "type": "object",
    "properties": {
      "title": {
        "type": "string",
        "description": "The todo item title",
        "minLength": 1,
        "maxLength": 200
      },
      "description": {
        "type": "string",
        "description": "Optional detailed description",
        "maxLength": 1000
      },
      "due_date": {
        "type": "string",
        "format": "date-time",
        "description": "Optional due date in ISO 8601 format"
      },
      "priority": {
        "type": "string",
        "enum": ["low", "medium", "high"],
        "description": "Priority level",
        "default": "medium"
      },
      "tags": {
        "type": "array",
        "items": {
          "type": "string"
        },
        "description": "Optional list of tags"
      }
    },
    "required": ["title"]
  }
}
```

**Example Agent Usage**:
```python
# Agent automatically calls this when user says:
# "Remind me to buy eggs tomorrow at 3pm"

tool_call = {
    "tool_name": "create_todo",
    "arguments": {
        "title": "buy eggs",
        "due_date": "2025-12-22T15:00:00",
        "priority": "medium"
    }
}
```

**Expected Response**:
```json
{
  "success": true,
  "todo_id": "todo_789xyz",
  "message": "Todo created successfully"
}
```

---

### 2. list_todos

**Purpose**: Retrieve todo items with optional filters

**Tool Schema**:
```json
{
  "name": "list_todos",
  "description": "List todo items with optional filtering by status, priority, due date, or tags",
  "parameters": {
    "type": "object",
    "properties": {
      "status": {
        "type": "string",
        "enum": ["pending", "completed", "all"],
        "description": "Filter by completion status",
        "default": "pending"
      },
      "priority": {
        "type": "string",
        "enum": ["low", "medium", "high"],
        "description": "Filter by priority level"
      },
      "due_date_filter": {
        "type": "string",
        "description": "Filter by due date: 'today', 'this_week', or specific ISO date",
        "examples": ["today", "this_week", "2025-12-25"]
      },
      "tags": {
        "type": "array",
        "items": {
          "type": "string"
        },
        "description": "Filter by tags (AND logic)"
      },
      "limit": {
        "type": "integer",
        "description": "Maximum number of results",
        "default": 50,
        "maximum": 100
      }
    },
    "required": []
  }
}
```

**Example Agent Usage**:
```python
# Agent automatically calls this when user says:
# "What's on my todo list for today?"

tool_call = {
    "tool_name": "list_todos",
    "arguments": {
        "status": "pending",
        "due_date_filter": "today"
    }
}
```

**Expected Response**:
```json
{
  "success": true,
  "todos": [
    {
      "todo_id": "todo_789xyz",
      "title": "buy eggs",
      "description": null,
      "due_date": "2025-12-22T15:00:00",
      "priority": "medium",
      "status": "pending",
      "tags": [],
      "created_at": "2025-12-21T10:30:00",
      "updated_at": "2025-12-21T10:30:00"
    }
  ],
  "count": 1
}
```

---

### 3. update_todo

**Purpose**: Update an existing todo item

**Tool Schema**:
```json
{
  "name": "update_todo",
  "description": "Update one or more fields of an existing todo item",
  "parameters": {
    "type": "object",
    "properties": {
      "todo_id": {
        "type": "string",
        "description": "The unique todo identifier"
      },
      "title": {
        "type": "string",
        "description": "Updated title",
        "minLength": 1,
        "maxLength": 200
      },
      "description": {
        "type": "string",
        "description": "Updated description",
        "maxLength": 1000
      },
      "due_date": {
        "type": "string",
        "format": "date-time",
        "description": "Updated due date in ISO 8601 format"
      },
      "priority": {
        "type": "string",
        "enum": ["low", "medium", "high"],
        "description": "Updated priority level"
      },
      "status": {
        "type": "string",
        "enum": ["pending", "completed"],
        "description": "Updated completion status"
      },
      "tags": {
        "type": "array",
        "items": {
          "type": "string"
        },
        "description": "Updated tags (replaces existing)"
      }
    },
    "required": ["todo_id"]
  }
}
```

**Example Agent Usage**:
```python
# Agent automatically calls this when user says:
# "Mark the buy eggs task as complete"

tool_call = {
    "tool_name": "update_todo",
    "arguments": {
        "todo_id": "todo_789xyz",
        "status": "completed"
    }
}
```

**Expected Response**:
```json
{
  "success": true,
  "todo_id": "todo_789xyz",
  "message": "Todo updated successfully",
  "updated_fields": ["status"]
}
```

---

### 4. delete_todo

**Purpose**: Delete a todo item (with safety confirmation)

**Tool Schema**:
```json
{
  "name": "delete_todo",
  "description": "Delete a todo item permanently. Requires explicit confirmation for safety.",
  "parameters": {
    "type": "object",
    "properties": {
      "todo_id": {
        "type": "string",
        "description": "The unique todo identifier to delete"
      },
      "confirmation": {
        "type": "boolean",
        "description": "Must be true to confirm deletion (safety check)",
        "const": true
      }
    },
    "required": ["todo_id", "confirmation"]
  }
}
```

**Example Agent Usage**:
```python
# Agent automatically calls this when user says:
# "Delete the buy eggs task"

tool_call = {
    "tool_name": "delete_todo",
    "arguments": {
        "todo_id": "todo_789xyz",
        "confirmation": true
    }
}
```

**Expected Response**:
```json
{
  "success": true,
  "todo_id": "todo_789xyz",
  "message": "Todo deleted successfully"
}
```

---

## Error Responses

All MCP tools should return consistent error responses:

```json
{
  "success": false,
  "error_type": "todo_not_found",
  "message": "Todo with ID 'todo_invalid' does not exist",
  "recoverable": false
}
```

**Error Types**:
- `todo_not_found`: Requested todo doesn't exist
- `invalid_arguments`: Tool arguments failed validation
- `database_error`: PostgreSQL connection or query failure
- `permission_denied`: User doesn't have access to this todo (future)

---

## Tool Discovery Validation

On startup, the orchestrator should validate that all expected tools are available:

```python
from agents_mcp import Agent, RunnerContext

# During initialization
context = RunnerContext(mcp_config_path="mcp_agent.config.yaml")

# Verify tools are discovered (optional health check)
expected_tools = ["create_todo", "list_todos", "update_todo", "delete_todo"]
# agents_mcp automatically discovers and registers tools
```

If any expected tool is missing, log a warning but continue (graceful degradation).

---

## Implementation Notes

1. **Tool schemas are defined by MCP server**, not this orchestrator
2. **Orchestrator only consumes tools** via agents_mcp integration
3. **Agent (Gemini) decides** which tool to call based on user intent
4. **No hardcoded tool logic** in orchestrator - fully dynamic discovery
5. **Error handling** should gracefully handle missing or failed tools
