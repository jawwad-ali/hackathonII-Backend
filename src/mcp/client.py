"""
MCP Client for Todo Server Integration
Handles RunnerContext initialization and dynamic MCP tool discovery

Includes circuit breaker and retry logic for resilience against MCP server failures.
Includes timeout handling for MCP operations (30s default).
"""

from agents_mcp import RunnerContext
from mcp_agent.config import MCPSettings, get_settings
from typing import List, Dict, Any
import logging
from pathlib import Path
from datetime import timedelta
import asyncio

# Import resilience components
from src.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError
)
from src.resilience.retry import mcp_retry

logger = logging.getLogger(__name__)

# MCP Server timeout configuration (T083)
# Default timeout for MCP operations: 30 seconds
MCP_TIMEOUT_SECONDS = 30

# Global circuit breaker for MCP server
# Configuration:
# - 5 consecutive failures before opening
# - 30 second recovery timeout
# - 3 test calls in half-open state
_mcp_circuit_breaker = CircuitBreaker(
    name="mcp_server",
    config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=timedelta(seconds=30),
        half_open_max_calls=3
    )
)


def get_mcp_config_path() -> Path:
    """
    Get the path to the mcp_agent.config.yaml file.

    Returns:
        Path: Absolute path to the config file
    """
    # Config file is at repository root
    return Path(__file__).parent.parent.parent / "mcp_agent.config.yaml"


@mcp_retry
async def _initialize_mcp_context_with_retry() -> RunnerContext:
    """
    Internal function to initialize MCP context with retry logic.

    This function is wrapped with @mcp_retry decorator for exponential backoff:
    - Max attempts: 5
    - Exponential backoff: 1s → 2s → 4s → 8s → 16s (with jitter)
    - Max wait: 30 seconds
    - Timeout: 30 seconds per attempt (T083)

    Raises:
        FileNotFoundError: If mcp_agent.config.yaml is not found
        ValueError: If config file is invalid or missing required fields
        ConnectionError: If MCP server cannot be reached (after retries)
        TimeoutError: If MCP initialization exceeds timeout (after retries)
    """
    config_path = get_mcp_config_path()

    if not config_path.exists():
        raise FileNotFoundError(
            f"MCP config file not found at {config_path}. "
            "Ensure mcp_agent.config.yaml exists in the repository root."
        )

    logger.info(f"Loading MCP configuration from {config_path}")

    try:
        # T083: Wrap MCP initialization with timeout to prevent hanging
        # This ensures the operation completes within 30 seconds or raises TimeoutError
        async with asyncio.timeout(MCP_TIMEOUT_SECONDS):
            # Load configuration using agents_mcp config loader
            settings = get_settings(str(config_path))
            mcp_config: MCPSettings = settings.mcp

            # Create RunnerContext with the loaded configuration
            context = RunnerContext(mcp_config=mcp_config)

            logger.info(
                f"MCP context initialized successfully with servers: "
                f"{list(mcp_config.mcp.servers.keys())}"
            )

            return context

    except asyncio.TimeoutError as e:
        # T083: Timeout handling - convert to TimeoutError for retry logic
        logger.warning(
            f"MCP context initialization timed out after {MCP_TIMEOUT_SECONDS}s (will retry)"
        )
        raise TimeoutError(
            f"MCP server initialization exceeded timeout of {MCP_TIMEOUT_SECONDS}s"
        ) from e

    except (ConnectionError, TimeoutError, OSError) as e:
        # These errors trigger retry logic
        logger.warning(f"MCP context initialization failed (will retry): {e}")
        raise

    except Exception as e:
        # Other errors (config errors, etc.) don't trigger retry
        logger.error(f"Failed to initialize MCP context: {e}")
        raise ValueError(
            f"Invalid MCP configuration in {config_path}: {e}"
        ) from e


async def initialize_mcp_context() -> RunnerContext:
    """
    Initialize RunnerContext using mcp_agent.config.yaml with resilience.

    This function wraps MCP initialization with:
    - Circuit breaker pattern (fail-fast when MCP server is down)
    - Exponential backoff retry (5 attempts with jitter)

    The config file defines the todo_server MCP server with:
    - command: "uvx"
    - args: ["fastmcp", "run", "todo_server.py"]
    - env: DATABASE_URL and other environment variables

    Returns:
        RunnerContext: Initialized context for MCP server communication

    Raises:
        CircuitBreakerError: If circuit breaker is open (MCP server unavailable)
        FileNotFoundError: If mcp_agent.config.yaml is not found
        ValueError: If config file is invalid or missing required fields
        ConnectionError: If MCP server cannot be reached (after retries)

    Example:
        >>> try:
        ...     context = await initialize_mcp_context()
        ... except CircuitBreakerError:
        ...     logger.error("MCP server circuit breaker open - service unavailable")
        ...     # Return cached data or fallback response
    """
    try:
        # Circuit breaker wraps retry logic
        return await _mcp_circuit_breaker.call(_initialize_mcp_context_with_retry)

    except CircuitBreakerError as e:
        logger.error(f"Circuit breaker open for MCP server: {e}")
        # Re-raise with context for caller to handle
        raise

    except Exception as e:
        logger.error(f"MCP context initialization failed: {e}")
        raise


async def discover_mcp_tools(context: RunnerContext) -> List[str]:
    """
    Dynamically discover available MCP tools from the todo_server.

    This function identifies the MCP servers configured in the context
    and returns their names for use in agent initialization.

    In agents_mcp, tool discovery happens automatically when an agent is
    initialized with mcp_servers parameter. The agent connects to each
    specified MCP server and discovers available tools at runtime.

    The discovered tools (create_todo, list_todos, update_todo, delete_todo)
    will be automatically registered with the TodoAgent when the agent is
    created with mcp_servers=["todo_server"].

    Args:
        context: Initialized RunnerContext with MCP server configuration

    Returns:
        List[str]: List of MCP server names available for tool discovery

    Raises:
        ValueError: If no MCP servers are configured
        RuntimeError: If tool discovery configuration fails

    Example:
        >>> context = initialize_mcp_context()
        >>> servers = await discover_mcp_tools(context)
        >>> print(servers)
        ['todo_server']

    Note:
        The actual tool discovery and registration happens when creating
        an Agent with mcp_servers parameter:

        >>> agent = Agent(
        ...     name="TodoAgent",
        ...     instructions="...",
        ...     mcp_servers=["todo_server"]  # Triggers automatic tool discovery
        ... )
    """
    logger.info("Starting MCP tool discovery from todo_server")

    try:
        # Get server names from config
        server_names = list(context.mcp_config.mcp.servers.keys())

        if not server_names:
            raise ValueError("No MCP servers configured in context")

        logger.info(f"Discovered MCP servers: {server_names}")

        # Validate that todo_server is configured
        if "todo_server" not in server_names:
            logger.warning(
                f"Expected 'todo_server' in MCP config, but found: {server_names}"
            )

        # Document expected tools from todo_server for reference
        expected_tools = [
            "create_todo",
            "list_todos",
            "update_todo",
            "delete_todo"
        ]

        logger.info(
            f"MCP servers ready for tool discovery. "
            f"Expected tools from todo_server: {expected_tools}"
        )

        # Return server names - these will be passed to Agent(mcp_servers=...)
        # which triggers automatic tool discovery and registration
        return server_names

    except Exception as e:
        logger.error(f"MCP tool discovery failed: {e}")
        raise RuntimeError(
            f"Failed to configure MCP tool discovery: {e}"
        ) from e


async def get_runner_context() -> RunnerContext:
    """
    Get a configured RunnerContext for use with TodoAgent (with resilience).

    This is a convenience function that combines initialization and
    returns a ready-to-use context for running the agent.

    Includes circuit breaker and retry logic for resilience.

    Returns:
        RunnerContext: Ready-to-use context with MCP server configuration

    Raises:
        CircuitBreakerError: If circuit breaker is open (MCP server unavailable)
        Other exceptions from initialize_mcp_context()

    Example:
        >>> from agents_mcp import Runner
        >>> from agents.todo_agent import create_todo_agent
        >>>
        >>> agent = create_todo_agent()
        >>> try:
        ...     context = await get_runner_context()
        ...     result = await Runner.run(agent, input="Add buy eggs to my list", context=context)
        ... except CircuitBreakerError:
        ...     # Handle MCP server unavailability
        ...     return {"error": "MCP service temporarily unavailable"}
    """
    return await initialize_mcp_context()


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
