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

    Supports multiple transport types via MCP_TRANSPORT_TYPE environment variable:
    - "stdio": Local subprocess with stdin/stdout (default, recommended for development)
    - "sse": HTTP with Server-Sent Events (placeholder for future production deployment)

    Returns:
        MCPServerStdio: Initialized MCP server connection with configured transport

    Raises:
        ConnectionError: If MCP server cannot be reached (after retries)
        TimeoutError: If MCP initialization exceeds timeout (after retries)
        ValueError: If configuration is invalid or transport type unsupported
    """
    transport_type = settings.MCP_TRANSPORT_TYPE
    logger.info(f"Initializing MCP server connection via {transport_type} transport")

    try:
        async with asyncio.timeout(settings.MCP_SERVER_TIMEOUT):
            # Conditional transport initialization based on MCP_TRANSPORT_TYPE
            if transport_type == "stdio":
                # stdio transport: Local subprocess with stdin/stdout communication
                # No network binding - inherently localhost-only and secure
                mcp_server = MCPServerStdio(
                    name="TodoDatabaseServer",
                    params={
                        "command": settings.MCP_SERVER_COMMAND,
                        "args": settings.MCP_SERVER_ARGS
                    },
                    # OpenAI Agents SDK defaults this to 5s; make it configurable so
                    # slower cold starts (imports, venv/uv wrappers, etc.) don't
                    # fail MCP initialization/tool discovery.
                    client_session_timeout_seconds=float(settings.MCP_SERVER_TIMEOUT),
                )

                # Initialize the connection (spawns subprocess)
                await mcp_server.__aenter__()

                logger.info(
                    f"MCP server initialized successfully via stdio (timeout: {settings.MCP_SERVER_TIMEOUT}s)"
                )

                return mcp_server

            elif transport_type == "sse":
                # SSE transport: HTTP with Server-Sent Events (future implementation)
                #
                # SECURITY REQUIREMENT: When implementing SSE transport, the MCP server
                # MUST bind to localhost only (127.0.0.1), NOT 0.0.0.0 or public IPs.
                # This prevents unauthorized network access to database operations.
                #
                # Example implementation (not yet available in OpenAI Agents SDK):
                # ```python
                # from agents.mcp import MCPServerSse  # Not yet implemented
                #
                # mcp_server = MCPServerSse(
                #     name="TodoDatabaseServer",
                #     params={
                #         "url": "http://127.0.0.1:8001",  # MUST be localhost only
                #         "timeout": settings.MCP_SERVER_TIMEOUT
                #     }
                # )
                # await mcp_server.__aenter__()
                # ```
                #
                # TODO: Implement SSE transport when MCPServerSse is available
                # TODO: Add localhost-only binding validation (127.0.0.1, not 0.0.0.0)
                # TODO: Add TLS/SSL configuration for production deployment
                # TODO: Update .env.example with SSE configuration variables
                raise NotImplementedError(
                    "SSE transport is not yet implemented. "
                    "Please use MCP_TRANSPORT_TYPE=stdio or wait for MCPServerSse support in OpenAI Agents SDK."
                )

            else:
                # Invalid transport type (should be caught by config validation)
                raise ValueError(
                    f"Unsupported MCP transport type: '{transport_type}'. "
                    f"Valid options: 'stdio', 'sse'"
                )

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

    except NotImplementedError as e:
        # SSE transport not implemented - don't retry
        logger.error(f"Transport type not supported: {e}")
        raise ValueError(str(e)) from e

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
