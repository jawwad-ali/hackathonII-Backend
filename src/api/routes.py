"""
API Routes for AI Agent Orchestrator

Implements the ChatKit streaming endpoint for natural language todo operations.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Any, List, Optional
import logging
import re
import time
import uuid

from agents import Runner
from agents.mcp import MCPServerStdio

from src.api.schemas import ChatRequest, ErrorResponse
from src.streaming.chatkit import StreamBuilder, ErrorType, ToolStatus, map_agent_event_to_chatkit
from src.orchestrators.todo_agent import create_todo_agent
from src.config import settings
from src.observability.metrics import metrics_tracker
from src.observability.logging import set_thread_id  # T031: Import for context metadata
from src.resilience.circuit_breaker import CircuitBreakerError

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/chat", tags=["chat"])


async def initialize_agent_with_mcp(mcp_server: Optional[MCPServerStdio]):
    """
    Initialize TodoAgent with MCP server connection from app.state.

    This function creates the TodoAgent and passes the MCP server instance
    for manual tool discovery and registration.

    T013: Agent initialization function that uses app.state.mcp_server

    Args:
        mcp_server: MCPServerStdio instance from app.state.mcp_server, or None
                   if MCP connection failed (degraded mode)

    Returns:
        Agent: Configured TodoAgent with MCP tools (if mcp_server is not None)
               or without tools (if mcp_server is None for degraded mode)

    Example:
        >>> # In endpoint handler
        >>> from fastapi import Request
        >>> mcp_server = request.app.state.mcp_server
        >>> agent = await initialize_agent_with_mcp(mcp_server)
        >>> # Agent now has access to all discovered MCP tools
    """
    # Build list of MCP servers for agent initialization
    # If mcp_server is None (degraded mode), agent will be created without tools
    mcp_servers: List[MCPServerStdio] = []

    if mcp_server is not None:
        mcp_servers.append(mcp_server)

        logger.info(
            "Initializing TodoAgent with MCP server connection",
            extra={
                "mcp_server_name": "TodoDatabaseServer",
                "mcp_servers_count": 1,
                "degraded_mode": False
            }
        )
    else:
        logger.warning(
            "Initializing TodoAgent in degraded mode - no MCP server available",
            extra={
                "mcp_servers_count": 0,
                "degraded_mode": True
            }
        )

    # Create TodoAgent with MCP servers (or empty list for degraded mode)
    # The create_todo_agent function handles None/empty list gracefully
    # Now async to support manual tool discovery
    agent = await create_todo_agent(mcp_servers=mcp_servers if mcp_servers else None)

    return agent


def format_todo_list(todos: Any) -> str:
    """
    Format list_todos MCP tool results into natural language response.

    Handles various result formats and creates a user-friendly summary
    of the todo list with relevant details for each item.

    Args:
        todos: Result from list_todos MCP tool (list of todo objects or dict)

    Returns:
        Formatted natural language string describing the todos

    Example:
        >>> todos = [{"title": "Buy eggs", "status": "pending", "priority": "medium"}]
        >>> format_todo_list(todos)
        "I found 1 todo:\n\n1. Buy eggs (Medium priority, Pending)"
    """
    # Handle empty or None results
    if not todos:
        return "You don't have any todos matching those criteria."

    # Handle list of todos (most common case)
    if isinstance(todos, list):
        count = len(todos)

        # Empty list
        if count == 0:
            return "You don't have any todos matching those criteria."

        # Build the header
        if count == 1:
            header = "I found 1 todo:\n\n"
        else:
            header = f"I found {count} todos:\n\n"

        # Format each todo
        formatted_items = []
        for idx, todo in enumerate(todos, 1):
            # Extract todo fields (handle dict or object)
            if isinstance(todo, dict):
                title = todo.get('title', 'Untitled')
                status = todo.get('status', 'unknown')
                priority = todo.get('priority', 'medium')
                due_date = todo.get('due_date')
                tags = todo.get('tags', [])
            else:
                # Handle object with attributes
                title = getattr(todo, 'title', 'Untitled')
                status = getattr(todo, 'status', 'unknown')
                priority = getattr(todo, 'priority', 'medium')
                due_date = getattr(todo, 'due_date', None)
                tags = getattr(todo, 'tags', [])

            # Build todo item string
            item_parts = [f"{idx}. {title}"]

            # Add priority if not default
            if priority and priority.lower() != 'medium':
                item_parts.append(f"{priority.capitalize()} priority")

            # Add status
            if status:
                item_parts.append(status.capitalize())

            # Add due date if present
            if due_date:
                item_parts.append(f"Due: {due_date}")

            # Add tags if present
            if tags and len(tags) > 0:
                tags_str = ', '.join(f"#{tag}" for tag in tags)
                item_parts.append(tags_str)

            # Join parts with proper formatting
            if len(item_parts) > 1:
                formatted_item = f"{item_parts[0]} ({', '.join(item_parts[1:])})"
            else:
                formatted_item = item_parts[0]

            formatted_items.append(formatted_item)

        # Combine header and items
        return header + '\n'.join(formatted_items)

    # Handle dict result (possible single todo or metadata)
    elif isinstance(todos, dict):
        if 'todos' in todos:
            # Recursive call with actual todos list
            return format_todo_list(todos['todos'])
        else:
            # Single todo object
            return format_todo_list([todos])

    # Handle string result (error message or simple response)
    elif isinstance(todos, str):
        return todos

    # Fallback for unknown format
    return f"Retrieved {len(todos) if hasattr(todos, '__len__') else 'some'} todos."


async def chat_stream_generator(
    message: str,
    request_id: str,
    mcp_server: Optional[MCPServerStdio],
    context_metadata: Optional[dict] = None
) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE events for the chat stream.

    Calls Runner.run_streamed() with TodoAgent to execute
    natural language todo operations and stream the results in ChatKit format.

    T013: Uses mcp_server from app.state to initialize agent with MCP tools
    T030: Accepts context_metadata for observability (request_id, thread_id, timestamp)

    Args:
        message: Sanitized user message from ChatRequest
        request_id: Request ID for correlation and logging
        mcp_server: MCPServerStdio instance from app.state.mcp_server (or None for degraded mode)
        context_metadata: Optional dict with request_id, thread_id, timestamp for observability

    Yields:
        SSE formatted event strings (thinking, tool_call, response_delta, error, done)

    Context Inference (T063):
        Within a single request, the system tracks:
        - recent_list_results: Todos returned by list_todos (for "update the first one")
        - last_created_todo_id: ID of most recently created todo
        - last_updated_todo_id: ID of most recently updated todo

        This enables the agent to infer todo_id from context when the user refers to
        "that task", "the first one", etc. within the same conversational turn.

        Note: This is request-scoped only. For cross-request conversation memory,
        the frontend must maintain conversation state and include relevant context
        in subsequent requests.

    Note:
        Event mapping from OpenAI Agents SDK to ChatKit format will be enhanced
        in T028. This implementation provides basic streaming functionality.
    """
    stream_builder = StreamBuilder()

    # T063: Context tracking for todo_id inference within the current request
    # This allows the agent to reference todos from recent operations in the same conversation turn
    # Note: This is request-scoped context, not cross-request conversation history
    # For cross-request context, the frontend would need to maintain conversation state
    context_state = {
        "recent_list_results": None,  # Track most recent list_todos results
        "last_created_todo_id": None,  # Track most recently created todo
        "last_updated_todo_id": None,  # Track most recently updated todo
        # T072: Mass deletion detection state
        "potential_mass_deletion": False,  # Flag set when list_todos called with delete intent
        "deletion_candidate_count": 0,  # Count of todos that would be deleted
        "deletion_filters": None,  # Filters used for mass deletion query
        # T074: Confirmation/cancellation parsing state
        "is_confirmation_response": False,  # Flag set when user confirms an operation
        "is_cancellation_response": False,  # Flag set when user cancels an operation
        "delete_intent_in_message": False,  # Parsed delete intent from user message
        "explicit_mass_delete": False,  # User explicitly requested delete all/clear all
    }

    # Initialize detected_intent to None to avoid UnboundLocalError in exception handlers
    # This variable tracks the detected user intent (CREATE, LIST, UPDATE, DELETE)
    detected_intent = None

    try:
        # T031: Use context_metadata for logging throughout execution
        # Default context if not provided
        if context_metadata is None:
            context_metadata = {
                "request_id": request_id,
                "thread_id": f"thread_{uuid.uuid4()}",
                "timestamp": time.time()
            }

        # T031: Set thread_id in logging context for automatic injection into all logs
        thread_id = context_metadata.get("thread_id")
        if thread_id:
            set_thread_id(thread_id)

        # Log request received with full context metadata
        logger.info(
            "Chat stream started",
            extra={
                "request_id": context_metadata.get("request_id", request_id),
                "thread_id": thread_id,
                "timestamp": context_metadata.get("timestamp"),
                "message_length": len(message)
            }
        )

        # T074: Parse user message for confirmation/cancellation keywords
        # This helps track when users are responding to mass deletion confirmation requests
        message_lower = message.lower().strip()

        delete_intent_keywords = [
            "delete",
            "remove",
            "clear",
            "cancel",
            "discard",
            "erase",
            "wipe",
            "purge",
        ]
        explicit_mass_keywords = [
            "delete all",
            "remove all",
            "clear all",
            "clear out all",
            "delete everything",
            "remove everything",
            "clear everything",
            "wipe all",
            "purge all",
        ]

        delete_intent_in_message = any(
            keyword in message_lower for keyword in delete_intent_keywords
        )
        explicit_mass_delete = any(
            keyword in message_lower for keyword in explicit_mass_keywords
        )

        context_state["delete_intent_in_message"] = delete_intent_in_message
        context_state["explicit_mass_delete"] = explicit_mass_delete

        # Define confirmation keywords (from agent instructions)
        confirmation_keywords = [
            "yes",
            "confirm",
            "proceed",
            "yes delete all",
            "yes, delete all",
            "do it",
            "go ahead",
            "confirm delete",
        ]
        cancellation_keywords = ["no", "cancel", "wait", "stop", "don't", "abort",
                                "never mind", "no don't", "do not"]

        # Check for confirmation response
        is_confirmation_response = any(
            message_lower == keyword or message_lower.startswith(keyword + " ") or message_lower.startswith(keyword + ",")
            for keyword in confirmation_keywords
        )

        # Check for cancellation response
        is_cancellation_response = any(
            message_lower == keyword or message_lower.startswith(keyword + " ") or message_lower.startswith(keyword + ",")
            for keyword in cancellation_keywords
        )

        # Track confirmation/cancellation state
        context_state["is_confirmation_response"] = is_confirmation_response
        context_state["is_cancellation_response"] = is_cancellation_response

        # T074: Log confirmation parsing results
        if is_confirmation_response:
            logger.info(
                "Confirmation response detected in user message",
                extra={
                    "request_id": request_id,
                    "user_message": message[:100],  # Log first 100 chars
                    "response_type": "CONFIRM"
                }
            )
        elif is_cancellation_response:
            logger.info(
                "Cancellation response detected in user message",
                extra={
                    "request_id": request_id,
                    "user_message": message[:100],
                    "response_type": "CANCEL"
                }
            )

        # T014: Check if MCP server is available (degraded mode check)
        # Per FR-010 and SC-013: Return HTTP 200 with user-friendly error (not 503)
        if mcp_server is None:
            logger.warning(
                "Request received in degraded mode - MCP server unavailable",
                extra={
                    "request_id": request_id,
                    "degraded_mode": True
                }
            )

            # Stream error event with degraded mode message
            # Per SC-013: HTTP 200 with user-friendly error message in response body
            degraded_message = (
                "I'm currently unable to access the todo database due to a temporary service issue. "
                "The todo management system is unavailable right now, but our team is working to restore it. "
                "Please try again in a few moments."
            )

            yield stream_builder.add_error(
                error_type=ErrorType.MCP_CONNECTION_ERROR,
                message=degraded_message,
                recoverable=True
            )

            # Send done event to close the stream gracefully
            yield stream_builder.add_done(
                final_output="Service temporarily unavailable",
                success=False
            )

            # Log the degraded mode response
            logger.info(
                "Degraded mode error returned to user",
                extra={
                    "request_id": request_id,
                    "degraded_mode": True,
                    "error_type": "MCP_CONNECTION_ERROR"
                }
            )

            # Exit early - don't try to run the agent without MCP tools
            return

        # T013: Initialize TodoAgent with MCP server from app.state
        # The initialize_agent_with_mcp function handles both normal and degraded mode
        # Now async to support manual tool discovery
        agent = await initialize_agent_with_mcp(mcp_server)

        logger.info(
            "TodoAgent initialized",
            extra={
                "request_id": request_id,
                "agent_name": agent.name,
                "has_mcp_tools": True,
                "tools_count": len(agent.tools) if hasattr(agent, 'tools') and agent.tools else 0
            }
        )

        # Stream initial thinking event
        # T074: Provide context-aware thinking based on confirmation parsing
        if is_confirmation_response:
            yield stream_builder.add_thinking(
                "Confirmation received. Processing your confirmed action..."
            )
        elif is_cancellation_response:
            yield stream_builder.add_thinking(
                "Cancellation received. Aborting the requested operation..."
            )
        else:
            yield stream_builder.add_thinking(
                "Processing your request and analyzing intent..."
            )

        # Run agent with streaming
        # T013: MCP tools are already registered with agent via mcp_servers parameter
        # No separate context needed - the Agent handles MCP communication
        result = Runner.run_streamed(
            agent,
            message,
            max_turns=settings.AGENT_MAX_TURNS,
        )

        # T031: Include context metadata in all logging
        logger.info(
            "Runner.run_streamed() initiated",
            extra={
                "request_id": context_metadata.get("request_id", request_id),
                "thread_id": context_metadata.get("thread_id"),
                "timestamp": context_metadata.get("timestamp"),
                "has_mcp_tools": mcp_server is not None
            }
        )

        # Process stream events from OpenAI Agents SDK
        # Map events to ChatKit SSE format using enhanced mapper (T028)
        # Note: detected_intent is initialized at function start to avoid UnboundLocalError
        tool_start_times = {}  # Track tool execution start times for duration calculation
        last_tool_call_info = {}  # Track the last tool call for pairing with output events

        async for event in result.stream_events():
            event_type = type(event).__name__

            logger.debug(
                "Stream event received: {event_type}",
                extra={
                    "request_id": request_id,
                    "event_type": event_type
                }
            )

            # T045: Detect CREATE intent when create_todo tool is called
            # T047: Stream thinking event showing parameter extraction reasoning
            # T051: Log mcp_tool_called event with create_todo details
            # T053: Detect LIST intent when list_todos tool is called (User Story 2)
            #
            # Tool call detection for streaming:
            # Events come via RunItemStreamEvent with item types:
            # - ToolCallItem: contains raw_item.name and raw_item.arguments
            # - ToolCallOutputItem: contains output attribute
            tool_name = None
            tool_args = {}
            tool_result = None
            is_tool_call_event = False
            is_tool_output_event = False

            # Check for RunItemStreamEvent (OpenAI Agents SDK streaming format)
            if event_type == "RunItemStreamEvent" and hasattr(event, 'item'):
                item = event.item
                item_type = type(item).__name__

                if item_type == "ToolCallItem":
                    is_tool_call_event = True
                    if hasattr(item, 'raw_item'):
                        raw_item = item.raw_item
                        tool_name = getattr(raw_item, 'name', None)
                        args_str = getattr(raw_item, 'arguments', '{}')
                        try:
                            import json
                            tool_args = json.loads(args_str) if isinstance(args_str, str) else args_str
                        except (json.JSONDecodeError, TypeError):
                            tool_args = {}

                elif item_type == "ToolCallOutputItem":
                    is_tool_output_event = True
                    tool_result_raw = getattr(item, 'output', None)
                    # Parse JSON string to dict if needed (MCP tools return JSON strings)
                    if isinstance(tool_result_raw, str):
                        try:
                            tool_result = json.loads(tool_result_raw)
                        except (json.JSONDecodeError, TypeError):
                            tool_result = tool_result_raw
                    else:
                        tool_result = tool_result_raw
                    # Retrieve tool name and args from last_tool_call_info (set during ToolCallItem)
                    if last_tool_call_info:
                        tool_name = last_tool_call_info.get('name')
                        tool_args = last_tool_call_info.get('args', {})

            # Legacy check for direct tool_name attribute (older SDK versions)
            elif hasattr(event, 'tool_name'):
                tool_name = event.tool_name
                is_tool_call_event = True
                tool_args = getattr(event, 'arguments', {})
                if hasattr(event, 'result'):
                    is_tool_output_event = True
                    tool_result_raw = event.result
                    # Parse JSON string to dict if needed
                    if isinstance(tool_result_raw, str):
                        try:
                            tool_result = json.loads(tool_result_raw)
                        except (json.JSONDecodeError, TypeError):
                            tool_result = tool_result_raw
                    else:
                        tool_result = tool_result_raw

            # Process tool call events
            if is_tool_call_event and tool_name:
                # Store tool call info for pairing with output events
                last_tool_call_info = {'name': tool_name, 'args': tool_args}

                # Track tool invocation start time (for duration calculation)
                tool_start_times[tool_name] = time.time()

                if tool_name == "create_todo" and detected_intent is None:
                    detected_intent = "CREATE"
                    # tool_args already extracted from RunItemStreamEvent detection above

                    logger.info(
                        "CREATE intent detected - create_todo tool called",
                        extra={
                            "request_id": request_id,
                            "intent": "CREATE",
                            "tool_name": tool_name,
                            "tool_arguments": tool_args
                        }
                    )

                    # T047: Stream thinking event showing parameter extraction for CREATE
                    # Build a user-friendly description of extracted parameters
                    extracted_params = []
                    if 'title' in tool_args:
                        extracted_params.append(f"Task: '{tool_args['title']}'")
                    if 'due_date' in tool_args:
                        extracted_params.append(f"Due: {tool_args['due_date']}")
                    if 'priority' in tool_args:
                        extracted_params.append(f"Priority: {tool_args['priority']}")
                    if 'tags' in tool_args and tool_args['tags']:
                        extracted_params.append(f"Tags: {', '.join(tool_args['tags'])}")

                    if extracted_params:
                        reasoning = f"I've extracted the following from your request: {' | '.join(extracted_params)}. Creating your todo now..."
                        yield stream_builder.add_thinking(reasoning)

                    # NOTE: tool_call events are emitted by map_agent_event_to_chatkit()
                    # Do NOT emit duplicate here

                # T053: Detect LIST intent when list_todos tool is called (User Story 2)
                elif tool_name == "list_todos" and detected_intent is None:
                    # tool_args already extracted from RunItemStreamEvent detection above
                    is_delete_lookup = context_state.get("delete_intent_in_message", False)

                    if is_delete_lookup:
                        detected_intent = "DELETE"
                        logger.info(
                            "DELETE intent detected - list_todos used to resolve deletion targets",
                            extra={
                                "request_id": request_id,
                                "intent": "DELETE",
                                "tool_name": tool_name,
                                "tool_arguments": tool_args
                            }
                        )

                        # For delete flows, list_todos is used to gather IDs only.
                        filter_params = []
                        if 'status' in tool_args:
                            filter_params.append(f"Status: {tool_args['status']}")
                        if 'priority' in tool_args:
                            filter_params.append(f"Priority: {tool_args['priority']}")
                        if 'due_date_filter' in tool_args:
                            filter_params.append(f"Due: {tool_args['due_date_filter']}")
                        if 'tags' in tool_args and tool_args['tags']:
                            filter_params.append(f"Tags: {', '.join(tool_args['tags'])}")

                        if filter_params:
                            reasoning = (
                                "Finding todos that match your delete request: "
                                f"{' | '.join(filter_params)}."
                            )
                        else:
                            reasoning = "Finding todos that match your delete request."
                        yield stream_builder.add_thinking(reasoning)
                    else:
                        detected_intent = "LIST"
                        logger.info(
                            "LIST intent detected - list_todos tool called",
                            extra={
                                "request_id": request_id,
                                "intent": "LIST",
                                "tool_name": tool_name,
                                "tool_arguments": tool_args
                            }
                        )

                        # T055: Stream thinking event showing filter extraction reasoning for LIST
                        # Build a user-friendly description of extracted filter parameters
                        filter_params = []
                        if 'status' in tool_args:
                            filter_params.append(f"Status: {tool_args['status']}")
                        if 'priority' in tool_args:
                            filter_params.append(f"Priority: {tool_args['priority']}")
                        if 'due_date_filter' in tool_args:
                            filter_params.append(f"Due: {tool_args['due_date_filter']}")
                        if 'tags' in tool_args and tool_args['tags']:
                            filter_params.append(f"Tags: {', '.join(tool_args['tags'])}")

                        if filter_params:
                            reasoning = (
                                "I'm looking for todos with these filters: "
                                f"{' | '.join(filter_params)}. Fetching your list now..."
                            )
                            yield stream_builder.add_thinking(reasoning)
                        else:
                            reasoning = "I'm fetching your todo list..."
                            yield stream_builder.add_thinking(reasoning)

                    # NOTE: tool_call events are emitted by map_agent_event_to_chatkit()
                    # Do NOT emit duplicate here

                # T062: Detect UPDATE intent when update_todo tool is called (User Story 3)
                elif tool_name == "update_todo" and detected_intent is None:
                    detected_intent = "UPDATE"
                    # tool_args already extracted from RunItemStreamEvent detection above

                    logger.info(
                        "UPDATE intent detected - update_todo tool called",
                        extra={
                            "request_id": request_id,
                            "intent": "UPDATE",
                            "tool_name": tool_name,
                            "tool_arguments": tool_args
                        }
                    )

                    # T065: Stream thinking event showing todo_id inference and field extraction reasoning
                    # Build a user-friendly description of the update operation
                    update_params = []

                    # Show which todo is being updated
                    if 'todo_id' in tool_args:
                        update_params.append(f"Todo ID: {tool_args['todo_id']}")

                    # Show what fields are being updated
                    if 'status' in tool_args:
                        update_params.append(f"Status -> {tool_args['status']}")
                    if 'priority' in tool_args:
                        update_params.append(f"Priority -> {tool_args['priority']}")
                    if 'title' in tool_args:
                        update_params.append(f"Title -> '{tool_args['title']}'")
                    if 'due_date' in tool_args:
                        due_value = tool_args['due_date']
                        if due_value is None:
                            update_params.append("Due date -> (cleared)")
                        else:
                            update_params.append(f"Due date -> {due_value}")
                    if 'tags' in tool_args and tool_args['tags']:
                        update_params.append(f"Tags -> {', '.join(tool_args['tags'])}")

                    if update_params:
                        reasoning = f"I'm updating the todo with these changes: {' | '.join(update_params)}. Applying updates now..."
                        yield stream_builder.add_thinking(reasoning)
                    else:
                        reasoning = "I'm updating the todo..."
                        yield stream_builder.add_thinking(reasoning)

                    # NOTE: tool_call events are emitted by map_agent_event_to_chatkit()
                    # Do NOT emit duplicate here

                # T071: Detect DELETE intent when delete_todo tool is called (User Story 4)
                elif tool_name == "delete_todo":
                    detected_intent = "DELETE"
                    # tool_args already extracted from RunItemStreamEvent detection above

                    # T074: Check if this deletion follows a user confirmation
                    deletion_after_confirmation = (
                        context_state.get("is_confirmation_response", False)
                        or context_state.get("explicit_mass_delete", False)
                    )

                    logger.info(
                        "DELETE intent detected - delete_todo tool called",
                        extra={
                            "request_id": request_id,
                            "intent": "DELETE",
                            "tool_name": tool_name,
                            "tool_arguments": tool_args,
                            "deletion_after_confirmation": deletion_after_confirmation
                        }
                    )

                    # T076: Stream thinking event showing deletion scope and safety check reasoning
                    # Build a user-friendly description of the delete operation
                    delete_params = []

                    # Show which todo is being deleted
                    if 'todo_id' in tool_args:
                        delete_params.append(f"Todo ID: {tool_args['todo_id']}")
                    if 'id' in tool_args and 'todo_id' not in tool_args:
                        delete_params.append(f"Todo ID: {tool_args['id']}")
                    if 'todo_ids' in tool_args and isinstance(tool_args.get('todo_ids'), list):
                        delete_params.append(f"Todo IDs: {tool_args['todo_ids']}")
                    if 'status' in tool_args:
                        delete_params.append(f"Status: {tool_args['status']}")
                    if 'priority' in tool_args:
                        delete_params.append(f"Priority: {tool_args['priority']}")
                    if 'keyword' in tool_args:
                        delete_params.append(f"Keyword: {tool_args['keyword']}")

                    # Check if this is a mass deletion (multiple IDs or filters indicating mass operation)
                    is_mass_deletion = False
                    if 'todo_ids' in tool_args and isinstance(tool_args.get('todo_ids'), list):
                        num_todos = len(tool_args['todo_ids'])
                        if num_todos >= 3:
                            is_mass_deletion = True
                            delete_params.append(f"Deleting {num_todos} todos")

                    # T074: Indicate if confirmation was provided (for mass deletions)
                    # Check both tool arguments and our context state
                    if tool_args.get('confirm') is True:
                        delete_params.append("Confirmed by user")
                    elif deletion_after_confirmation:
                        delete_params.append("User confirmed deletion")

                    # Build reasoning message
                    if is_mass_deletion:
                        reasoning = f"WARNING: Mass deletion detected: {' | '.join(delete_params)}. Verifying safety checks and executing deletion..."
                    elif delete_params:
                        reasoning = f"I'm deleting the todo: {' | '.join(delete_params)}. Processing deletion now..."
                    else:
                        reasoning = "I'm processing the deletion request..."

                    yield stream_builder.add_thinking(reasoning)

                    # NOTE: tool_call events are emitted by map_agent_event_to_chatkit()
                    # Do NOT emit duplicate here

            # T051: Log mcp_tool_called event when tool execution completes
            # Detect tool completion via ToolCallOutputItem (is_tool_output_event)
            if is_tool_output_event and tool_name:
                # Calculate tool execution duration
                if tool_name in tool_start_times:
                    tool_duration_ms = (time.time() - tool_start_times[tool_name]) * 1000
                else:
                    # Estimate minimal duration if start time not captured
                    tool_duration_ms = 1.0

                # Track MCP tool call with metrics
                metrics_tracker.track_mcp_tool_called(
                    request_id=request_id,
                    tool_name=tool_name,
                    duration_ms=tool_duration_ms
                )

                # T051 & T060 & T069 & T080: Log mcp_tool_called event for observability (FR-011)
                # This logs ALL MCP tool executions including:
                # - create_todo (User Story 1) - T051
                # - list_todos (User Story 2) - T060
                # - update_todo (User Story 3) - T069
                # - delete_todo (User Story 4) - T080
                logger.info(
                    "MCP tool execution completed",
                    extra={
                        "event": "mcp_tool_called",
                        "request_id": request_id,
                        "tool_name": tool_name,
                        "tool_arguments": tool_args,
                        "duration_ms": tool_duration_ms,
                        "success": True
                    }
                )

                # T063: Track created todo_id for potential reference in subsequent operations
                if tool_name == "create_todo" and detected_intent == "CREATE":
                    # Extract todo_id from result if available
                    if isinstance(tool_result, dict) and 'id' in tool_result:
                        context_state["last_created_todo_id"] = tool_result['id']
                        logger.debug(
                            "Stored created todo_id in context",
                            extra={
                                "request_id": request_id,
                                "todo_id": tool_result['id']
                            }
                        )
                    elif hasattr(tool_result, 'id'):
                        context_state["last_created_todo_id"] = tool_result.id
                        logger.debug(
                            "Stored created todo_id in context",
                            extra={
                                "request_id": request_id,
                                "todo_id": tool_result.id
                            }
                        )

                # T063: Track updated todo_id for logging and context
                if tool_name == "update_todo" and detected_intent == "UPDATE":
                    # tool_args already set from last_tool_call_info
                    if 'todo_id' in tool_args:
                        context_state["last_updated_todo_id"] = tool_args['todo_id']
                        logger.debug(
                            "Stored updated todo_id in context",
                            extra={
                                "request_id": request_id,
                                "todo_id": tool_args['todo_id']
                            }
                        )

                # T078: Track delete_todo completion for observability (User Story 4)
                # NOTE: We do NOT stream response_delta here - let the model generate
                # the natural language response based on the tool output it receives.
                # This prevents duplicate output (hardcoded message + model response).
                if tool_name == "delete_todo" and detected_intent == "DELETE":
                    # tool_result already set from ToolCallOutputItem

                    # Extract deletion details for logging only
                    success = False
                    deleted_ids = []
                    deleted_count = 0
                    was_mass_deletion = context_state.get("potential_mass_deletion", False)

                    if isinstance(tool_result, dict):
                        success = tool_result.get('success', True)
                        requested_count = tool_result.get("requested_count")
                        deleted_count = tool_result.get("deleted_count", 0)
                        deleted_ids = tool_result.get("deleted_ids") or []
                        if not deleted_ids and tool_result.get('deleted_id'):
                            deleted_ids = [tool_result.get('deleted_id')]

                        if requested_count and requested_count >= 3:
                            was_mass_deletion = True
                    else:
                        success = True
                        if 'todo_id' in tool_args:
                            deleted_ids = [tool_args.get('todo_id')]
                        elif 'id' in tool_args:
                            deleted_ids = [tool_args.get('id')]
                        elif 'todo_ids' in tool_args:
                            deleted_ids = tool_args.get('todo_ids') or []
                        deleted_count = len(deleted_ids)

                    # T080: Log deletion for observability (but don't stream response)
                    logger.info(
                        "DELETE operation completed",
                        extra={
                            "request_id": request_id,
                            "deleted_id": deleted_ids[0] if deleted_ids else None,
                            "deleted_ids": deleted_ids if len(deleted_ids) > 1 else None,
                            "deleted_count": deleted_count,
                            "success": success,
                            "was_mass_deletion": was_mass_deletion,
                            "operation": "delete_todo_completed"
                        }
                    )

                # T057 & T058: Format list_todos results and stream as response_delta events
                if tool_name == "list_todos" and detected_intent == "LIST":
                    # tool_result already set from ToolCallOutputItem

                    # T063: Store list results in context for potential todo_id inference
                    # This allows subsequent update/delete operations in the same request
                    # to reference "the first todo", "that task", etc.
                    context_state["recent_list_results"] = tool_result
                    result_count = 0
                    if isinstance(tool_result, list):
                        result_count = len(tool_result)
                    elif isinstance(tool_result, dict) and isinstance(
                        tool_result.get("todos"), list
                    ):
                        result_count = len(tool_result.get("todos"))
                    logger.debug(
                        "Stored list results in context for todo_id inference",
                        extra={
                            "request_id": request_id,
                            "result_count": result_count
                        }
                    )

                    # T057: Format list_todos results into natural language response
                    formatted_response = format_todo_list(tool_result)

                    # T058: Stream response_delta events with formatted todo list
                    # Stream the formatted response incrementally for better UX
                    if formatted_response:
                        yield stream_builder.add_response_delta(formatted_response)

                    logger.info(
                        "LIST results formatted and streamed",
                        extra={
                            "request_id": request_id,
                            "todo_count": result_count,
                            "response_length": len(formatted_response) if formatted_response else 0
                        }
                    )

                # T072: Detect potential mass deletion scenarios for logging/tracking only
                # NOTE: The delete_todo function handles confirmation internally.
                # We do NOT stream confirmation messages here to avoid duplicate output.
                if tool_name == "list_todos":
                    # tool_result and tool_args already set from ToolCallOutputItem

                    # Check if user message contains deletion keywords
                    has_deletion_intent = context_state.get("delete_intent_in_message", False)

                    # Count the todos that would be affected
                    todo_count = 0
                    if isinstance(tool_result, list):
                        todo_count = len(tool_result)
                    elif isinstance(tool_result, dict):
                        if 'todos' in tool_result:
                            todos_list = tool_result['todos']
                            todo_count = len(todos_list) if isinstance(todos_list, list) else 0
                        elif 'total' in tool_result:
                            todo_count = tool_result['total']

                    # T072: Track mass deletion context for logging
                    if has_deletion_intent and todo_count >= 3:
                        context_state["potential_mass_deletion"] = True
                        context_state["deletion_candidate_count"] = todo_count
                        context_state["deletion_filters"] = tool_args

                        logger.info(
                            f"Mass deletion context - {todo_count} todos may be affected",
                            extra={
                                "request_id": request_id,
                                "deletion_candidate_count": todo_count,
                                "deletion_filters": tool_args,
                            }
                        )

            # Use comprehensive event mapper to convert SDK events to ChatKit SSE
            sse_event = map_agent_event_to_chatkit(event, stream_builder)

            # Yield the formatted SSE event if mapping produced output
            if sse_event:
                yield sse_event

        # Get final output from the streamed result
        # Note: final_output is a property, not a method
        final_result = result.final_output
        logger.info(
            "Agent execution completed",
            extra={
                "request_id": request_id,
                "tools_called": stream_builder.tools_called
            }
        )

        # T059: Send done event with final_output and tools_called
        # The stream_builder.add_done() automatically includes tools_called list
        # For LIST operations, this will be ["list_todos"]
        # For CREATE operations, this will be ["create_todo"]
        # Prefer streamed accumulated text, but fall back to the agent's final_output if no deltas were emitted.
        final_output = stream_builder.accumulated_text
        if not final_output:
            if isinstance(final_result, str) and final_result.strip():
                final_output = final_result.strip()
            elif final_result is not None:
                final_output = str(final_result)
            else:
                final_output = "Request processed successfully."

            # Ensure clients that rely on RESPONSE_DELTA still receive the final text.
            if final_output:
                yield stream_builder.add_response_delta(final_output)
        yield stream_builder.add_done(
            final_output=final_output,
            success=True
        )

        # T074: Enhanced logging with confirmation/cancellation context
        logger.info(
            "Chat stream completed successfully",
            extra={
                "request_id": request_id,
                "detected_intent": detected_intent,
                "tools_called": stream_builder.tools_called,
                "final_output_length": len(final_output),
                "was_confirmation_response": context_state.get("is_confirmation_response", False),
                "was_cancellation_response": context_state.get("is_cancellation_response", False)
            }
        )

    # T085: Graceful degradation for circuit breaker errors per FR-012
    # Handle circuit breaker open state with user-friendly messages
    except CircuitBreakerError as e:
        logger.warning(
            f"Circuit breaker open: {str(e)}",
            extra={
                "request_id": request_id,
                "detected_intent": detected_intent,
                "circuit_breaker": e.circuit_breaker_name if hasattr(e, 'circuit_breaker_name') else "unknown"
            }
        )

        # Determine which circuit breaker is open based on error message
        error_str = str(e).lower()
        is_mcp_breaker = "mcp" in error_str or "todo" in error_str
        is_openai_breaker = "openai" in error_str or "api" in error_str

        # T085: Provide graceful degradation messages based on which service is unavailable
        if is_mcp_breaker:
            # MCP server circuit breaker open - cannot access todo data
            error_type = ErrorType.MCP_CONNECTION_ERROR
            error_message = (
                "The todo management service is temporarily unavailable due to repeated failures. "
                "Our system is automatically monitoring the service and will restore access once it's healthy. "
                "Please try again in a few moments."
            )
            recoverable = True  # Will auto-recover when circuit breaker closes

        elif is_openai_breaker:
            # OpenAI API circuit breaker open - cannot process natural language
            error_type = ErrorType.OPENAI_API_ERROR
            error_message = (
                "The AI language service is temporarily unavailable due to repeated failures. "
                "Our system is automatically monitoring the service and will restore access once it's healthy. "
                "Please try again in a few moments."
            )
            recoverable = True  # Will auto-recover when circuit breaker closes

        else:
            # Generic circuit breaker error
            error_type = ErrorType.OPENAI_API_ERROR
            error_message = (
                "A critical service is temporarily unavailable. "
                "Our system is working to restore access. Please try again shortly."
            )
            recoverable = True

        # Stream error event with graceful degradation message
        yield stream_builder.add_error(
            error_type=error_type,
            message=error_message,
            recoverable=recoverable
        )

        # Log the graceful degradation
        logger.info(
            "Graceful degradation: Circuit breaker error handled with user-friendly message",
            extra={
                "request_id": request_id,
                "error_type": error_type.value,
                "recoverable": recoverable
            }
        )

        # Track failed request in metrics
        metrics_tracker.track_request_completed(
            request_id=request_id,
            success=False,
            duration_ms=int((time.time() - time.time()) * 1000)
        )

    except Exception as e:
        logger.error(
            f"Chat stream error: {str(e)}",
            extra={
                "request_id": request_id,
                "detected_intent": detected_intent,
                "error_type": type(e).__name__
            },
            exc_info=True
        )

        # Send error event to client
        error_type = ErrorType.OPENAI_API_ERROR
        error_message = "An unexpected error occurred. Please try again."
        recoverable = True

        # T046: Enhanced error handling for create_todo MCP tool failures (User Story 1)
        # T054: Enhanced error handling for list_todos MCP tool failures (User Story 2)
        # Provide user-friendly error messages specific to todo operations
        error_str = str(e).lower()

        # Check if error is related to create_todo operation
        is_create_operation = (detected_intent == "CREATE" or
                              "create_todo" in error_str or
                              "create" in error_str)

        # T054: Check if error is related to list_todos operation
        is_list_operation = (detected_intent == "LIST" or
                            "list_todos" in error_str or
                            ("list" in error_str and "todo" in error_str))

        # T064: Check if error is related to update_todo operation (User Story 3)
        is_update_operation = (detected_intent == "UPDATE" or
                              "update_todo" in error_str or
                              ("update" in error_str and "todo" in error_str))

        # T075: Check if error is related to delete_todo operation (User Story 4)
        is_delete_operation = (detected_intent == "DELETE" or
                              "delete_todo" in error_str or
                              ("delete" in error_str and "todo" in error_str))

        # MCP connection/server errors
        if "mcp" in error_str or "connection" in error_str:
            error_type = ErrorType.MCP_CONNECTION_ERROR
            if is_create_operation:
                error_message = "Unable to create your todo - the todo service is currently unavailable. Please try again in a moment."
            elif is_list_operation:
                error_message = "Unable to fetch your todos - the todo service is currently unavailable. Please try again in a moment."
            elif is_update_operation:
                error_message = "Unable to update your todo - the todo service is currently unavailable. Please try again in a moment."
            elif is_delete_operation:
                error_message = "Unable to delete your todo - the todo service is currently unavailable. Please try again in a moment."
            else:
                error_message = "Failed to connect to the todo service. Please try again."

        # Timeout errors
        elif "timeout" in error_str:
            error_type = ErrorType.TIMEOUT
            if is_create_operation:
                error_message = "Creating your todo is taking longer than expected. Please try again."
            elif is_list_operation:
                error_message = "Fetching your todos is taking longer than expected. Please try again."
            elif is_update_operation:
                error_message = "Updating your todo is taking longer than expected. Please try again."
            elif is_delete_operation:
                error_message = "Deleting your todo is taking longer than expected. Please try again."
            else:
                error_message = "Request timed out. Please try again."

        # Rate limit errors
        elif "rate limit" in error_str or "rate_limit_exceeded" in error_str or "tokens per day" in error_str:
            error_type = ErrorType.OPENAI_API_ERROR
            recoverable = True

            # Best-effort parse of "Please try again in 3m33.408s"
            wait_match = re.search(
                r"try again in\\s+(?:(?P<hours>\\d+)h)?(?:(?P<minutes>\\d+)m)?(?P<seconds>\\d+(?:\\.\\d+)?)s",
                error_str,
            )
            if wait_match:
                hours = int(wait_match.group("hours") or 0)
                minutes = int(wait_match.group("minutes") or 0)
                seconds = float(wait_match.group("seconds") or 0.0)
                wait_seconds = int(hours * 3600 + minutes * 60 + seconds)
                wait_hint = f"{wait_seconds}s" if wait_seconds else "a moment"
            else:
                wait_hint = "a moment"

            error_message = (
                "The AI service hit a temporary limit. "
                f"Please try again in {wait_hint}."
            )

        # Tool execution errors (MCP tool failed)
        elif "tool" in error_str and ("failed" in error_str or "error" in error_str):
            error_type = ErrorType.TOOL_EXECUTION_FAILED
            if is_create_operation:
                error_message = "Failed to create your todo. The task details may be invalid or the database is unavailable. Please check your input and try again."
            elif is_list_operation:
                error_message = "Failed to retrieve your todos. The database may be unavailable. Please try again."
            elif is_update_operation:
                error_message = "Failed to update your todo. The todo may not exist or the update parameters are invalid. Please check and try again."
            elif is_delete_operation:
                error_message = "Failed to delete your todo. The todo may not exist or the database is unavailable. Please check and try again."
            else:
                error_message = "Tool execution failed. Please try again."

        # Invalid arguments (validation errors)
        elif "invalid" in error_str or "validation" in error_str:
            error_type = ErrorType.INVALID_TOOL_ARGUMENTS
            if is_create_operation:
                error_message = "Unable to create todo - the task details couldn't be processed. Please try rephrasing your request with clear title and due date."
            elif is_list_operation:
                error_message = "Unable to list todos - the filter parameters couldn't be processed. Please try rephrasing your query (e.g., 'show my todos', 'what's due today')."
            elif is_update_operation:
                error_message = "Unable to update todo - the update parameters couldn't be processed. Please specify which todo to update and what changes to make (e.g., 'mark task #5 as complete')."
            elif is_delete_operation:
                error_message = "Unable to delete todo - the deletion parameters couldn't be processed. Please specify which todo to delete (e.g., 'delete task #5', 'remove the shopping task')."
            else:
                error_message = "Invalid request format. Please try rephrasing."
            recoverable = True  # User can fix and retry

        # Database errors
        elif "database" in error_str or "db" in error_str or "constraint" in error_str:
            error_type = ErrorType.TOOL_EXECUTION_FAILED
            if is_create_operation:
                error_message = "Unable to save your todo - database error occurred. Please try again."
            elif is_list_operation:
                error_message = "Unable to retrieve your todos - database error occurred. Please try again."
            elif is_update_operation:
                error_message = "Unable to update your todo - database error occurred. Please try again."
            elif is_delete_operation:
                error_message = "Unable to delete your todo - database error occurred. Please try again."
            else:
                error_message = "Database error occurred. Please try again."

        # Generic errors for create operations
        elif is_create_operation:
            error_message = "Sorry, I couldn't create your todo. Please try again or rephrase your request."

        # T054: Generic errors for list operations
        elif is_list_operation:
            error_message = "Sorry, I couldn't fetch your todo list. Please try again or rephrase your request."

        # T064: Generic errors for update operations (User Story 3)
        elif is_update_operation:
            error_message = "Sorry, I couldn't update your todo. Please make sure you specify which todo to update and try again."

        # T075: Generic errors for delete operations (User Story 4)
        elif is_delete_operation:
            error_message = "Sorry, I couldn't delete your todo. Please make sure you specify which todo to delete and try again."

        # Log the specific error handling decision
        logger.info(
            "Error categorized for user response",
            extra={
                "request_id": request_id,
                "detected_intent": detected_intent,
                "error_type": error_type.value,
                "is_create_operation": is_create_operation,
                "is_list_operation": is_list_operation,
                "is_update_operation": is_update_operation,
                "is_delete_operation": is_delete_operation,
                "recoverable": recoverable
            }
        )

        yield stream_builder.add_error(
            error_type=error_type,
            message=error_message,
            recoverable=recoverable
        )

        # Still send done event to close the stream
        yield stream_builder.add_done(
            final_output="Error occurred during processing",
            success=False
        )


@router.post(
    "/stream",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Successful streaming response",
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
        },
        422: {
            "description": "Validation error",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
    summary="Stream conversational todo operations",
    description="""
    Accepts natural language input and streams agent reasoning, tool calls,
    and responses in real-time using Server-Sent Events (SSE).

    The response follows the ChatKit protocol with event types:
    - thinking: Agent reasoning and intent extraction
    - tool_call: MCP tool invocation with arguments
    - response_delta: Incremental response text
    - error: Error events with recovery information
    - done: Final event indicating stream completion

    T013: Uses app.state.mcp_server for agent initialization with MCP tools
    """,
)
async def stream_chat(chat_request: ChatRequest, request: Request) -> StreamingResponse:
    """
    POST /chat/stream endpoint for natural language todo operations.

    This endpoint implements the ChatKit streaming protocol, converting natural
    language requests into structured MCP tool calls via the TodoAgent.

    T013: Retrieves app.state.mcp_server and passes to agent initialization

    Args:
        chat_request: ChatRequest containing the user's message and optional request_id
        request: FastAPI Request object (for accessing app.state)

    Returns:
        StreamingResponse: SSE stream with media_type="text/event-stream"

    Raises:
        HTTPException: On validation errors or internal failures

    Example:
        Request:
            POST /chat/stream
            {"message": "Remind me to buy eggs tomorrow at 3pm"}

        Response (SSE):
            event: thinking
            data: {"content": "User wants to create a todo..."}

            event: tool_call
            data: {"tool_name": "create_todo", "arguments": {...}, "status": "in_progress"}

            event: response_delta
            data: {"delta": "I've created", "accumulated": "I've created"}

            event: done
            data: {"final_output": "...", "tools_called": ["create_todo"], "success": true}
    """
    # T030: Extract context metadata from ChatRequest
    # Generate request_id if not provided
    request_id = chat_request.request_id or str(uuid.uuid4())

    # Generate thread_id if not provided (for conversation tracking)
    thread_id = chat_request.thread_id or f"thread_{uuid.uuid4()}"

    # Create context metadata dictionary for observability
    context_metadata = {
        "request_id": request_id,
        "thread_id": thread_id,
        "timestamp": time.time()
    }

    logger.info(
        "Received chat stream request",
        extra={
            "request_id": request_id,
            "thread_id": thread_id,
            "message_preview": chat_request.message[:50] + "..." if len(chat_request.message) > 50 else chat_request.message
        }
    )

    try:
        # T013: Get MCP server instance from app.state
        # This will be None if MCP connection failed during startup (degraded mode)
        mcp_server = getattr(request.app.state, 'mcp_server', None)

        if mcp_server is None:
            logger.warning(
                "MCP server not available - degraded mode",
                extra={
                    "request_id": request_id,
                    "degraded_mode": True
                }
            )

        # Create the streaming response
        # T030: Pass context_metadata to generator for observability
        return StreamingResponse(
            chat_stream_generator(
                message=chat_request.message,
                request_id=request_id,
                mcp_server=mcp_server,
                context_metadata=context_metadata
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Request-ID": request_id,
            },
        )

    except Exception as e:
        logger.error(
            f"Failed to create streaming response: {str(e)}",
            extra={"request_id": request_id},
            exc_info=True
        )

        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to initialize chat stream",
                "error_code": "STREAM_INITIALIZATION_FAILED",
                "request_id": request_id,
            },
        )
