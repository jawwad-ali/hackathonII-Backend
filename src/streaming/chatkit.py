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
    # EventType/Enum members stringify to "EventType.X" by default; SSE needs the raw value.
    if isinstance(event_type, Enum):
        event_type = str(getattr(event_type, "value", event_type))
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
    # agents>=0.6 stream events provide a stable `.type` discriminator.
    event_kind = getattr(event, "type", None)

    # ---- Raw model streaming events (text deltas, lifecycle, etc.) ----
    if event_kind == "raw_response_event":
        raw = getattr(event, "data", None)
        if raw is None:
            return None

        # Text deltas (preferred).
        delta = getattr(raw, "delta", None)
        if isinstance(delta, str) and delta:
            return stream_builder.add_response_delta(delta)

        # Some providers emit only "done" events with a full text payload.
        text = getattr(raw, "text", None)
        if isinstance(text, str) and text and not stream_builder.accumulated_text:
            return stream_builder.add_response_delta(text)

        # Surface raw errors as ChatKit error events (best-effort).
        raw_type = getattr(raw, "type", None)
        if isinstance(raw_type, str) and "error" in raw_type.lower():
            message = (
                getattr(raw, "message", None)
                or getattr(raw, "error", None)
                or str(raw)
            )
            return stream_builder.add_error(
                error_type=ErrorType.GEMINI_API_ERROR,
                message=str(message),
                recoverable=True,
            )

        return None

    # ---- Structured run item events (tool calls, tool outputs, messages, etc.) ----
    if event_kind == "run_item_stream_event":
        name = getattr(event, "name", None)
        item = getattr(event, "item", None)

        # Tool call created.
        if name == "tool_called" and item is not None and hasattr(item, "raw_item"):
            raw_item = getattr(item, "raw_item", None)

            tool_name = None
            call_id = None
            raw_args: Any = None

            # Responses API function tool call
            tool_name = getattr(raw_item, "name", None)
            call_id = getattr(raw_item, "call_id", None)
            raw_args = getattr(raw_item, "arguments", None)

            # Alternate shapes (dicts, chat-completions tool calls, etc.)
            if tool_name is None and isinstance(raw_item, dict):
                tool_name = raw_item.get("name") or raw_item.get("tool_name")
                call_id = raw_item.get("call_id") or raw_item.get("callId") or raw_item.get("id")
                raw_args = raw_item.get("arguments") or raw_item.get("args")
            elif tool_name is None and hasattr(raw_item, "function"):
                func = getattr(raw_item, "function", None)
                tool_name = getattr(func, "name", None)
                raw_args = getattr(func, "arguments", raw_args)

            tool_args: Dict[str, Any] = {}
            if isinstance(raw_args, str):
                try:
                    tool_args = json.loads(raw_args) if raw_args.strip() else {}
                except json.JSONDecodeError:
                    tool_args = {"raw": raw_args}
            elif isinstance(raw_args, dict):
                tool_args = raw_args

            if isinstance(call_id, str) and call_id and tool_name:
                stream_builder.track_tool_call(call_id=call_id, tool_name=str(tool_name), arguments=tool_args)

            if tool_name:
                return stream_builder.add_tool_call(
                    tool_name=str(tool_name),
                    arguments=tool_args,
                    status=ToolStatus.IN_PROGRESS,
                )

            return None

        # Tool output created (best-effort correlation via call_id).
        if name == "tool_output" and item is not None and hasattr(item, "raw_item"):
            raw_item = getattr(item, "raw_item", None)

            call_id = None
            if isinstance(raw_item, dict):
                call_id = raw_item.get("call_id") or raw_item.get("callId") or raw_item.get("id")
            else:
                call_id = getattr(raw_item, "call_id", None) or getattr(raw_item, "callId", None)

            if isinstance(call_id, str) and call_id:
                tracked = stream_builder.get_tracked_tool_call(call_id)
                if tracked is not None:
                    tool_name, tool_args = tracked
                    return stream_builder.add_tool_call(
                        tool_name=tool_name,
                        arguments=tool_args,
                        status=ToolStatus.COMPLETED,
                    )

            return None

        # Message output created (fallback when we don't receive raw text deltas).
        if name == "message_output_created" and item is not None and hasattr(item, "raw_item"):
            if stream_builder.accumulated_text:
                return None

            message = getattr(item, "raw_item", None)
            contents = getattr(message, "content", None)
            if isinstance(contents, list):
                text_parts: list[str] = []
                for part in contents:
                    part_text = getattr(part, "text", None)
                    if isinstance(part_text, str) and part_text:
                        text_parts.append(part_text)
                    refusal = getattr(part, "refusal", None)
                    if isinstance(refusal, str) and refusal:
                        text_parts.append(refusal)
                text = "".join(text_parts).strip()
                if text:
                    return stream_builder.add_response_delta(text)

            return None

        # Reasoning summary item created.
        if name == "reasoning_item_created" and item is not None and hasattr(item, "raw_item"):
            reasoning = getattr(item, "raw_item", None)
            summaries = getattr(reasoning, "summary", None)
            if isinstance(summaries, list) and summaries:
                summary_texts: list[str] = []
                for summary_part in summaries:
                    text = getattr(summary_part, "text", None)
                    if isinstance(text, str) and text:
                        summary_texts.append(text)
                summary = " ".join(summary_texts).strip()
                if summary:
                    return stream_builder.add_thinking(summary)

            return None

        return None

    # ---- Backwards-compatible fallbacks for older / custom event shapes ----
    if hasattr(event, "delta") and getattr(event, "delta"):
        return stream_builder.add_response_delta(str(getattr(event, "delta")))

    if hasattr(event, "tool_name"):
        tool_name = getattr(event, "tool_name")
        tool_args = getattr(event, "arguments", {}) or {}
        status = ToolStatus.COMPLETED if hasattr(event, "result") else ToolStatus.IN_PROGRESS
        return stream_builder.add_tool_call(tool_name=str(tool_name), arguments=tool_args, status=status)

    if hasattr(event, "error"):
        return stream_builder.add_error(
            error_type=ErrorType.GEMINI_API_ERROR,
            message=str(getattr(event, "error")),
            recoverable=getattr(event, "recoverable", True),
        )

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
        self._tool_calls_by_id: Dict[str, tuple[str, Dict[str, Any]]] = {}

    def track_tool_call(self, call_id: str, tool_name: str, arguments: Dict[str, Any]) -> None:
        """Track tool call metadata so later tool_output events can be correlated."""
        if call_id:
            self._tool_calls_by_id[call_id] = (tool_name, arguments)

    def get_tracked_tool_call(self, call_id: str) -> Optional[tuple[str, Dict[str, Any]]]:
        """Return (tool_name, arguments) for a previously tracked call_id, if any."""
        return self._tool_calls_by_id.get(call_id)

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
        self._tool_calls_by_id = {}
