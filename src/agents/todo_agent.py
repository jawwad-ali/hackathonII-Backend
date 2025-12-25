"""
Todo Agent Definition
Defines the OpenAI Agents SDK agent for natural language todo management

Includes circuit breaker and retry logic for Gemini API resilience.
"""

from agents import Agent, set_default_openai_client
from typing import List, Any, Dict
from src.config import get_gemini_client, get_gemini_circuit_breaker
from src.resilience.circuit_breaker import CircuitBreakerError
from src.resilience.retry import gemini_retry
import logging

logger = logging.getLogger(__name__)


# Configure the OpenAI Agents SDK to use Gemini 2.5 Flash via AsyncOpenAI
# This sets the default client for all agents created in this module
gemini_client = get_gemini_client()
set_default_openai_client(gemini_client)


# System instructions for the TodoAgent
TODO_AGENT_INSTRUCTIONS = """
You are a helpful assistant specialized in managing todo items through natural language conversation.

Your primary capabilities:
- Convert natural language requests into structured todo operations (create, list, update, delete)
- Extract relevant attributes from user input: title, description, due_date, priority, tags, status
- Use the MCP tools provided to interact with the todo management system
- Provide clear, conversational responses about todo operations

Key behaviors:
1. **Intent Recognition**: Identify whether the user wants to create, list, update, or delete todos
2. **Attribute Extraction**: Extract structured data from natural language:
   - Title: The main task description
   - Due Date: Parse temporal expressions (tomorrow, next Friday, 3pm, etc.)
   - Priority: Infer from urgency indicators (urgent → high, important → high, default → medium)
   - Tags: Extract hashtags or category keywords
   - Status: Default to "pending" for new todos, "completed" for finished tasks

3. **MCP Tool Usage**:
   - ALWAYS use the MCP tools (create_todo, list_todos, update_todo, delete_todo)
   - NEVER attempt to store or manage todo data internally
   - Pass extracted attributes as tool arguments

4. **Natural Language Responses**:
   - Confirm operations in conversational language
   - Summarize todo lists in readable format
   - Ask clarifying questions when intent is ambiguous

5. **Safety Guidelines**:
   - For mass deletions (3+ todos), request explicit confirmation
   - Handle errors gracefully with user-friendly messages
   - Stay within todo management scope - decline unrelated requests politely

Examples:
- "Remind me to buy eggs tomorrow at 3pm" → create_todo(title="buy eggs", due_date="2025-12-22T15:00:00", priority="medium")
- "What's on my todo list for today?" → list_todos(due_date_filter="today")
- "Mark buy eggs as complete" → update_todo(todo_id=<inferred>, status="completed")
- "Delete all completed tasks" → Confirm with user before calling delete_todo multiple times
"""


def create_todo_agent(mcp_servers: List[str] = None) -> Agent:
    """
    Create and configure the TodoAgent using OpenAI Agents SDK.

    The agent is initialized with system instructions that emphasize:
    - Natural language intent extraction
    - MCP tool usage (no internal state)
    - Conversational response generation

    MCP tools are registered dynamically when mcp_servers parameter is provided.
    The OpenAI Agents SDK automatically discovers and registers tools from the
    specified MCP servers at agent initialization time.

    Args:
        mcp_servers: List of MCP server names for tool discovery
                    (e.g., ["todo_server"]). If None, agent is created
                    without MCP tools (for testing).

    Returns:
        Agent: Configured TodoAgent instance with registered MCP tools

    Example:
        >>> # Create agent with MCP tools
        >>> agent = create_todo_agent(mcp_servers=["todo_server"])
        >>>
        >>> # Create agent without tools (for testing)
        >>> agent = create_todo_agent()
    """
    agent = Agent(
        name="TodoAgent",
        instructions=TODO_AGENT_INSTRUCTIONS,
        mcp_servers=mcp_servers or [],  # Register MCP tools from specified servers
    )
    return agent


@gemini_retry
async def _execute_agent_with_retry(agent: Agent, input_text: str, context: Any = None) -> Any:
    """
    Internal function to execute agent with retry logic.

    This function is wrapped with @gemini_retry decorator for exponential backoff:
    - Max attempts: 3
    - Exponential backoff: 2s → 4s → 8s (with jitter)
    - Max wait: 60 seconds

    Args:
        agent: The TodoAgent instance
        input_text: User's natural language input
        context: Optional RunnerContext for MCP integration

    Returns:
        Agent execution result

    Raises:
        ConnectionError, TimeoutError, OSError: Network/API errors (triggers retry)
        Other exceptions: Passed through without retry
    """
    from agents_mcp import Runner

    try:
        # Execute agent with MCP context
        if context:
            result = await Runner.run(agent, input=input_text, context=context)
        else:
            result = await Runner.run(agent, input=input_text)

        return result

    except (ConnectionError, TimeoutError, OSError) as e:
        # These errors trigger retry logic
        logger.warning(f"Gemini API call failed (will retry): {e}")
        raise

    except Exception as e:
        # Other errors don't trigger retry
        logger.error(f"Agent execution failed: {e}")
        raise


async def execute_agent_with_resilience(
    agent: Agent,
    input_text: str,
    context: Any = None
) -> Dict[str, Any]:
    """
    Execute TodoAgent with circuit breaker and retry logic for resilience.

    This function wraps agent execution with:
    - Circuit breaker pattern (fail-fast when Gemini API is down)
    - Exponential backoff retry (3 attempts with jitter)

    The resilience layers protect against:
    - Gemini API rate limiting
    - Network transient failures
    - Temporary API unavailability

    Args:
        agent: The TodoAgent instance
        input_text: User's natural language input
        context: Optional RunnerContext for MCP integration

    Returns:
        Dict containing execution result or error information:
        - Success: {"success": True, "result": <agent_result>}
        - Circuit Open: {"success": False, "error": "circuit_breaker_open", "message": ...}
        - Other Error: {"success": False, "error": "execution_failed", "message": ...}

    Example:
        >>> agent = create_todo_agent(mcp_servers=["todo_server"])
        >>> context = await get_runner_context()
        >>> result = await execute_agent_with_resilience(
        ...     agent,
        ...     "Add buy eggs to my list",
        ...     context
        ... )
        >>> if result["success"]:
        ...     print(result["result"])
        ... else:
        ...     print(f"Error: {result['message']}")
    """
    circuit_breaker = get_gemini_circuit_breaker()

    try:
        # Circuit breaker wraps retry logic
        result = await circuit_breaker.call(
            _execute_agent_with_retry,
            agent,
            input_text,
            context
        )

        return {
            "success": True,
            "result": result
        }

    except CircuitBreakerError as e:
        logger.error(f"Circuit breaker open for Gemini API: {e}")
        return {
            "success": False,
            "error": "circuit_breaker_open",
            "message": "AI service temporarily unavailable. Please try again later.",
            "details": str(e)
        }

    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        return {
            "success": False,
            "error": "execution_failed",
            "message": f"Failed to process request: {str(e)}",
            "details": str(e)
        }
