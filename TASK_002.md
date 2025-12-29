Decompose the plan.md for the FastMCP Database Server into a sequential list of implementation tasks.

Task Decomposition Structure:

Phase 1: Environment & Connectivity (Foundation)

T001: Initialize the project using uv and install fastmcp, sqlmodel, asyncpg, and python-dotenv.

T002: Create a .env file template and a config.py utility to load and validate the Neon DATABASE_URL (ensuring sslmode=require is present).

T003: Implement the database.py module with an AsyncEngine and an AsyncSession generator function.

Phase 2: Data Modeling & Schema (The Blueprint)

T004: Define the Todo SQLModel in models.py including id, title, description, status, and timestamps.

T005: Implement a database initialization task in mcp_server.py using FastMCP's lifespan to create tables on Neon if they don't exist.

Phase 3: MCP Tool Implementation (The CRUD)

T006: Implement the create_todo tool with input validation and async session handling.

T007: Implement the list_todos and get_todo_by_id tools.

T008: Implement the update_todo (partial updates) and delete_todo tools.

Phase 4: Testing & Validation

T009: Create a local test script to run the MCP server in stdio mode and verify tool output formatting.

T010: Verify the "cold start" behavior with Neon to ensure the server doesn't timeout when the database is waking up.

Acceptance Criteria per Task:

Every tool must return a descriptive string or JSON for the AI Agent to consume.

No synchronous database calls; everything must use await.