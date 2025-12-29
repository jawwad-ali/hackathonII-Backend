# Data Model: AI Agent Orchestrator

**Feature**: 001-ai-agent-orchestrator
**Date**: 2025-12-21
**Phase**: 1 (Design & Contracts)

## Overview

The AI Agent Orchestrator is **stateless** - it does not persist any data locally. All entities below represent **data contracts** for communication with external systems (MCP server, ChatKit frontend, Gemini API).

## Entities

### 1. ChatRequest (Inbound from Frontend)

**Purpose**: Represents user input from ChatKit frontend

**Fields**:
| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `input` | `str` | Yes | `min_length=1, max_length=5000` | Natural language user request |
| `conversation_id` | `str \| None` | No | UUID format (if provided) | Optional conversation tracking ID |
| `user_id` | `str \| None` | No | - | Optional user identifier (for multi-user future) |

**Pydantic Model**:
```python
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    input: str = Field(..., min_length=1, max_length=5000, description="User's natural language input")
    conversation_id: str | None = Field(None, description="Optional conversation ID for context")
    user_id: str | None = Field(None, description="Optional user ID")
```

**Example**:
```json
{
  "input": "Remind me to buy eggs tomorrow at 3pm",
  "conversation_id": "conv_123abc",
  "user_id": "user_456def"
}
```

---

### 2. StreamEvent (Outbound to Frontend)

**Purpose**: Server-Sent Event format for streaming agent responses to ChatKit

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event` | `str` | Yes | Event type: "thinking", "tool_call", "response_delta", "error", "done" |
| `data` | `str \| dict` | Yes | Event payload (JSON string or dict) |

**Event Types**:

#### a. **thinking** - Agent reasoning step
```json
{
  "event": "thinking",
  "data": {
    "content": "The user wants to create a todo for buying eggs tomorrow at 3pm. I need to extract: title='buy eggs', due_date='2025-12-22T15:00:00', priority='medium'"
  }
}
```

#### b. **tool_call** - Agent executing MCP tool
```json
{
  "event": "tool_call",
  "data": {
    "tool_name": "create_todo",
    "arguments": {
      "title": "buy eggs",
      "due_date": "2025-12-22T15:00:00",
      "priority": "medium"
    },
    "status": "in_progress"
  }
}
```

#### c. **response_delta** - Streaming text response
```json
{
  "event": "response_delta",
  "data": {
    "delta": "I've created a todo to ",
    "accumulated": "I've created a todo to "
  }
}
```

#### d. **error** - Error occurred
```json
{
  "event": "error",
  "data": {
    "error_type": "tool_execution_failed",
    "message": "Failed to connect to MCP server",
    "recoverable": false
  }
}
```

#### e. **done** - Stream complete
```json
{
  "event": "done",
  "data": {
    "final_output": "I've created a todo to buy eggs tomorrow at 3pm with medium priority.",
    "tools_called": ["create_todo"],
    "success": true
  }
}
```

**SSE Format**:
```
event: thinking
data: {"content": "Analyzing user request..."}

event: tool_call
data: {"tool_name": "create_todo", "arguments": {...}, "status": "in_progress"}

event: response_delta
data: {"delta": "I've created", "accumulated": "I've created"}

event: done
data: {"final_output": "...", "success": true}

```

---

### 3. MCPToolCall (Internal - Agent to MCP Server)

**Purpose**: Represents a tool invocation to the external MCP server

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tool_name` | `str` | Yes | MCP tool identifier (e.g., "create_todo", "list_todos") |
| `arguments` | `dict` | Yes | Tool-specific parameters |

**Available MCP Tools** (defined by external FastMCP server):

#### a. **create_todo**
```python
{
  "tool_name": "create_todo",
  "arguments": {
    "title": str,           # Required
    "description": str,     # Optional
    "due_date": str,        # Optional, ISO 8601 format
    "priority": str,        # Optional: "low" | "medium" | "high"
    "tags": list[str]       # Optional
  }
}
```

#### b. **list_todos**
```python
{
  "tool_name": "list_todos",
  "arguments": {
    "status": str,          # Optional: "pending" | "completed" | "all"
    "priority": str,        # Optional: "low" | "medium" | "high"
    "due_date_filter": str, # Optional: "today" | "this_week" | ISO date
    "tags": list[str]       # Optional: filter by tags
  }
}
```

#### c. **update_todo**
```python
{
  "tool_name": "update_todo",
  "arguments": {
    "todo_id": str,         # Required
    "title": str,           # Optional
    "description": str,     # Optional
    "due_date": str,        # Optional
    "priority": str,        # Optional
    "status": str,          # Optional: "pending" | "completed"
    "tags": list[str]       # Optional
  }
}
```

#### d. **delete_todo**
```python
{
  "tool_name": "delete_todo",
  "arguments": {
    "todo_id": str,         # Required
    "confirmation": bool    # Required for safety (must be true)
  }
}
```

**Note**: These tool schemas are defined in the external MCP server. The orchestrator discovers them dynamically via agents_mcp integration.

---

### 4. AgentContext (Internal - Runner Context)

**Purpose**: Execution context for OpenAI Agents SDK Runner

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `mcp_config` | `MCPSettings` | MCP server configuration |
| `conversation_history` | `list[dict]` | Optional conversation history (for future multi-turn support) |

**Example**:
```python
from agents_mcp import RunnerContext
from mcp_agent.config import MCPSettings, MCPServerSettings

context = RunnerContext(
    mcp_config=MCPSettings(
        servers={
            "todo_server": MCPServerSettings(
                command="uvx",
                args=["fastmcp", "run", "path/to/todo_server.py"]
            )
        }
    )
)
```

---

### 5. TodoAttributes (Extracted from Natural Language)

**Purpose**: Structured data extracted from user's natural language input by the agent

**Fields**:
| Field | Type | Extraction Pattern Examples |
|-------|------|----------------------------|
| `title` | `str` | "buy eggs", "finish project proposal", "call mom" |
| `description` | `str \| None` | Inferred from context or explicit ("remind me to X because Y") |
| `due_date` | `str \| None` | "tomorrow" → 2025-12-22, "Friday" → next Friday, "3pm" → 15:00:00 |
| `priority` | `str \| None` | "urgent" → "high", "important" → "high", default → "medium" |
| `status` | `str` | "pending" (default for create), "completed" (for updates) |
| `tags` | `list[str] \| None` | Extracted keywords or explicit ("#work", "personal") |

**Extraction Responsibility**: OpenAI Agents SDK (via Gemini model) handles extraction during tool call generation.

---

## Data Flow

```
┌─────────────┐
│ ChatKit     │
│ Frontend    │
└──────┬──────┘
       │ ChatRequest (JSON)
       ▼
┌─────────────────────────────┐
│ FastAPI                     │
│ POST /chat/stream           │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│ OpenAI Agents SDK           │
│ (Gemini 2.5 Flash)          │
│ - Extract intent            │
│ - Generate MCP tool calls   │
│ - Stream reasoning          │
└──────┬──────────────────────┘
       │ MCPToolCall
       ▼
┌─────────────────────────────┐
│ agents_mcp Integration      │
│ - Discover MCP tools        │
│ - Execute tool calls        │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│ External FastMCP Server     │
│ (PostgreSQL + SQLModel)     │
│ - CRUD operations           │
│ - Data persistence          │
└──────┬──────────────────────┘
       │ Tool results
       ▼
┌─────────────────────────────┐
│ FastAPI Streaming           │
│ - Map events to SSE format  │
│ - Stream to ChatKit         │
└──────┬──────────────────────┘
       │ StreamEvent (SSE)
       ▼
┌─────────────┐
│ ChatKit     │
│ Frontend    │
│ - Display   │
└─────────────┘
```

---

## Validation Rules

### Input Validation (FastAPI layer)
- `input`: Non-empty string, max 5000 characters
- `conversation_id`: UUID format if provided
- `user_id`: Any string format (future-proofing)

### MCP Tool Call Validation (Agents SDK layer)
- Tool name must exist in discovered MCP tools
- Arguments must match tool schema (enforced by MCP server)
- Required fields must be present

### Error Handling
- **Invalid input**: Return 422 Unprocessable Entity
- **MCP tool execution failure**: Stream error event, graceful degradation
- **Gemini API failure**: Stream error event with retry suggestion
- **Timeout**: Stream timeout error after 30 seconds (configurable)

---

## State Management

**Critical Constraint**: This orchestrator is **stateless**.

- **No local database**: All todo data lives in external MCP server
- **No session storage**: Conversation context is optional and ephemeral
- **No caching**: Each request is independent (future: add Redis for performance)

**Rationale**: Enforces separation of concerns (orchestration vs. persistence) and enables horizontal scaling.

---

## NEW: Input Validation Schema (from Clarifications)

### Purpose
Enforce FR-013: Request size limits and basic sanitization

### Validation Rules

**Control Character Stripping**:
```python
import re

def strip_control_characters(text: str) -> str:
    """Remove control characters except newline, tab, carriage return"""
    # Keep \n, \t, \r; remove all other control chars
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
```

**UTF-8 Validation**:
```python
from pydantic import field_validator

class ChatRequest(BaseModel):
    input: str = Field(..., min_length=1, max_length=5000)

    @field_validator('input')
    @classmethod
    def validate_utf8_and_sanitize(cls, v: str) -> str:
        # Pydantic ensures UTF-8 by default (raises UnicodeDecodeError if invalid)
        # Additional sanitization: strip control characters
        return strip_control_characters(v)
```

**Validation Flow**:
1. FastAPI receives request body
2. Pydantic validates UTF-8 encoding (automatic)
3. Custom validator strips control characters
4. Length check (1-5000 chars) enforced by Field constraints
5. If any validation fails → 422 Unprocessable Entity with detailed error

---

## NEW: Logging Event Schema (from Clarifications)

### Purpose
Implement FR-011: Structured JSON logging with request IDs

### Log Entry Structure

```python
{
  "timestamp": "2025-12-21T12:00:00.123Z",  # ISO 8601 UTC
  "level": "INFO",                          # DEBUG | INFO | WARNING | ERROR
  "request_id": "req_abc123xyz",            # Generated per request
  "event": "mcp_tool_called",               # Event type
  "duration_ms": 150,                       # Optional: timing metric
  "details": {                              # Event-specific structured data
    "tool_name": "create_todo",
    "arguments": {"title": "buy eggs"},
    "success": true
  },
  "user_id": "user_456def",                 # Optional: if available
  "conversation_id": "conv_123abc"          # Optional: if provided
}
```

### Log Event Types

| Event Type | When Logged | Details Schema |
|------------|-------------|----------------|
| `request_received` | API request arrives | `{method, path, input_length}` |
| `agent_reasoning` | Agent processes intent | `{reasoning_step, confidence}` |
| `mcp_tool_called` | MCP tool invoked | `{tool_name, arguments, duration_ms}` |
| `mcp_tool_result` | MCP tool completes | `{tool_name, success, result_preview}` |
| `gemini_api_called` | Gemini API invoked | `{model, prompt_length, duration_ms}` |
| `gemini_api_result` | Gemini responds | `{model, response_length, tokens_used}` |
| `circuit_breaker_opened` | Circuit breaker triggers | `{service, failure_count, threshold}` |
| `request_completed` | Response streamed | `{total_duration_ms, success, tools_called}` |
| `error_occurred` | Any error happens | `{error_type, error_message, recoverable}` |

### Request ID Generation

```python
import uuid

def generate_request_id() -> str:
    """Generate unique request ID for correlation"""
    return f"req_{uuid.uuid4().hex[:12]}"
```

**Request ID Propagation**:
- Generated in FastAPI middleware
- Added to logging context for all log entries
- Included in SSE stream events (for client-side debugging)
- Returned in response headers: `X-Request-ID`

---

## NEW: Circuit Breaker State (from Clarifications)

### Purpose
Implement FR-012: Circuit breaker pattern for external dependencies

### State Machine

```
┌─────────┐
│ CLOSED  │◄──────┐
│ (normal)│       │ Success after timeout
└────┬────┘       │ (half-open → closed)
     │            │
     │ Failure    │
     │ threshold  │
     ▼            │
┌─────────┐       │
│  OPEN   │───────┤
│ (fail   │       │ Timeout elapsed
│  fast)  │       │ (open → half-open)
└─────────┘       │
                  │
              ┌───┴────┐
              │ HALF-  │
              │ OPEN   │
              │ (test) │
              └────────┘
```

### Circuit Breaker Configuration

```python
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5       # Open after 5 consecutive failures
    recovery_timeout: timedelta = timedelta(seconds=30)  # Test after 30s
    half_open_max_calls: int = 3     # Test with 3 calls in half-open

@dataclass
class CircuitBreakerState:
    state: str  # "closed" | "open" | "half_open"
    failure_count: int
    last_failure_time: datetime | None
    last_state_change: datetime
    consecutive_successes: int  # For half-open state
```

### Per-Service Circuit Breakers

- **MCP Server Circuit Breaker**: Protects against MCP server failures
  - Threshold: 5 consecutive failures
  - Timeout: 30 seconds
  - Fallback: Stream error event "MCP service temporarily unavailable"

- **Gemini API Circuit Breaker**: Protects against Gemini API failures
  - Threshold: 3 consecutive failures (lower due to API rate limits)
  - Timeout: 60 seconds (longer due to external API)
  - Fallback: Stream error event "AI service temporarily unavailable"

### Circuit Breaker Metrics (Logged)

```python
{
  "event": "circuit_breaker_state_change",
  "service": "mcp_server",
  "old_state": "closed",
  "new_state": "open",
  "failure_count": 5,
  "last_error": "ConnectionTimeout"
}
```

---

## Future Enhancements (Out of Scope for MVP)

1. **Conversation Memory**: Store conversation history in Redis for multi-turn context
2. **User Authentication**: Add JWT token validation and user_id enforcement
3. **Rate Limiting**: Add per-user rate limits via Redis (mentioned in clarifications for future)
4. **Multi-Tenancy**: Support multiple users with isolated todo lists
5. **Tool Result Caching**: Cache recent list_todos results to reduce MCP calls
6. **Advanced Metrics**: Prometheus metrics export for circuit breaker state, request latency histograms
