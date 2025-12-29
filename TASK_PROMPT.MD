Break down the plan.md into granular, sequential tasks for the FastAPI Orchestrator.

Task Decomposition Rules:

Phase 1: Environment & Boilerplate:

Create a task to initialize the project using uv and create the .venv.

Create a task to set up the basic FastAPI structure with a /health check.

Phase 2: Gemini Bridge (The Brain):

Create a task to implement the AsyncOpenAI client configuration targeting Gemini 2.5 Flash.

Create a task to define the TodoAgent using the OpenAI Agents SDK, ensuring it has the correct system instructions but no internal database logic.

Phase 3: MCP Client (The Hands):

Create a task to set up the MCP Client within FastAPI that connects to the (upcoming) FastMCP server.

Create a task to dynamically register MCP tools to the TodoAgent.

Phase 4: ChatKit Streaming:

Create a task to implement the /api/chatkit endpoint.

Create a task to handle the streaming response, ensuring it includes Thinking blocks and Tool Call status events.

Acceptance Criteria per Task:

Each task must result in code that is testable/runnable.

Tasks must adhere to the Constitution (no standard OpenAI imports, strictly uv commands).

Refer to SKILLS/SKILL.md for any specific behavioral logic for the agent.