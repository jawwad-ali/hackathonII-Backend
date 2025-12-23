"""
Todo Agent Definition
Defines the OpenAI Agents SDK agent for natural language todo management
"""

from agents import Agent, set_default_openai_client
from typing import List
from config import get_gemini_client


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
