"""
ChatKit-compatible Server-Sent Events (SSE) formatters.

This module provides formatters for converting agent execution events
into SSE format compatible with the ChatKit protocol as defined in
specs/001-ai-agent-orchestrator/contracts/openapi.yaml.

SSE Format:
    event: <event_type>
    data: <json_payload>

    (blank line separates events)
"""

import json
from typing import Any, Dict, List, Optional
from enum import Enum


class EventType(str, Enum):
    """ChatKit SSE event types."""
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    RESPONSE_DELTA = "response_delta"
    ERROR = "error"
    DONE = "done"


class ToolStatus(str, Enum):
    """Tool execution status."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ErrorType(str, Enum):
    """Error types for error events."""
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    MCP_CONNECTION_ERROR = "mcp_connection_error"
    GEMINI_API_ERROR = "gemini_api_error"
    TIMEOUT = "timeout"
    INVALID_TOOL_ARGUMENTS = "invalid_tool_arguments"


def format_sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """
    Format a single SSE event following ChatKit protocol.

    Args:
        event_type: The event type (thinking, tool_call, response_delta, error, done)
        data: Event payload as a dictionary

    Returns:
        Formatted SSE string with event type and JSON data

    Example:
        >>> format_sse_event("thinking", {"content": "Processing request..."})
        'event: thinking\\ndata: {"content": "Processing request..."}\\n\\n'
    """
    json_data = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {json_data}\n\n"


def thinking_event(content: str) -> str:
    """
    Create a thinking event showing agent reasoning.

    Args:
        content: The agent's reasoning or thought process

    Returns:
        Formatted SSE thinking event

    Example:
        >>> thinking_event("User wants to create a todo for buying eggs")
        'event: thinking\\ndata: {"content": "User wants to create a todo for buying eggs"}\\n\\n'
    """
    data = {"content": content}
    return format_sse_event(EventType.THINKING, data)


def tool_call_event(
    tool_name: str,
    arguments: Dict[str, Any],
    status: ToolStatus = ToolStatus.IN_PROGRESS
) -> str:
    """
    Create a tool call event showing MCP tool invocation.

    Args:
        tool_name: Name of the MCP tool (create_todo, list_todos, update_todo, delete_todo)
        arguments: Tool arguments extracted from user intent
        status: Tool execution status (default: in_progress)

    Returns:
        Formatted SSE tool_call event

    Example:
        >>> tool_call_event("create_todo", {"title": "buy eggs", "due_date": "2025-12-22"})
        'event: tool_call\\ndata: {"tool_name": "create_todo", "arguments": {...}, "status": "in_progress"}\\n\\n'
    """
    data = {
        "tool_name": tool_name,
        "arguments": arguments,
        "status": status.value if isinstance(status, ToolStatus) else status
    }
    return format_sse_event(EventType.TOOL_CALL, data)


def response_delta_event(delta: str, accumulated: str) -> str:
    """
    Create a response delta event for streaming text.

    Args:
        delta: The incremental text chunk
        accumulated: The full accumulated text so far

    Returns:
        Formatted SSE response_delta event

    Example:
        >>> response_delta_event("I've created ", "I've created ")
        'event: response_delta\\ndata: {"delta": "I\'ve created ", "accumulated": "I\'ve created "}\\n\\n'
    """
    data = {
        "delta": delta,
        "accumulated": accumulated
    }
    return format_sse_event(EventType.RESPONSE_DELTA, data)


def error_event(
    error_type: ErrorType,
    message: str,
    recoverable: bool = False
) -> str:
    """
    Create an error event for failures.

    Args:
        error_type: Type of error that occurred
        message: User-friendly error message
        recoverable: Whether the error can be recovered with retry

    Returns:
        Formatted SSE error event

    Example:
        >>> error_event(ErrorType.MCP_CONNECTION_ERROR, "Failed to connect to MCP server", False)
        'event: error\\ndata: {"error_type": "mcp_connection_error", "message": "...", "recoverable": false}\\n\\n'
    """
    data = {
        "error_type": error_type.value if isinstance(error_type, ErrorType) else error_type,
        "message": message,
        "recoverable": recoverable
    }
    return format_sse_event(EventType.ERROR, data)


def done_event(
    final_output: str,
    tools_called: List[str],
    success: bool = True
) -> str:
    """
    Create a done event indicating stream completion.

    Args:
        final_output: The final response message to the user
        tools_called: List of MCP tools that were invoked
        success: Whether the operation completed successfully

    Returns:
        Formatted SSE done event

    Example:
        >>> done_event("I've created a todo to buy eggs.", ["create_todo"], True)
        'event: done\\ndata: {"final_output": "...", "tools_called": ["create_todo"], "success": true}\\n\\n'
    """
    data = {
        "final_output": final_output,
        "tools_called": tools_called,
        "success": success
    }
    return format_sse_event(EventType.DONE, data)


def map_agent_event_to_chatkit(
    event: Any,
    stream_builder: "StreamBuilder"
) -> Optional[str]:
    """
    Map OpenAI Agents SDK stream events to ChatKit SSE format.

    This function handles the conversion of various event types from the
    OpenAI Agents SDK (via agents_mcp) to the ChatKit SSE protocol format.

    Args:
        event: Stream event from Runner.run_streamed()
        stream_builder: StreamBuilder instance for state management

    Returns:
        Formatted SSE event string, or None if event should be skipped

    Event Type Mappings:
        - ResponseTextDeltaEvent (delta) → response_delta SSE
        - ToolCallEvent (tool_name, arguments) → tool_call SSE
        - ToolCallResultEvent (tool_name, result) → tool_call SSE (completed)
        - AgentUpdatedStreamEvent (content) → thinking SSE
        - AgentThinkingEvent (reasoning) → thinking SSE
        - ErrorEvent (error) → error SSE
        - Other events → None (skipped)

    Example:
        >>> event = ResponseTextDeltaEvent(delta="Hello")
        >>> sse = map_agent_event_to_chatkit(event, stream_builder)
        >>> print(sse)
        'event: response_delta\\ndata: {"delta": "Hello", "accumulated": "Hello"}\\n\\n'
    """
    event_type = type(event).__name__

    # Handle text delta events (agent text responses)
    if hasattr(event, 'delta') and event.delta:
        return stream_builder.add_response_delta(event.delta)

    # Handle tool call initiation events
    elif hasattr(event, 'tool_name') and not hasattr(event, 'result'):
        tool_name = event.tool_name
        tool_args = getattr(event, 'arguments', {})
        return stream_builder.add_tool_call(
            tool_name=tool_name,
            arguments=tool_args,
            status=ToolStatus.IN_PROGRESS
        )

    # Handle tool call completion events
    elif hasattr(event, 'tool_name') and hasattr(event, 'result'):
        tool_name = event.tool_name
        tool_args = getattr(event, 'arguments', {})
        return stream_builder.add_tool_call(
            tool_name=tool_name,
            arguments=tool_args,
            status=ToolStatus.COMPLETED
        )

    # Handle agent thinking/reasoning events
    elif event_type in ["AgentUpdatedStreamEvent", "AgentThinkingEvent"]:
        # Try multiple attribute names for content
        content = None
        for attr in ['content', 'reasoning', 'thought', 'message']:
            if hasattr(event, attr):
                content = getattr(event, attr)
                if content:
                    break

        if content:
            return stream_builder.add_thinking(str(content))

    # Handle explicit error events
    elif event_type == "ErrorEvent" or hasattr(event, 'error'):
        error_msg = getattr(event, 'error', str(event))
        error_type_str = getattr(event, 'error_type', 'GEMINI_API_ERROR')

        # Map error type string to ErrorType enum
        try:
            error_type = ErrorType[error_type_str.upper()]
        except (KeyError, AttributeError):
            error_type = ErrorType.GEMINI_API_ERROR

        return stream_builder.add_error(
            error_type=error_type,
            message=str(error_msg),
            recoverable=getattr(event, 'recoverable', True)
        )

    # Handle raw response events (fallback for text content)
    elif event_type == "raw_response_event" and hasattr(event, 'content'):
        content = event.content
        if isinstance(content, str) and content.strip():
            return stream_builder.add_response_delta(content)

    # Skip other event types (debug, metadata, etc.)
    return None


class StreamBuilder:
    """
    Helper class for building streaming responses with accumulated state.

    Maintains accumulated text for response_delta events and tracks tools called.
    """

    def __init__(self):
        """Initialize the stream builder."""
        self.accumulated_text: str = ""
        self.tools_called: List[str] = []

    def add_thinking(self, content: str) -> str:
        """
        Add a thinking event to the stream.

        Args:
            content: Agent reasoning content

        Returns:
            Formatted SSE thinking event
        """
        return thinking_event(content)

    def add_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        status: ToolStatus = ToolStatus.IN_PROGRESS
    ) -> str:
        """
        Add a tool call event to the stream.

        Args:
            tool_name: MCP tool name
            arguments: Tool arguments
            status: Tool execution status

        Returns:
            Formatted SSE tool_call event
        """
        if tool_name not in self.tools_called:
            self.tools_called.append(tool_name)
        return tool_call_event(tool_name, arguments, status)

    def add_response_delta(self, delta: str) -> str:
        """
        Add a response delta event to the stream.

        Automatically accumulates text.

        Args:
            delta: Incremental text chunk

        Returns:
            Formatted SSE response_delta event
        """
        self.accumulated_text += delta
        return response_delta_event(delta, self.accumulated_text)

    def add_error(
        self,
        error_type: ErrorType,
        message: str,
        recoverable: bool = False
    ) -> str:
        """
        Add an error event to the stream.

        Args:
            error_type: Type of error
            message: User-friendly error message
            recoverable: Whether recoverable

        Returns:
            Formatted SSE error event
        """
        return error_event(error_type, message, recoverable)

    def add_done(self, final_output: Optional[str] = None, success: bool = True) -> str:
        """
        Add a done event to the stream.

        Uses accumulated text as final_output if not provided.

        Args:
            final_output: Final message (defaults to accumulated text)
            success: Whether operation succeeded

        Returns:
            Formatted SSE done event
        """
        output = final_output if final_output is not None else self.accumulated_text
        return done_event(output, self.tools_called, success)

    def reset(self):
        """Reset the builder state for a new stream."""
        self.accumulated_text = ""
        self.tools_called = []
