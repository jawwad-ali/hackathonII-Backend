Implement the FastAPI Orchestrator using a modular 3-server architecture.

1. Core Tech Stack:

Backend Framework: FastAPI (Async).

AI Engine: OpenAI Agents SDK using AsyncOpenAI to bridge with Google Gemini 2.5 Flash.

Package Manager: uv (strictly).

2. Architecture Rules:

Stateless Brain: The FastAPI server must remain stateless regarding the database.

MCP Integration: The TodoAgent must be configured to connect to an external FastMCP server (Server 3) using the official MCP Python SDK to perform all CRUD operations.

ChatKit Stream: Use the openai-chatkit Python library to expose a streaming endpoint that supports "Thinking" blocks and "Tool Calls" for the Next.js frontend.

3. Technical Mandates:

Ensure all I/O is asynchronous (FastAPI, MCP calls, Gemini streaming).

Cross-reference SKILLS/SKILL.md for standardized agent behavior.

Call context-7 MCP to verify the exact initialization syntax for the openai-agents SDK to ensure the Gemini bridge is correctly implemented.

4. Constraints:

No direct Postgres/SQLModel code in this server; it must only exist in the MCP server.

No custom session/threading logic; rely on the ChatKit protocol for thread management.