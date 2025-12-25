"""
API Routes for AI Agent Orchestrator

Implements the ChatKit streaming endpoint for natural language todo operations.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import logging
import time
import uuid

from agents import Runner

from src.api.schemas import ChatRequest, ErrorResponse
from src.streaming.chatkit import StreamBuilder, ErrorType, map_agent_event_to_chatkit
from src.agents.todo_agent import create_todo_agent
from src.mcp.client import get_runner_context, discover_mcp_tools
from src.observability.metrics import metrics_tracker

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/chat", tags=["chat"])


async def chat_stream_generator(
    message: str,
    request_id: str
) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE events for the chat stream.

    Calls Runner.run_streamed() with TodoAgent and MCP context to execute
    natural language todo operations and stream the results in ChatKit format.

    Args:
        message: Sanitized user message from ChatRequest
        request_id: Request ID for correlation and logging

    Yields:
        SSE formatted event strings (thinking, tool_call, response_delta, error, done)

    Note:
        Event mapping from OpenAI Agents SDK to ChatKit format will be enhanced
        in T028. This implementation provides basic streaming functionality.
    """
    stream_builder = StreamBuilder()

    try:
        # Log request received
        logger.info(
            f"Chat stream started",
            extra={
                "request_id": request_id,
                "message_length": len(message)
            }
        )

        # Initialize MCP context and discover tools
        context = get_runner_context()
        mcp_servers = await discover_mcp_tools(context)

        logger.info(
            f"MCP context initialized",
            extra={
                "request_id": request_id,
                "mcp_servers": mcp_servers
            }
        )

        # Create TodoAgent with MCP tools
        agent = create_todo_agent(mcp_servers=mcp_servers)

        logger.info(
            f"TodoAgent created",
            extra={
                "request_id": request_id,
                "agent_name": agent.name
            }
        )

        # Stream initial thinking event
        yield stream_builder.add_thinking(
            "Processing your request and analyzing intent..."
        )

        # Run agent with streaming
        result = Runner.run_streamed(
            agent=agent,
            input=message,
            context=context
        )

        logger.info(
            f"Runner.run_streamed() initiated",
            extra={"request_id": request_id}
        )

        # Process stream events from OpenAI Agents SDK
        # Map events to ChatKit SSE format using enhanced mapper (T028)
        # Track detected intent for User Story 1 (Create operations)
        detected_intent = None
        tool_start_times = {}  # Track tool execution start times for duration calculation

        async for event in result.stream_events():
            event_type = type(event).__name__

            logger.debug(
                f"Stream event received: {event_type}",
                extra={
                    "request_id": request_id,
                    "event_type": event_type
                }
            )

            # T045: Detect CREATE intent when create_todo tool is called
            # T047: Stream thinking event showing parameter extraction reasoning
            # T051: Log mcp_tool_called event with create_todo details
            if hasattr(event, 'tool_name'):
                tool_name = event.tool_name

                # Track tool invocation start time (for duration calculation)
                if not hasattr(event, 'result'):
                    tool_start_times[tool_name] = time.time()

                if tool_name == "create_todo" and detected_intent is None:
                    detected_intent = "CREATE"
                    tool_args = getattr(event, 'arguments', {})

                    logger.info(
                        f"CREATE intent detected - create_todo tool called",
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

                # T051: Log mcp_tool_called event when tool execution completes
                # Detect tool completion by checking for 'result' attribute
                if hasattr(event, 'result'):
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

                    # Log mcp_tool_called event for observability (FR-011)
                    logger.info(
                        f"MCP tool execution completed",
                        extra={
                            "event": "mcp_tool_called",
                            "request_id": request_id,
                            "tool_name": tool_name,
                            "tool_arguments": getattr(event, 'arguments', {}),
                            "duration_ms": tool_duration_ms,
                            "success": True
                        }
                    )

            # Use comprehensive event mapper to convert SDK events to ChatKit SSE
            sse_event = map_agent_event_to_chatkit(event, stream_builder)

            # Yield the formatted SSE event if mapping produced output
            if sse_event:
                yield sse_event

        # Get final result
        final_result = result.result()

        logger.info(
            f"Agent execution completed",
            extra={
                "request_id": request_id,
                "tools_called": stream_builder.tools_called
            }
        )

        # Send done event
        final_output = stream_builder.accumulated_text or "Request processed successfully."
        yield stream_builder.add_done(
            final_output=final_output,
            success=True
        )

        logger.info(
            f"Chat stream completed successfully",
            extra={
                "request_id": request_id,
                "detected_intent": detected_intent,
                "tools_called": stream_builder.tools_called,
                "final_output_length": len(final_output)
            }
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
        error_type = ErrorType.GEMINI_API_ERROR
        error_message = "An unexpected error occurred. Please try again."
        recoverable = True

        # T046: Enhanced error handling for create_todo MCP tool failures (User Story 1)
        # Provide user-friendly error messages specific to todo creation
        error_str = str(e).lower()

        # Check if error is related to create_todo operation
        is_create_operation = (detected_intent == "CREATE" or
                              "create_todo" in error_str or
                              "create" in error_str)

        # MCP connection/server errors
        if "mcp" in error_str or "connection" in error_str:
            error_type = ErrorType.MCP_CONNECTION_ERROR
            if is_create_operation:
                error_message = "Unable to create your todo - the todo service is currently unavailable. Please try again in a moment."
            else:
                error_message = "Failed to connect to the todo service. Please try again."

        # Timeout errors
        elif "timeout" in error_str:
            error_type = ErrorType.TIMEOUT
            if is_create_operation:
                error_message = "Creating your todo is taking longer than expected. Please try again."
            else:
                error_message = "Request timed out. Please try again."

        # Tool execution errors (MCP tool failed)
        elif "tool" in error_str and ("failed" in error_str or "error" in error_str):
            error_type = ErrorType.TOOL_EXECUTION_FAILED
            if is_create_operation:
                error_message = "Failed to create your todo. The task details may be invalid or the database is unavailable. Please check your input and try again."
            else:
                error_message = "Tool execution failed. Please try again."

        # Invalid arguments (validation errors)
        elif "invalid" in error_str or "validation" in error_str:
            error_type = ErrorType.INVALID_TOOL_ARGUMENTS
            if is_create_operation:
                error_message = "Unable to create todo - the task details couldn't be processed. Please try rephrasing your request with clear title and due date."
            else:
                error_message = "Invalid request format. Please try rephrasing."
            recoverable = True  # User can fix and retry

        # Database errors
        elif "database" in error_str or "db" in error_str or "constraint" in error_str:
            error_type = ErrorType.TOOL_EXECUTION_FAILED
            if is_create_operation:
                error_message = "Unable to save your todo - database error occurred. Please try again."
            else:
                error_message = "Database error occurred. Please try again."

        # Generic errors for create operations
        elif is_create_operation:
            error_message = "Sorry, I couldn't create your todo. Please try again or rephrase your request."

        # Log the specific error handling decision
        logger.info(
            f"Error categorized for user response",
            extra={
                "request_id": request_id,
                "detected_intent": detected_intent,
                "error_type": error_type.value,
                "is_create_operation": is_create_operation,
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
    """,
)
async def stream_chat(request: ChatRequest) -> StreamingResponse:
    """
    POST /chat/stream endpoint for natural language todo operations.

    This endpoint implements the ChatKit streaming protocol, converting natural
    language requests into structured MCP tool calls via the TodoAgent.

    Args:
        request: ChatRequest containing the user's message and optional request_id

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
    # Generate or use provided request ID
    request_id = request.request_id or str(uuid.uuid4())

    logger.info(
        f"Received chat stream request",
        extra={
            "request_id": request_id,
            "message_preview": request.message[:50] + "..." if len(request.message) > 50 else request.message
        }
    )

    try:
        # Create the streaming response
        return StreamingResponse(
            chat_stream_generator(
                message=request.message,
                request_id=request_id
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
