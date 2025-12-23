"""
MCP Client for Todo Server Integration
Handles RunnerContext initialization and dynamic MCP tool discovery
"""

from agents_mcp import RunnerContext
from mcp_agent.config import MCPSettings, load_config
from typing import List, Dict, Any
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_mcp_config_path() -> Path:
    """
    Get the path to the mcp_agent.config.yaml file.

    Returns:
        Path: Absolute path to the config file
    """
    # Config file is at repository root
    return Path(__file__).parent.parent.parent / "mcp_agent.config.yaml"


def initialize_mcp_context() -> RunnerContext:
    """
    Initialize RunnerContext using mcp_agent.config.yaml.

    This function loads the MCP configuration from the YAML file and creates
    a RunnerContext that will be used to connect the TodoAgent to the
    external FastMCP server handling PostgreSQL + SQLModel CRUD operations.

    The config file defines the todo_server MCP server with:
    - command: "uvx"
    - args: ["fastmcp", "run", "todo_server.py"]
    - env: DATABASE_URL and other environment variables

    Returns:
        RunnerContext: Initialized context for MCP server communication

    Raises:
        FileNotFoundError: If mcp_agent.config.yaml is not found
        ValueError: If config file is invalid or missing required fields
    """
    config_path = get_mcp_config_path()

    if not config_path.exists():
        raise FileNotFoundError(
            f"MCP config file not found at {config_path}. "
            "Ensure mcp_agent.config.yaml exists in the repository root."
        )

    logger.info(f"Loading MCP configuration from {config_path}")

    try:
        # Load configuration using agents_mcp config loader
        mcp_config: MCPSettings = load_config(str(config_path))

        # Create RunnerContext with the loaded configuration
        context = RunnerContext(mcp_config=mcp_config)

        logger.info(
            f"MCP context initialized successfully with servers: "
            f"{list(mcp_config.mcp.servers.keys())}"
        )

        return context

    except Exception as e:
        logger.error(f"Failed to initialize MCP context: {e}")
        raise ValueError(
            f"Invalid MCP configuration in {config_path}: {e}"
        ) from e


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


def get_runner_context() -> RunnerContext:
    """
    Get a configured RunnerContext for use with TodoAgent.

    This is a convenience function that combines initialization and
    returns a ready-to-use context for running the agent.

    Returns:
        RunnerContext: Ready-to-use context with MCP server configuration

    Example:
        >>> from agents_mcp import Runner
        >>> from agents.todo_agent import create_todo_agent
        >>>
        >>> agent = create_todo_agent()
        >>> context = get_runner_context()
        >>> result = await Runner.run(agent, input="Add buy eggs to my list", context=context)
    """
    return initialize_mcp_context()
