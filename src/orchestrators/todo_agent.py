"""
Todo Agent Definition
Defines the OpenAI Agents SDK agent for natural language todo management

Includes circuit breaker and retry logic for Groq API resilience.
"""

from agents import (
    Agent,
    set_default_openai_client,
    set_tracing_disabled,
    OpenAIChatCompletionsModel,
    function_tool,
    ModelSettings,
)
from agents.mcp import MCPServerStdio
from typing import List, Any, Dict, Optional, Literal, Union
from src.config import get_groq_client, get_groq_circuit_breaker, settings
from src.resilience.circuit_breaker import CircuitBreakerError
from src.resilience.retry import groq_retry
import logging

logger = logging.getLogger(__name__)


# Disable OpenAI tracing to prevent 401 errors when using Groq API
# The OpenAI Agents SDK has built-in tracing that tries to send telemetry to OpenAI's servers
# Since we're using Groq (not OpenAI), this would cause authentication failures
set_tracing_disabled(True)

# Configure the OpenAI Agents SDK to use Llama via Groq's AsyncOpenAI
# This sets the default client for all agents created in this module
groq_client = get_groq_client()
set_default_openai_client(groq_client)

# Create OpenAI Chat Completions Model for Llama 3.3 70B via Groq
# Reference: https://console.groq.com/docs/models
groq_model = OpenAIChatCompletionsModel(
    model=settings.GROQ_MODEL,
    openai_client=groq_client,
)


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
   - CREATE indicators: "add", "remind me", "create", "new task", "I need to", "don't forget"
   - LIST indicators: "show", "what's on my list", "list", "display", "view"
   - UPDATE indicators: "mark as", "change", "update", "modify", "move deadline"
   - DELETE indicators: "delete", "remove", "clear", "cancel"

2. **Attribute Extraction for CREATE Operations** (User Story 1 - MVP):
   - **Title Extraction**: Identify the core task description from natural language
     * Strip action verbs: "Remind me to buy eggs" → title="buy eggs"
     * Extract imperative phrases: "Add grocery shopping" → title="grocery shopping"
     * Handle compound tasks: "I need to call mom" → title="call mom"
     * Preserve important context: "finish project proposal" → title="finish project proposal"

   - **Description Extraction**: Capture supporting details beyond the short title
     * Explicit markers: "Description: ...", "Details: ...", "Notes: ..." → description="<that text>"
     * After separators: "Call dentist - schedule annual checkup" → title="call dentist", description="schedule annual checkup"
     * Second sentence: "Buy groceries. Milk, eggs, bread." → title="buy groceries", description="Milk, eggs, bread."
     * If no extra details are provided, omit description (leave it null)

   - **Due Date Parsing**: Convert temporal expressions to ISO 8601 datetime strings
     * Relative dates: "tomorrow" → next day's date, "next Friday" → upcoming Friday
     * Time specifications: "at 3pm" → 15:00:00, "by 5:30" → 17:30:00
     * Date combinations: "tomorrow at 3pm" → combine date and time
     * Default time: If only date specified, use 09:00:00 as default time
     * Current date reference: Use the current date/time as baseline for calculations

   - **Priority Inference**: Map urgency indicators to priority levels
     * HIGH priority: "urgent", "ASAP", "important", "critical", "high priority", "immediately"
     * MEDIUM priority: default for most tasks, "normal", "regular"
     * LOW priority: "low priority", "when I get to it", "sometime", "not urgent"
     * Extract from context: "high priority task: finish proposal" → priority="high"

   - **Tags Extraction**: Identify category keywords and hashtags
     * Hashtags: "#work", "#personal", "#shopping" → tags=["work", "personal", "shopping"]
     * Category keywords: "work task", "personal reminder" → tags=["work"], tags=["personal"]

   - **Status**: Always default to "pending" for new todos

3. **MCP Tool Usage**:
   - ALWAYS use the MCP tools (create_todo, list_todos, update_todo, delete_todo)
   - NEVER attempt to store or manage todo data internally
   - Pass extracted attributes as tool arguments
   - For CREATE operations, call create_todo with extracted: title, description (optional), due_date (optional), priority, tags (optional)

4. **Natural Language Responses**:
   - Confirm operations in conversational language
   - Summarize todo lists in readable format
   - Ask clarifying questions when intent is ambiguous

5. **Safety Guidelines**:
   - For mass deletions (3+ todos), request explicit confirmation
   - Handle errors gracefully with user-friendly messages
   - Stay within todo management scope - decline unrelated requests politely

6. **Ambiguous Input Handling** (Edge Case - T081):
   - **Detect Ambiguity**: Identify when user intent is unclear or insufficient information is provided
   - **Ambiguous Intent Indicators**:
     * Vague verbs without clear action: "something about eggs", "things to do"
     * Missing critical attributes: "Add a task" (no title specified)
     * Conflicting intentions: "Show me and delete my todos" (both list and delete?)
     * Unclear references: "Update that" (which todo?)
     * Multiple possible interpretations: "Change it" (change what field?)

   - **Clarification Strategy**:
     * Ask targeted, specific questions to resolve ambiguity
     * Provide examples of what information is needed
     * Limit to 1-2 clarifying questions at a time
     * Be conversational and helpful

   - **Clarification Examples**:
     * User: "Add something about groceries" → "I'd be happy to help! What specific grocery item should I add to your todo list?"
     * User: "Update the task" → "Which task would you like to update? You can reference it by name or I can show you your current list."
     * User: "Change it to tomorrow" → "I can help you reschedule a task. Which task should I move to tomorrow?"
     * User: "Delete things" → "Which tasks would you like to delete? Please specify which one(s) you want removed."
     * User: "Show and delete" → "Would you like me to: (1) show you your tasks first, or (2) delete specific tasks? Let me know which action you'd prefer."

   - **Never Guess**: When ambiguous, ALWAYS ask for clarification rather than making assumptions
   - **Provide Context**: Remind user of recent operations to help with context-based references

7. **Out-of-Scope Request Detection** (Edge Case - T082):
   - **Scope Boundaries**: This assistant ONLY handles todo management operations (CRUD on todos)
   - **Out-of-Scope Indicators**:
     * General knowledge questions: "What's the weather?", "How do I cook pasta?", "What's 2+2?"
     * Calendar operations beyond todos: "Schedule a meeting", "Set up a recurring event", "Check my availability"
     * Email/messaging: "Send an email", "Text my friend", "Reply to messages"
     * File operations: "Create a document", "Delete a file", "Upload photos"
     * Web browsing: "Search the web", "Open YouTube", "Check my email"
     * System operations: "Restart my computer", "Install an app", "Change settings"
     * Personal assistance beyond todos: "Set an alarm", "Call someone", "Order food"
     * Complex project management: "Create a Gantt chart", "Assign tasks to team members", "Track dependencies"

   - **Polite Decline Strategy**:
     * Acknowledge the request politely
     * Clearly state the scope limitation
     * Redirect to what you CAN help with (todo management)
     * Offer an alternative if applicable (e.g., suggest creating a todo as a reminder)

   - **Out-of-Scope Response Examples**:
     * User: "What's the weather today?" → "I'm a todo management assistant and can't check the weather. However, I can create a reminder for you to check the weather if you'd like!"
     * User: "Send an email to John" → "I can't send emails, but I can add 'Email John' to your todo list as a reminder. Would that help?"
     * User: "How do I make lasagna?" → "I specialize in managing your todo list, not recipes! But I'd be happy to add 'Look up lasagna recipe' as a task if you want to remember to do that."
     * User: "Set an alarm for 6am" → "I manage todos, not alarms. However, I can create a todo reminder like 'Wake up at 6am' if that helps you remember."
     * User: "Schedule a team meeting on Friday" → "While I can't manage calendar events, I can add 'Schedule team meeting for Friday' to your todo list to remind you. Would that work?"
     * User: "What's 2 plus 2?" → "I'm focused on helping you manage your todos! If you need to remember to do a calculation or math task, I can add that to your list."
     * User: "Book a flight to Paris" → "I can't book flights, but I can add 'Book flight to Paris' as a high-priority todo so you don't forget! Should I create that task?"

   - **Scope-Friendly Conversions**: When possible, offer to convert out-of-scope requests into todos
     * "I can't do X, but I can add 'Do X' to your todo list"
     * Always ask for confirmation before converting to a todo

   - **Tone**: Always be friendly, helpful, and clear about boundaries
   - **Never Pretend**: Don't attempt to handle out-of-scope requests or make up capabilities

8. **Examples for CREATE Operations** (User Story 1):
 - "Remind me to buy eggs" → create_todo(title="buy eggs", priority="medium")
 - "Add high priority task: finish project proposal by Friday" → create_todo(title="finish project proposal", priority="high", due_date="<this Friday's ISO date>")
 - "I need to call mom tomorrow" → create_todo(title="call mom", due_date="<tomorrow's date at 09:00:00>", priority="medium")
 - "Remind me to buy eggs tomorrow at 3pm" → create_todo(title="buy eggs", due_date="<tomorrow's date>T15:00:00", priority="medium")
 - "Create urgent task: submit report ASAP" → create_todo(title="submit report", priority="high")
 - "Call dentist - schedule annual checkup" → create_todo(title="call dentist", description="schedule annual checkup", priority="medium")

9. **Attribute Extraction for LIST Operations** (User Story 2):
   - **Status Filter**: Extract desired completion state from query
     * PENDING todos: "active tasks", "what do I need to do", "incomplete", "pending tasks", "open items"
     * COMPLETED todos: "finished tasks", "what did I complete", "done items", "completed tasks"
     * ALL todos: "everything", "all tasks", "entire list", "all todos", "show me everything"
     * Default: If not specified, show "pending" (active tasks)

   - **Priority Filter**: Extract priority level from query
     * HIGH priority: "urgent tasks", "high priority items", "important todos", "critical tasks"
     * MEDIUM priority: "medium priority", "normal tasks"
     * LOW priority: "low priority tasks", "non-urgent items", "when I get to it"
     * Default: If not specified, show ALL priority levels

   - **Due Date Filter**: Convert temporal query expressions to filter values
     * TODAY: "today", "today's tasks", "what's due today", "tasks for today"
     * THIS_WEEK: "this week", "week's tasks", "what's due this week", "weekly tasks"
     * OVERDUE: "overdue", "past due", "late tasks", "missed deadlines"
     * Specific date: "tasks for Friday", "what's due on Monday" → convert to ISO date
     * Date range: "tasks between Monday and Friday" → extract start and end dates
     * Default: If not specified, show ALL due dates

   - **Tags Filter**: Identify category keywords to filter by
     * Hashtags: "show #work tasks", "#personal items" → tags=["work"], tags=["personal"]
     * Category keywords: "work todos", "personal reminders" → tags=["work"], tags=["personal"]
     * Multiple tags: "show work and personal tasks" → tags=["work", "personal"]
     * Default: If not specified, show ALL tags

   - **Combined Filters**: Handle queries with multiple filter criteria
     * "Show me high priority work tasks for today" → priority="high", tags=["work"], due_date_filter="today"
     * "What are my completed tasks this week?" → status="completed", due_date_filter="this_week"
     * "List all urgent overdue items" → priority="high", due_date_filter="overdue"

   - **MCP Tool Usage for LIST**: Call list_todos with extracted filter arguments
     * For LIST operations, call list_todos with extracted: status (optional), priority (optional), due_date_filter (optional), tags (optional)
     * If no filters specified, list_todos() returns all pending todos by default

10. **Examples for LIST Operations** (User Story 2):
- "What's on my todo list?" → list_todos(status="pending")
- "Show me all tasks" → list_todos(status="all")
- "What's on my todo list for today?" → list_todos(due_date_filter="today", status="pending")
- "Show me high priority tasks" → list_todos(priority="high", status="pending")
- "What work tasks do I have this week?" → list_todos(tags=["work"], due_date_filter="this_week", status="pending")
- "List all completed tasks" → list_todos(status="completed")
- "Show me overdue urgent items" → list_todos(due_date_filter="overdue", priority="high", status="pending")
- "What personal tasks are due today?" → list_todos(tags=["personal"], due_date_filter="today", status="pending")

11. **Attribute Extraction for UPDATE Operations** (User Story 3):
   - **TODO ID Inference**: Determine which todo to update from context
     * Explicit ID: "Update todo #123" → todo_id="123"
     * Title reference: "Mark buy eggs as complete" → infer todo_id from recent list results or conversation
     * Contextual reference: "Change the priority to high" → use most recently mentioned todo
     * Implicit reference: "Complete that task" → infer from last discussed todo
     * **IMPORTANT**: If todo_id cannot be inferred with confidence, ask user to clarify which todo

   - **Status Updates**: Detect status change requests
     * COMPLETE indicators: "mark as complete", "mark as done", "complete", "finish", "mark done", "set to completed"
     * PENDING indicators: "mark as pending", "reopen", "uncomplete", "mark as not done", "set to pending"
     * Default: If "mark" or "update" without status specified, ask for clarification

   - **Priority Updates**: Detect priority change requests
     * HIGH priority: "change to high priority", "make urgent", "set priority to high", "upgrade priority"
     * MEDIUM priority: "change to medium priority", "normal priority", "set to medium"
     * LOW priority: "change to low priority", "downgrade priority", "set to low"

   - **Due Date Updates**: Detect due date modification requests
     * New due date: "move to Friday", "change deadline to tomorrow", "reschedule to next week"
     * Remove due date: "remove deadline", "clear due date", "no deadline"
     * Parse temporal expressions: "push back by 2 days", "move up by 1 week"

   - **Title Updates**: Detect title modification requests
     * Direct title change: "rename to 'Finish report'", "change title to 'Call client'"
     * Implicit update: "Update the task to 'Complete presentation'"

   - **Tags Updates**: Detect tag modifications
     * Add tags: "add #work tag", "tag with personal", "add work and urgent tags"
     * Remove tags: "remove #work tag", "untag personal", "clear all tags"
     * Replace tags: "change tags to #work and #important"

   - **Multi-Field Updates**: Handle requests that update multiple fields simultaneously
     * "Mark buy eggs as complete and high priority" → status="completed", priority="high"
     * "Change deadline to Friday and mark as urgent" → due_date="<Friday's ISO date>", priority="high"

   - **MCP Tool Usage for UPDATE**: Call update_todo with inferred todo_id and changed fields
     * For UPDATE operations, call update_todo with: todo_id (required), and any updated fields (title, description, due_date, priority, status, tags)
     * Only include fields that are being changed - don't send unchanged fields
     * Validate todo_id exists before updating (if possible from context)

12. **Examples for UPDATE Operations** (User Story 3):
- "Mark buy eggs as complete" → update_todo(todo_id=<inferred from context>, status="completed")
- "Change the deadline to Friday" → update_todo(todo_id=<inferred>, due_date="<this Friday's ISO date>")
- "Make the project proposal task urgent" → update_todo(todo_id=<inferred>, priority="high")
- "Rename task to 'Call dentist'" → update_todo(todo_id=<inferred>, title="Call dentist")
- "Mark task #42 as done and high priority" → update_todo(todo_id="42", status="completed", priority="high")
- "Update the shopping task: change to tomorrow at 5pm" → update_todo(todo_id=<inferred>, due_date="<tomorrow at 17:00:00>")
- "Clear the deadline for the gym task" → update_todo(todo_id=<inferred>, due_date=None)
- "Add work tag to the report task" → update_todo(todo_id=<inferred>, tags=<existing_tags + ["work"]>)

13. **Attribute Extraction for DELETE Operations** (User Story 4):
   - **TODO ID Inference**: Determine which todo(s) to delete from context
     * Explicit ID: "Delete todo #123" → todo_id="123" (SINGLE deletion)
     * Title reference: "Delete buy eggs task" → infer todo_id from recent list results or conversation (SINGLE deletion)
     * Contextual reference: "Remove that task" → use most recently mentioned todo (SINGLE deletion)
     * **IMPORTANT**: If todo_id cannot be inferred with confidence for single deletion, ask user to clarify which todo

   - **Single vs Mass Deletion Detection**: Determine deletion scope and apply safety guardrails
     * **SINGLE deletion indicators**: "delete todo #5", "remove the buy eggs task", "delete that task", "cancel the meeting reminder"
       - Count: Affects exactly 1 todo
       - Behavior: Execute deletion immediately without confirmation
       - Example: "Delete the shopping task" → delete_todo(todo_id=<inferred>)

     * **MASS deletion indicators**: "delete all", "clear all", "remove all", "delete completed tasks", "clear my list"
       - Count: Affects 3 or more todos (threshold for confirmation)
       - Behavior: MUST request explicit user confirmation before executing
       - Example: "Delete all completed tasks" → First ask: "Are you sure you want to delete X completed tasks? This cannot be undone. Please confirm."
       - Wait for user response: "yes", "confirm", "delete all", "proceed" → Execute deletions
       - User denies: "no", "cancel", "wait", "stop" → Abort operation

     * **Batch deletion (2 todos)**: Edge case - treat as SINGLE deletion (no confirmation needed)
       - Example: "Delete task #5 and task #10" → delete both without confirmation

   - **Filter-Based Mass Deletion**: Detect deletions based on filters (requires confirmation)
     * Status filter: "delete all completed tasks", "clear finished items" → filter by status="completed", then confirm
     * Priority filter: "remove all low priority tasks" → filter by priority="low", then confirm
     * Tag filter: "delete all #work tasks" → filter by tags=["work"], then confirm
     * Due date filter: "clear overdue tasks" → filter by due_date_filter="overdue", then confirm
     * Combined filters: "delete completed work tasks" → filter by status="completed" AND tags=["work"], then confirm

   - **Deletion Scope Calculation**: Before requesting confirmation, calculate exact count
     * Query matching todos using list_todos with appropriate filters
     * Count the number of todos that will be affected
     * If count >= 3: Request confirmation with exact count ("Are you sure you want to delete 5 completed tasks?")
     * If count < 3: Proceed with deletion immediately
     * If count == 0: Inform user ("No matching todos found to delete")

   - **Confirmation Request Format**: Clear, explicit confirmation request with details
     * Include exact count: "Are you sure you want to delete 8 tasks?"
     * Include deletion criteria: "Are you sure you want to delete all completed tasks (8 total)?"
     * Warn about irreversibility: "This cannot be undone."
     * Request explicit confirmation: "Please confirm by saying 'yes, delete all' or cancel by saying 'no'."

   - **Confirmation Parsing**: Detect user's confirmation or cancellation intent
     * CONFIRM indicators: "yes", "confirm", "delete", "proceed", "yes delete all", "do it", "go ahead"
     * CANCEL indicators: "no", "cancel", "wait", "stop", "don't", "abort", "never mind"
     * AMBIGUOUS: If unclear, ask again for explicit confirmation

   - **MCP Tool Usage for DELETE**: Call delete_todo with appropriate parameters
     * For SINGLE deletion: delete_todo(todo_id=<inferred or explicit ID>)
     * For MASS deletion: After confirmation, call delete_todo for each matching todo_id
     * Consider batch delete if MCP supports it: delete_todo(todo_ids=[...])
     * Handle errors gracefully: If some deletions fail, report which ones succeeded/failed

14. **Examples for DELETE Operations** (User Story 4):
- "Delete the buy eggs task" → delete_todo(todo_id=<inferred>) [SINGLE - no confirmation]
- "Remove todo #42" → delete_todo(todo_id="42") [SINGLE - no confirmation]
- "Cancel that meeting reminder" → delete_todo(todo_id=<inferred from context>) [SINGLE - no confirmation]
- "Delete all completed tasks" → list_todos(status="completed") → count=8 → REQUEST CONFIRMATION → "Are you sure you want to delete 8 completed tasks? This cannot be undone. Please confirm." → Wait for "yes" → delete each todo [MASS - requires confirmation]
- "Clear all my todos" → list_todos() → count=25 → REQUEST CONFIRMATION → "Are you sure you want to delete all 25 tasks? This cannot be undone. Please confirm." → Wait for "yes" → delete each todo [MASS - requires confirmation]
- "Remove all low priority tasks" → list_todos(priority="low") → count=5 → REQUEST CONFIRMATION → delete each todo [MASS - requires confirmation]
- "Delete completed work tasks" → list_todos(status="completed", tags=["work"]) → count=3 → REQUEST CONFIRMATION → delete each todo [MASS - requires confirmation]
- "Clear overdue items" → list_todos(due_date_filter="overdue") → count=12 → REQUEST CONFIRMATION → delete each todo [MASS - requires confirmation]
"""

TODO_AGENT_INSTRUCTIONS_COMPACT = """
You are a todo management assistant. Convert the user's message into one or more tool calls, then respond concisely using the tool results.

Available tools:
- create_todo(title, description?, due_date?, priority?, tags?)
- list_todos(status?, priority?, limit?, offset?) - status: active/completed/archived/all, priority: low/medium/high
- update_todo(todo_id, title?, description?, status?, priority?) - status: active/completed/archived, priority: low/medium/high
- search_todos(keyword)
- delete_todo(todo_id?, todo_ids?, status?, priority?, keyword?, confirm?)

Rules:
- Always use tools for CRUD actions; never invent todos, IDs, or internal state.
- If the user refers to a todo without an ID, use list_todos or search_todos first to find the right item.
- Keep replies short and practical.

CREATE extraction:
- Title: required, short action phrase.
- Description Extraction: optional details beyond the short title.
- Due date: if provided, pass an ISO-8601 datetime string; otherwise omit.
- Priority: infer low/medium/high; default medium.
- Tags: extract hashtags or obvious categories; otherwise omit.
- For CREATE operations, call create_todo with extracted: title, description (optional), due_date (optional), priority, tags (optional)

LIST:
- status: use "active" for active/pending/open, "completed" for completed/done/finished, "archived" for archived/cancelled, "all" for all.
- priority: map to low/medium/high; if multiple priorities are requested, pass a list or a comma-separated string (e.g., "medium,high").
- If no filters are specified, call list_todos() for active todos.
- Examples: "What todos have I completed?" -> list_todos(status="completed"); "Show me active todos that are medium or high priority" -> list_todos(status="active", priority="medium,high").

UPDATE:
- Determine todo_id (list/search if needed), then update only requested fields.
- status must be one of: active, completed, archived.
- priority must be one of: low, medium, high.
- Examples: "Mark task as completed" -> update_todo(todo_id=X, status="completed"); "Change to high priority" -> update_todo(todo_id=X, priority="high")

DELETE:
- delete_todo supports todo_id, todo_ids, status, priority, keyword, confirm.
- If user specifies a todo by ID ("delete todo 5"), call delete_todo(todo_id=5).
- If user specifies a todo by title/description, use delete_todo(keyword="...") or search_todos(keyword) -> delete_todo(todo_id=...).
- For deleting by status/priority ("remove all completed", "clear archived"), call delete_todo(status="completed"/"archived", confirm=true if user explicitly says delete all/remove all/clear all).
- For mass delete (3+ todos), set confirm=true only when the user explicitly confirms; otherwise ask for confirmation and wait.
- Examples:
  - "Delete the task about organizing my desk" -> delete_todo(keyword="organizing my desk")
  - "Delete todo number 5" -> delete_todo(todo_id=5)
  - "Remove all completed todos" -> delete_todo(status="completed", confirm=true)
  - "Clear out all my archived tasks" -> delete_todo(status="archived", confirm=true)
"""


async def create_todo_agent(
    mcp_servers: Optional[List[MCPServerStdio]] = None,
) -> Agent:
    """
    Create and configure the TodoAgent using OpenAI Agents SDK.

    The agent is initialized with system instructions that emphasize:
    - Natural language intent extraction
    - MCP tool usage (no internal state)
    - Conversational response generation

    MCP tools are registered dynamically when mcp_servers parameter is provided.
    Due to Groq API limitations with MCP protocol, tools are manually discovered
    and registered as Function tools.

    Args:
        mcp_servers: Optional list of MCPServerStdio instances for tool discovery.
                    Each instance represents a connected MCP server with available tools.
                    Tools are manually listed and registered with the agent.
                    If None or empty list, agent is created without MCP tools (for testing).

    Returns:
        Agent: Configured TodoAgent instance with registered MCP tools

    Example:
        >>> # Create agent with MCP tools
        >>> from src.mcp.client import initialize_mcp_connection
        >>> mcp_server = await initialize_mcp_connection()
        >>> if mcp_server:
        ...     agent = await create_todo_agent(mcp_servers=[mcp_server])
        >>>
        >>> # Create agent without tools (for testing)
        >>> agent = await create_todo_agent()
    """
    # NOTE: Groq uses the OpenAI ChatCompletions API, which does NOT support Hosted tools
    # (including raw MCP `mcp.types.Tool` objects). We expose MCP tools to the model as
    # Function tools that proxy to `MCPServerStdio.call_tool(...)`.
    mcp_server: Optional[MCPServerStdio] = mcp_servers[0] if mcp_servers else None

    discovered_tool_names: List[str] = []
    if mcp_server is not None:
        try:
            tools_list = await mcp_server.list_tools()
            discovered_tool_names = [t.name for t in tools_list if hasattr(t, "name")]
            logger.info(
                f"Listed {len(tools_list) if tools_list else 0} tools from MCP server",
                extra={
                    "mcp_server": getattr(mcp_server, "name", "unknown"),
                    "tools_count": len(tools_list) if tools_list else 0,
                    "tools": discovered_tool_names,
                },
            )
        except Exception as e:
            logger.error(
                f"Failed to list tools from MCP server: {e}",
                extra={"error": str(e)},
                exc_info=True,
            )

    def _extract_mcp_result(result: Any) -> Any:
        if isinstance(result, (dict, list, str)):
            return result

        structured = getattr(result, "structuredContent", None)
        if structured is not None:
            if isinstance(structured, dict) and "result" in structured:
                return structured["result"]
            return structured

        content = getattr(result, "content", None)
        if isinstance(content, list):
            text_parts: List[str] = []
            for part in content:
                part_text = getattr(part, "text", None)
                if isinstance(part_text, str) and part_text:
                    text_parts.append(part_text)
            if text_parts:
                return "\n".join(text_parts)

        return str(result)

    async def _call_mcp_tool(tool_name: str, args: Dict[str, Any]) -> str:
        if mcp_server is None:
            raise ConnectionError("MCP server is not available (degraded mode)")

        result = await mcp_server.call_tool(tool_name, args)

        is_error = getattr(result, "isError", False)
        payload = _extract_mcp_result(result)
        if is_error:
            raise RuntimeError(str(payload))
        return payload

    tools = []
    if mcp_server is not None:
        @function_tool(strict_mode=False)
        async def create_todo(
            title: str,
            description: Optional[str] = None,
            due_date: Optional[str] = None,
            priority: str = "medium",
            tags: Optional[List[str]] = None,
        ) -> str:
            """Create a new todo item.

            Args:
                title: The title/name of the todo (required)
                description: Optional detailed description
                due_date: Optional due date in ISO 8601 format
                priority: Priority level - "low", "medium" (default), or "high"
                tags: Optional list of tags/categories

            Returns:
                Success message with created todo details
            """
            return await _call_mcp_tool(
                "create_todo",
                {
                    "title": title,
                    "description": description,
                    "due_date": due_date,
                    "priority": priority,
                    "tags": tags,
                },
            )

        @function_tool(strict_mode=False)
        async def list_todos(
            status: Optional[str] = None,
            priority: Optional[Union[str, List[str]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
        ) -> Any:
            """List todo items with optional filters.

            By default (no filters), returns only active todos. Supports filtering by
            status, priority, and pagination. All filters use AND logic.

            Args:
                status: Filter by status - "active", "completed", "archived", or "all"
                priority: Filter by priority - "low", "medium", or "high" (single or list)
                limit: Maximum number of results to return
                offset: Number of results to skip for pagination

            Returns:
                Structured list of filtered todos
            """
            args = {
                "status": status,
                "priority": priority,
                "limit": limit,
                "offset": offset,
            }
            return await _call_mcp_tool(
                "list_todos",
                {key: value for key, value in args.items() if value is not None},
            )

        @function_tool(strict_mode=False)
        async def update_todo(
            todo_id: int,
            title: Optional[str] = None,
            description: Optional[str] = None,
            status: Optional[str] = None,
            priority: Optional[str] = None,
        ) -> str:
            """Update an existing todo item by ID.

            Args:
                todo_id: The ID of the todo to update (required)
                title: New title for the todo (optional)
                description: New description for the todo (optional)
                status: New status - "active", "completed", or "archived" (optional)
                priority: New priority - "low", "medium", or "high" (optional)

            Returns:
                Success message with updated todo details
            """
            # Build args dict, excluding None values
            args = {
                "id": todo_id,  # MCP tool expects "id" not "todo_id"
                "title": title,
                "description": description,
                "status": status,
                "priority": priority,
            }
            # Filter out None values to allow partial updates
            args = {k: v for k, v in args.items() if v is not None}
            return await _call_mcp_tool("update_todo", args)

        @function_tool(strict_mode=False)
        async def search_todos(keyword: str) -> Any:
            """Search active todos by keyword in title or description.

            Use this to find a todo when the user mentions it by name/title.
            Returns a structured list with todo IDs which can be used with delete_todo or update_todo.
            NOTE: Only searches ACTIVE todos. Use list_todos(status=...) for completed/archived.

            Args:
                keyword: Search term to match in title or description

            Returns:
                Structured list of matching todos with their IDs
            """
            return await _call_mcp_tool("search_todos", {"keyword": keyword})

        @function_tool(strict_mode=False)
        async def delete_todo(
            todo_id: Optional[int] = None,
            id: Optional[int] = None,
            todo_ids: Optional[List[int]] = None,
            status: Optional[str] = None,
            priority: Optional[Union[str, List[str]]] = None,
            keyword: Optional[str] = None,
            confirm: Optional[bool] = None,
        ) -> Any:
            """Delete todos by ID or filter.

            Supports single ID, multiple IDs, or filter-based deletion using
            status/priority/keyword. For 3+ matches, returns a confirmation_required
            response unless confirm=True is provided.

            Args:
                todo_id: Single todo ID to delete (preferred)
                id: Alias for todo_id
                todo_ids: List of todo IDs to delete
                status: Filter by status ("active", "completed", "archived", "all")
                priority: Filter by priority ("low", "medium", "high") or list
                keyword: Substring match against title/description
                confirm: Set true to confirm mass deletion

            Returns:
                Structured confirmation or confirmation_required response
            """
            def _coerce_int(value: Any) -> Optional[int]:
                if isinstance(value, int):
                    return value
                if isinstance(value, str):
                    stripped = value.strip()
                    if stripped.isdigit():
                        return int(stripped)
                return None

            def _extract_items(result: Any) -> List[Any]:
                if isinstance(result, dict):
                    items = result.get("todos")
                    if isinstance(items, list):
                        return items
                    if "id" in result:
                        return [result]
                    return []
                if isinstance(result, list):
                    return result
                return []

            def _validate_list_result(result: Any) -> Any:
                if isinstance(result, str) and result.strip().lower().startswith("error"):
                    raise ValueError(result)
                return result

            def _extract_ids(items: List[Any]) -> List[int]:
                ids: List[int] = []
                for item in items:
                    if isinstance(item, dict):
                        raw_id = item.get("id")
                    else:
                        raw_id = getattr(item, "id", None)
                    coerced = _coerce_int(raw_id)
                    if coerced is not None:
                        ids.append(coerced)
                return ids

            def _filter_ids_by_keyword(items: List[Any], keyword_value: str) -> List[int]:
                keyword_lower = keyword_value.lower()
                matched: List[int] = []
                for item in items:
                    if isinstance(item, dict):
                        title = str(item.get("title", "") or "")
                        description = str(item.get("description", "") or "")
                        raw_id = item.get("id")
                    else:
                        title = str(getattr(item, "title", "") or "")
                        description = str(getattr(item, "description", "") or "")
                        raw_id = getattr(item, "id", None)
                    if keyword_lower in title.lower() or keyword_lower in description.lower():
                        coerced = _coerce_int(raw_id)
                        if coerced is not None:
                            matched.append(coerced)
                return matched

            resolved_ids: List[int] = []

            if todo_id is None and id is not None:
                todo_id = id

            if todo_id is not None:
                coerced = _coerce_int(todo_id)
                if coerced is None:
                    raise ValueError("todo_id must be an integer")
                resolved_ids = [coerced]
            elif todo_ids:
                for item in todo_ids:
                    coerced = _coerce_int(item)
                    if coerced is not None:
                        resolved_ids.append(coerced)

            if not resolved_ids:
                list_args: Dict[str, Any] = {}
                if status:
                    list_args["status"] = status
                if priority:
                    list_args["priority"] = priority

                if keyword:
                    if "status" not in list_args:
                        list_args["status"] = "all"
                    list_result = await _call_mcp_tool("list_todos", list_args)
                    list_result = _validate_list_result(list_result)
                    resolved_ids = _filter_ids_by_keyword(
                        _extract_items(list_result),
                        keyword,
                    )
                elif list_args:
                    list_result = await _call_mcp_tool("list_todos", list_args)
                    list_result = _validate_list_result(list_result)
                    resolved_ids = _extract_ids(_extract_items(list_result))

            if not resolved_ids:
                return {
                    "success": False,
                    "deleted_id": None,
                    "deleted_ids": [],
                    "deleted_count": 0,
                    "requested_count": 0,
                    "message": "No todos matched the deletion criteria.",
                }

            if len(resolved_ids) >= 3 and not confirm:
                return {
                    "success": False,
                    "confirmation_required": True,
                    "deleted_id": None,
                    "deleted_ids": [],
                    "deleted_count": 0,
                    "requested_count": len(resolved_ids),
                    "message": (
                        f"This will delete {len(resolved_ids)} todos. "
                        "Please confirm to proceed."
                    ),
                }

            deleted_ids: List[int] = []
            errors: List[str] = []

            for todo_id_value in resolved_ids:
                try:
                    result = await _call_mcp_tool("delete_todo", {"id": todo_id_value})
                    success = True
                    if isinstance(result, dict):
                        success = result.get("success", True)
                    if success:
                        deleted_ids.append(todo_id_value)
                    else:
                        errors.append(f"Failed to delete todo {todo_id_value}")
                except Exception as exc:
                    errors.append(f"Todo {todo_id_value}: {exc}")

            success = len(errors) == 0
            if success:
                if len(deleted_ids) == 1:
                    message = f"Todo (ID: {deleted_ids[0]}) deleted."
                else:
                    message = f"Deleted {len(deleted_ids)} todos."
            else:
                if deleted_ids:
                    message = (
                        f"Deleted {len(deleted_ids)} todos; "
                        f"{len(errors)} failed."
                    )
                else:
                    message = "Failed to delete todos."

            return {
                "success": success,
                "deleted_id": deleted_ids[0] if len(deleted_ids) == 1 else None,
                "deleted_ids": deleted_ids,
                "deleted_count": len(deleted_ids),
                "requested_count": len(resolved_ids),
                "errors": errors or None,
                "message": message,
            }

        tools = [create_todo, list_todos, update_todo, search_todos, delete_todo]

        # Align tool schema titles with tool names to prevent model confusion.
        for tool in tools:
            schema = getattr(tool, "params_json_schema", None)
            if isinstance(schema, dict) and schema.get("title") != tool.name:
                schema["title"] = tool.name

    # Do NOT pass `mcp_servers` into the Agent when using ChatCompletions + Groq.
    # The model can only see and call Function tools; MCP is used under the hood.
    agent = Agent(
        name="TodoAgent",
        model=groq_model,
        instructions=TODO_AGENT_INSTRUCTIONS_COMPACT,  # Use compact instructions (full might be too verbose for Groq)
        tools=tools,
        mcp_servers=[],
        # Removed tool_use_behavior to allow all operations to complete properly
        model_settings=ModelSettings(
            max_tokens=settings.AGENT_MAX_OUTPUT_TOKENS,
            parallel_tool_calls=False,
        ),
    )

    logger.info(
        f"TodoAgent created with {1 if mcp_server else 0} MCP server(s) - "
        f"Registered {len(tools)} Function tool(s) for Groq",
        extra={
            "mcp_servers_count": 1 if mcp_server else 0,
            "discovered_tools_count": len(discovered_tool_names),
            "discovered_tools": discovered_tool_names,
            "registered_tools_count": len(tools),
            "registered_tools": [t.name for t in tools] if tools else [],
            "agent_name": "TodoAgent",
            "degraded_mode": mcp_server is None,
        },
    )

    return agent


@groq_retry
async def _execute_agent_with_retry(
    agent: Agent, input_text: str, context: Any = None
) -> Any:
    """
    Internal function to execute agent with retry logic.

    This function is wrapped with @groq_retry decorator for exponential backoff:
    - Max attempts: 3
    - Exponential backoff: 2s → 4s → 8s (with jitter)
    - Max wait: 60 seconds
    - Timeout: 30 seconds per attempt (T084)

    T028: Includes tool call validation logging for all MCP tool executions:
    - Log tool name
    - Log parameters
    - Log execution duration
    - Log result status (success/failure)

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
    import asyncio
    import time

    # T084: Groq API timeout constant (30 seconds)
    # This ensures each Groq API call completes within reasonable time
    GROQ_TIMEOUT_SECONDS = 30

    # T028: Track execution start time for duration logging
    execution_start_time = time.time()

    try:
        # T084: Wrap agent execution with timeout to prevent hanging on slow Groq API
        # Note: AsyncOpenAI client also has timeout configured, this is a safety net
        async with asyncio.timeout(GROQ_TIMEOUT_SECONDS):
            # Execute agent with MCP context
            if context:
                result = await Runner.run(agent, input=input_text, context=context)
            else:
                result = await Runner.run(agent, input=input_text)

            # T028: Calculate total execution duration
            execution_duration = time.time() - execution_start_time

            # T028: Log successful agent execution with tool call details
            _log_tool_calls_from_result(result, execution_duration, success=True)

            return result

    except asyncio.TimeoutError as e:
        # T084: Timeout handling - convert to TimeoutError for retry logic
        execution_duration = time.time() - execution_start_time

        logger.warning(
            f"Groq API call timed out after {GROQ_TIMEOUT_SECONDS}s (will retry)",
            extra={
                "execution_duration_seconds": execution_duration,
                "timeout_seconds": GROQ_TIMEOUT_SECONDS,
                "result_status": "timeout",
            },
        )
        raise TimeoutError(
            f"Groq API execution exceeded timeout of {GROQ_TIMEOUT_SECONDS}s"
        ) from e

    except (ConnectionError, TimeoutError, OSError) as e:
        # These errors trigger retry logic
        execution_duration = time.time() - execution_start_time

        logger.warning(
            f"Groq API call failed (will retry): {e}",
            extra={
                "execution_duration_seconds": execution_duration,
                "result_status": "failed",
                "error_type": type(e).__name__,
            },
        )
        raise

    except Exception as e:
        # Other errors don't trigger retry
        execution_duration = time.time() - execution_start_time

        logger.error(
            f"Agent execution failed: {e}",
            extra={
                "execution_duration_seconds": execution_duration,
                "result_status": "error",
                "error_type": type(e).__name__,
            },
        )
        raise


def _log_tool_calls_from_result(
    result: Any, execution_duration: float, success: bool
) -> None:
    """
    T028: Extract and log tool call information from agent execution result.

    Logs each MCP tool call with:
    - Tool name
    - Tool parameters/arguments
    - Execution duration
    - Result status (success/failure)

    Args:
        result: Agent execution result
        execution_duration: Total execution time in seconds
        success: Whether execution succeeded
    """
    # Extract tool calls from result (structure depends on OpenAI Agents SDK)
    # The result may contain tool_calls information in various formats
    tool_calls = []

    # Try to extract tool calls from result
    if hasattr(result, "tool_calls"):
        tool_calls = result.tool_calls
    elif isinstance(result, dict) and "tool_calls" in result:
        tool_calls = result["tool_calls"]
    elif hasattr(result, "messages"):
        # Check messages for tool call information
        for message in result.messages:
            if hasattr(message, "tool_calls") and message.tool_calls:
                tool_calls.extend(message.tool_calls)

    # T028: Log overall agent execution
    logger.info(
        f"Agent execution completed - Duration: {execution_duration:.3f}s, Tools called: {len(tool_calls)}",
        extra={
            "event": "agent_execution_completed",
            "execution_duration_seconds": round(execution_duration, 3),
            "tools_called_count": len(tool_calls),
            "result_status": "success" if success else "failed",
            "agent_name": "TodoAgent",
        },
    )

    # T028: Log each individual tool call
    for idx, tool_call in enumerate(tool_calls):
        # Extract tool details (format varies by SDK)
        tool_name = None
        tool_arguments = {}
        tool_status = "unknown"

        if hasattr(tool_call, "function"):
            # OpenAI SDK format with function object
            tool_name = getattr(tool_call.function, "name", "unknown_tool")
            tool_arguments_str = getattr(tool_call.function, "arguments", "{}")

            # Parse arguments from JSON string if needed
            try:
                import json

                tool_arguments = (
                    json.loads(tool_arguments_str)
                    if isinstance(tool_arguments_str, str)
                    else tool_arguments_str
                )
            except (json.JSONDecodeError, TypeError):
                tool_arguments = {"raw": tool_arguments_str}

            tool_status = "completed" if success else "failed"

        elif hasattr(tool_call, "name"):
            # Direct name attribute
            tool_name = tool_call.name
            tool_arguments = getattr(tool_call, "arguments", {}) or getattr(
                tool_call, "parameters", {}
            )
            tool_status = "completed" if success else "failed"

        elif isinstance(tool_call, dict):
            # Dictionary format
            tool_name = tool_call.get("name") or tool_call.get(
                "tool_name", "unknown_tool"
            )
            tool_arguments = tool_call.get("arguments", {}) or tool_call.get(
                "parameters", {}
            )
            tool_status = tool_call.get("status", "completed" if success else "failed")

        # T028: Log individual tool call with full validation details
        logger.info(
            f"MCP Tool Call #{idx + 1}: {tool_name}",
            extra={
                "event": "mcp_tool_call",
                "tool_index": idx + 1,
                "tool_name": tool_name,
                "tool_arguments": tool_arguments,
                "tool_status": tool_status,
                "execution_duration_seconds": round(execution_duration, 3),
                "agent_name": "TodoAgent",
                "result_status": "success" if success else "failed",
            },
        )

        # T028: Log tool arguments in debug mode for detailed inspection
        logger.debug(
            f"Tool arguments for {tool_name}: {tool_arguments}",
            extra={
                "event": "tool_arguments_detail",
                "tool_name": tool_name,
                "arguments": tool_arguments,
                "argument_count": (
                    len(tool_arguments) if isinstance(tool_arguments, dict) else 0
                ),
            },
        )


async def execute_agent_with_resilience(
    agent: Agent, input_text: str, context: Any = None
) -> Dict[str, Any]:
    """
    Execute TodoAgent with circuit breaker and retry logic for resilience.

    This function wraps agent execution with:
    - Circuit breaker pattern (fail-fast when Groq API is down)
    - Exponential backoff retry (3 attempts with jitter)

    The resilience layers protect against:
    - Groq API rate limiting
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
    circuit_breaker = get_groq_circuit_breaker()

    try:
        # Circuit breaker wraps retry logic
        result = await circuit_breaker.call(
            _execute_agent_with_retry, agent, input_text, context
        )

        return {"success": True, "result": result}

    except CircuitBreakerError as e:
        logger.error(f"Circuit breaker open for Groq API: {e}")
        return {
            "success": False,
            "error": "circuit_breaker_open",
            "message": "AI service temporarily unavailable. Please try again later.",
            "details": str(e),
        }

    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        return {
            "success": False,
            "error": "execution_failed",
            "message": f"Failed to process request: {str(e)}",
            "details": str(e),
        }
