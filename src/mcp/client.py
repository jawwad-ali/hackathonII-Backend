"""
MCP Client for Todo Server Integration
Handles MCPServerStdio initialization and dynamic MCP tool discovery

Uses OpenAI Agents SDK (agents.mcp.MCPServerStdio) to spawn FastMCP server as subprocess.
Includes circuit breaker and retry logic for resilience against MCP server failures.
Includes 5-second timeout for MCP operations per spec requirements (FR-017).
"""

from agents.mcp import MCPServerStdio
from typing import Optional, List
import logging
from datetime import timedelta
import asyncio

# Import resilience components
from src.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError
)
from src.resilience.retry import mcp_retry
from src.config import settings

logger = logging.getLogger(__name__)

# Global circuit breaker for MCP server
# Configuration:
# - 5 consecutive failures before opening (per FR-013)
# - 30 second recovery timeout (per CIRCUIT_BREAKER_MCP_RECOVERY_TIMEOUT)
# - 3 test calls in half-open state
_mcp_circuit_breaker = CircuitBreaker(
    name="mcp_server",
    config=CircuitBreakerConfig(
        failure_threshold=settings.CIRCUIT_BREAKER_MCP_FAILURE_THRESHOLD,
        recovery_timeout=timedelta(seconds=settings.CIRCUIT_BREAKER_MCP_RECOVERY_TIMEOUT),
        half_open_max_calls=3
    )
)


@mcp_retry
async def _initialize_mcp_connection_with_retry() -> MCPServerStdio:
    """
    Internal function to initialize MCP server connection with retry logic.

    This function is wrapped with @mcp_retry decorator for exponential backoff:
    - Max attempts: 3 (per FR-013)
    - Exponential backoff: 1s → 2s → 4s (with jitter)
    - Timeout: 5 seconds per attempt (per FR-017)

    Returns:
        MCPServerStdio: Initialized MCP server connection with stdio transport

    Raises:
        ConnectionError: If MCP server cannot be reached (after retries)
        TimeoutError: If MCP initialization exceeds timeout (after retries)
        ValueError: If configuration is invalid
    """
    logger.info("Initializing MCP server connection via stdio transport")

    try:
        # Create MCPServerStdio with subprocess parameters from settings
        # This spawns the FastMCP server as a subprocess with stdin/stdout communication
        async with asyncio.timeout(settings.MCP_SERVER_TIMEOUT):
            mcp_server = MCPServerStdio(
                name="TodoDatabaseServer",
                params={
                    "command": settings.MCP_SERVER_COMMAND,
                    "args": settings.MCP_SERVER_ARGS
                }
            )

            # Initialize the connection (spawns subprocess)
            await mcp_server.__aenter__()

            logger.info(
                f"MCP server initialized successfully (timeout: {settings.MCP_SERVER_TIMEOUT}s)"
            )

            return mcp_server

    except asyncio.TimeoutError as e:
        # Timeout handling - convert to TimeoutError for retry logic
        logger.warning(
            f"MCP server initialization timed out after {settings.MCP_SERVER_TIMEOUT}s (will retry)"
        )
        raise TimeoutError(
            f"MCP server initialization exceeded timeout of {settings.MCP_SERVER_TIMEOUT}s"
        ) from e

    except (ConnectionError, TimeoutError, OSError) as e:
        # These errors trigger retry logic
        logger.warning(f"MCP server initialization failed (will retry): {e}")
        raise

    except Exception as e:
        # Other errors (config errors, etc.) don't trigger retry
        logger.error(f"Failed to initialize MCP server: {e}")
        raise ValueError(f"Invalid MCP server configuration: {e}") from e


async def initialize_mcp_connection() -> Optional[MCPServerStdio]:
    """
    Initialize MCP server connection using MCPServerStdio with resilience.

    This function wraps MCP initialization with:
    - Circuit breaker pattern (fail-fast when MCP server is down)
    - Exponential backoff retry (3 attempts with jitter per FR-013)
    - 5-second timeout per attempt (per FR-017)

    The MCP server is spawned as a subprocess with stdio transport:
    - command: "uvx" (from MCP_SERVER_COMMAND)
    - args: ["fastmcp", "run", "src/mcp_server/server.py"] (from MCP_SERVER_ARGS)

    Returns:
        Optional[MCPServerStdio]: Initialized MCP server connection, or None if failed
            - Returns MCPServerStdio instance on success
            - Returns None on failure (enables degraded mode per FR-010)

    Note:
        This function NEVER raises exceptions to enable graceful degraded mode.
        Always check for None return value before using the connection.

    Example:
        >>> mcp_server = await initialize_mcp_connection()
        >>> if mcp_server is None:
        ...     logger.error("MCP server unavailable - entering degraded mode")
        ...     return {"error": "Database temporarily unavailable"}
    """
    try:
        # Circuit breaker wraps retry logic
        mcp_server = await _mcp_circuit_breaker.call(_initialize_mcp_connection_with_retry)
        return mcp_server

    except CircuitBreakerError as e:
        logger.error(f"Circuit breaker open for MCP server: {e}")
        # Return None instead of raising to enable degraded mode
        return None

    except Exception as e:
        logger.error(f"MCP server initialization failed: {e}")
        # Return None instead of raising to enable degraded mode
        return None


async def get_discovered_tools(mcp_server: MCPServerStdio) -> List[str]:
    """
    Get list of tools discovered from the MCP server.

    This function queries the MCP server for available tools after connection.
    Tools are automatically discovered via the MCP protocol's tools/list method.

    Args:
        mcp_server: Initialized MCPServerStdio connection

    Returns:
        List[str]: List of discovered tool names (e.g., ['create_todo', 'list_todos', ...])

    Raises:
        RuntimeError: If tool discovery fails

    Example:
        >>> mcp_server = await initialize_mcp_connection()
        >>> if mcp_server:
        ...     tools = await get_discovered_tools(mcp_server)
        ...     print(f"Discovered {len(tools)} tools: {tools}")
    """
    logger.info("Discovering tools from MCP server")

    try:
        # Query MCP server for available tools
        # The MCPServerStdio provides a tools property or list_tools() method
        # depending on the SDK version
        tools = await mcp_server.list_tools()

        tool_names = [tool.name for tool in tools]

        logger.info(f"Discovered {len(tool_names)} tools from MCP server: {tool_names}")

        # Validate expected tools
        expected_tools = ["create_todo", "list_todos", "update_todo", "search_todos", "delete_todo"]
        missing_tools = set(expected_tools) - set(tool_names)

        if missing_tools:
            logger.warning(f"Expected tools missing from MCP server: {missing_tools}")

        return tool_names

    except Exception as e:
        logger.error(f"MCP tool discovery failed: {e}")
        raise RuntimeError(f"Failed to discover MCP tools: {e}") from e


def get_mcp_circuit_breaker() -> CircuitBreaker:
    """
    Get the MCP server circuit breaker for monitoring.

    This function provides access to the circuit breaker instance for:
    - Health check endpoints
    - Monitoring dashboards
    - Manual circuit breaker reset (administrative use)

    Returns:
        CircuitBreaker: The global MCP server circuit breaker

    Example:
        >>> breaker = get_mcp_circuit_breaker()
        >>> state = breaker.get_state()
        >>> print(f"Circuit state: {state.state.value}")
        >>> print(f"Failure count: {state.failure_count}")
    """
    return _mcp_circuit_breaker
