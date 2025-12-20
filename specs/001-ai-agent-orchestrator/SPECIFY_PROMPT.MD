Build an AI Agent Orchestrator for a Todo application.

Core Purpose: This service acts as the logic engine that connects a ChatKit frontend to a suite of Todo management tools. It interprets user intent and coordinates task operations.

Key Features:

Intent Mapping: The service must accurately translate natural language into specific tool calls (e.g., "Remind me to buy eggs" becomes a create_todo call).

Tool Execution: The orchestrator must consume and execute tools from an external FastMCP server to perform CRUD operations on a Postgres database.

Real-time Streaming: The service must provide a streaming response compatible with ChatKit, showing the agent's step-by-step reasoning and tool-calling status to the user.

Guardrails: The agent must confirm before performing mass deletions or irreversible changes to the task list.

Technical Boundaries:

State Management: Conversational history and threading are handled externally by the OpenAI ChatKit infrastructure. This service should focus only on processing the current turn and executing tools.

Data Isolation: This service is stateless. It does not store Todos; it only interacts with the data through the provided MCP tool interfaces.

Success Criteria:

The agent successfully triggers the correct MCP tools based on user chat input.

The FastAPI endpoint provides a valid stream that ChatKit can render.

The logic remains simple, delegating all data persistence to the tool layer.