"""
API Routes for AI Agent Orchestrator

Implements the ChatKit streaming endpoint for natural language todo operations.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import logging
import uuid

from agents_mcp import Runner

from src.api.schemas import ChatRequest, ErrorResponse
from src.streaming.chatkit import StreamBuilder, ErrorType, map_agent_event_to_chatkit
from src.agents.todo_agent import create_todo_agent
from src.mcp.client import get_runner_context, discover_mcp_tools

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
        async for event in result.stream_events():
            event_type = type(event).__name__

            logger.debug(
                f"Stream event received: {event_type}",
                extra={
                    "request_id": request_id,
                    "event_type": event_type
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
                "tools_called": stream_builder.tools_called,
                "final_output_length": len(final_output)
            }
        )

    except Exception as e:
        logger.error(
            f"Chat stream error: {str(e)}",
            extra={"request_id": request_id},
            exc_info=True
        )

        # Send error event to client
        error_type = ErrorType.GEMINI_API_ERROR
        error_message = "An unexpected error occurred. Please try again."

        # Determine specific error type based on exception
        if "MCP" in str(e) or "mcp" in str(e).lower():
            error_type = ErrorType.MCP_CONNECTION_ERROR
            error_message = "Failed to connect to the todo service. Please try again."
        elif "timeout" in str(e).lower():
            error_type = ErrorType.TIMEOUT
            error_message = "Request timed out. Please try again."

        yield stream_builder.add_error(
            error_type=error_type,
            message=error_message,
            recoverable=True
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
