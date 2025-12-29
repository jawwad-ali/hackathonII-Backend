# Quickstart: FastMCP Database Server Setup

**Feature**: 002-fastmcp-database-server
**Date**: 2025-12-29
**Purpose**: Step-by-step guide to set up and run the FastMCP database server

---

## Prerequisites

- **Python**: 3.11 or higher
- **uv**: Installed globally (`pip install uv`)
- **Neon PostgreSQL**: Account and database created (https://neon.tech)
- **Git**: Repository cloned to local machine

---

## Step 1: Environment Setup

### 1.1 Activate Virtual Environment

**CRITICAL**: Always activate `.venv` before running any commands.

#### Windows:
```powershell
.venv\Scripts\activate
```

#### Unix/macOS/Linux:
```bash
source .venv/bin/activate
```

**Verification**: Your command prompt should show `(.venv)` prefix.

### 1.2 Install Dependencies

```bash
# Ensure .venv is active first!
uv pip install fastmcp sqlmodel asyncpg python-dotenv pytest pytest-asyncio aiofiles
```

**Dependencies Installed**:
- `fastmcp` - FastMCP framework for MCP server
- `sqlmodel` - ORM (combines SQLAlchemy + Pydantic)
- `asyncpg` - Async PostgreSQL driver
- `python-dotenv` - Environment variable management
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `aiofiles` - Async file I/O (optional, for future file-based resources)

---

## Step 2: Database Configuration

### 2.1 Create Neon PostgreSQL Database

1. Go to https://neon.tech and sign in
2. Create a new project (e.g., "todo-app")
3. Create a new database (e.g., "todo_db")
4. Copy the connection string from the dashboard

**Connection String Format**:
```
postgresql://username:password@ep-xyz-123456.us-east-2.aws.neon.tech/database?sslmode=require
```

**Important**: The connection string MUST include `?sslmode=require` at the end (Neon enforces SSL).

### 2.2 Configure Environment Variables

#### Create `.env` File

In the **repository root** (`D:\hackathonII-Backend\`), create a `.env` file:

```bash
# Navigate to repository root
cd D:\hackathonII-Backend

# Create .env file (Windows PowerShell)
New-Item -Path .env -ItemType File

# OR (Unix/macOS)
touch .env
```

#### Add Database Connection String

Edit `.env` and add:

```env
# Neon PostgreSQL Connection
DATABASE_URL=postgresql+asyncpg://username:password@ep-xyz-123456.us-east-2.aws.neon.tech/database?sslmode=require

# Application Settings
DEBUG=True
LOG_LEVEL=INFO
```

**Replace**:
- `username` → Your Neon database username
- `password` → Your Neon database password
- `ep-xyz-123456.us-east-2.aws.neon.tech` → Your Neon host
- `database` → Your Neon database name (e.g., `todo_db`)

**CRITICAL**: Ensure `postgresql+asyncpg://` protocol (NOT `postgresql://`) and `?sslmode=require` suffix.

#### Create `.env.example` Template

For version control, create a `.env.example` template:

```env
# Neon PostgreSQL Connection
DATABASE_URL=postgresql+asyncpg://username:password@your-host.neon.tech/database?sslmode=require

# Application Settings
DEBUG=False
LOG_LEVEL=INFO
```

**Add to `.gitignore`**:
```bash
# Ensure .env is ignored
echo ".env" >> .gitignore
```

---

## Step 3: Project Structure Verification

Ensure the following directory structure exists:

```
hackathonII-Backend/
├── src/
│   └── mcp_server/          # NEW - Create this directory
│       ├── __init__.py
│       ├── server.py
│       ├── models.py
│       ├── database.py
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── create_todo.py
│       │   ├── list_todos.py
│       │   ├── update_todo.py
│       │   ├── delete_todo.py
│       │   └── search_todos.py
│       └── schemas.py
├── tests/
│   └── mcp_server/          # NEW - Create this directory
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_models.py
│       ├── test_tools.py
│       └── test_database.py
├── specs/
│   └── 002-fastmcp-database-server/
│       ├── spec.md
│       ├── plan.md          # This planning document
│       ├── research.md
│       ├── data-model.md
│       ├── quickstart.md    # This file
│       └── contracts/
├── .env                     # YOUR database connection (DO NOT COMMIT)
├── .env.example             # Template (COMMIT THIS)
└── pyproject.toml
```

**Create Directories** (if not exist):
```bash
# From repository root
mkdir -p src/mcp_server/tools
mkdir -p tests/mcp_server
```

---

## Step 4: Running the MCP Server

### 4.1 Start MCP Server (Development Mode)

#### Ensure Environment is Active
```bash
# Windows
.venv\Scripts\activate

# Unix/macOS
source .venv/bin/activate
```

#### Run Server
```bash
# From repository root
uv run python -m src.mcp_server.server
```

**Expected Output**:
```
INFO:     Database engine initialized
INFO:     Tables created successfully
INFO:     FastMCP server 'TodoDatabaseServer' listening on stdio
INFO:     Registered tools: create_todo, list_todos, update_todo, delete_todo, search_todos
```

**What Happens**:
1. Database engine connects to Neon PostgreSQL
2. Tables are created (if they don't exist)
3. MCP server starts listening on **stdio** (standard input/output)
4. 5 tools are registered and ready for MCP client invocations

### 4.2 Verify Server is Running

The MCP server communicates via **stdio** (JSON-RPC protocol). To test:

#### Option A: MCP Inspector (Recommended for Development)

**Install MCP Inspector**:
```bash
npm install -g @modelcontextprotocol/inspector
```

**Run Server with Inspector**:
```bash
mcp-inspector uv run python -m src.mcp_server.server
```

**Expected**: Browser opens with MCP Inspector UI showing all 5 tools.

#### Option B: Manual JSON-RPC Test (Advanced)

Send a JSON-RPC request to the server via stdin:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

**Expected Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {"name": "create_todo", "description": "Creates a new todo item..."},
      {"name": "list_todos", "description": "Retrieves all active todos..."},
      {"name": "update_todo", "description": "Updates an existing todo..."},
      {"name": "delete_todo", "description": "Permanently deletes a todo..."},
      {"name": "search_todos", "description": "Searches active todos..."}
    ]
  }
}
```

---

## Step 5: Testing the Server

### 5.1 Run Unit Tests

```bash
# Ensure .venv is active
uv run pytest tests/mcp_server/ -v
```

**Expected Output**:
```
tests/mcp_server/test_models.py::test_create_todo PASSED
tests/mcp_server/test_models.py::test_list_todos PASSED
tests/mcp_server/test_tools.py::test_create_todo_tool PASSED
...
==================== 10 passed in 2.5s ====================
```

### 5.2 Run Integration Tests (with Test Database)

```bash
# Run all tests including integration
uv run pytest tests/mcp_server/ -v --cov=src/mcp_server
```

**Expected**: >80% code coverage.

---

## Step 6: Integration with Agent Orchestrator (Future)

**NOT part of feature 002** - this will be a separate feature.

The AI Agent Orchestrator will connect to this MCP server as a client:

### Agent Orchestrator MCP Client Configuration (Preview)

```python
from mcp.client import Client
from mcp.client.stdio import StdioTransport

# In agent orchestrator code:
async def connect_to_database_server():
    transport = StdioTransport(
        command="uv",
        args=["run", "python", "-m", "src.mcp_server.server"]
    )
    async with Client(transport) as client:
        # List available tools
        tools = await client.list_tools()
        print(f"Connected to MCP server with {len(tools)} tools")

        # Call a tool
        result = await client.call_tool("list_todos", {})
        print(result)
```

**Timeline**: Integration planned for feature 003 or later.

---

## Step 7: Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'fastmcp'`

**Cause**: `.venv` not active or dependencies not installed.

**Fix**:
```bash
# Activate environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Unix

# Install dependencies
uv pip install fastmcp sqlmodel asyncpg python-dotenv
```

---

### Issue: `asyncpg.exceptions.InvalidPasswordError`

**Cause**: Incorrect database credentials in `.env`.

**Fix**:
1. Verify connection string in Neon dashboard
2. Ensure `DATABASE_URL` in `.env` matches Neon connection string
3. Check username/password are correct
4. Ensure `?sslmode=require` is present

---

### Issue: `ssl.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED]`

**Cause**: SSL certificate verification failed (rare with Neon).

**Fix**:
Add `sslmode=require` to connection string:
```env
DATABASE_URL=postgresql+asyncpg://user:pass@host.neon.tech/db?sslmode=require
```

---

### Issue: `sqlalchemy.exc.OperationalError: (asyncpg.exceptions.CannotConnectNowError)`

**Cause**: Neon database is paused (serverless auto-pause after inactivity).

**Fix**:
- Wait 5-10 seconds for Neon to resume
- Retry connection (automatic retry with `pool_pre_ping=True`)

---

### Issue: `FastMCP server not responding`

**Cause**: Server crashed or not started.

**Fix**:
1. Check terminal output for error messages
2. Verify `.env` file exists and has correct `DATABASE_URL`
3. Ensure all dependencies installed: `uv pip list | grep fastmcp`

---

### Issue: `ImportError: cannot import name 'AsyncSession'`

**Cause**: Incorrect SQLAlchemy/SQLModel version.

**Fix**:
```bash
uv pip install --upgrade sqlmodel sqlalchemy
```

---

## Step 8: Development Workflow

### Daily Development Loop

```bash
# 1. Activate environment (ALWAYS FIRST)
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Unix

# 2. Pull latest changes
git pull origin 002-fastmcp-database-server

# 3. Install/update dependencies (if pyproject.toml changed)
uv pip install -e .

# 4. Run tests
uv run pytest tests/mcp_server/ -v

# 5. Start MCP server
uv run python -m src.mcp_server.server

# 6. (In another terminal) Test with MCP Inspector
mcp-inspector uv run python -m src.mcp_server.server
```

### Adding New Tools

1. Create tool file: `src/mcp_server/tools/my_new_tool.py`
2. Define tool function:
   ```python
   from fastmcp import FastMCP
   from fastmcp.dependencies import Depends

   @mcp.tool
   async def my_new_tool(param: str, session = Depends(get_session)) -> dict:
       """Tool description."""
       # Implementation
       return {"result": param}
   ```
3. Register in `src/mcp_server/server.py`
4. Add contract: `specs/002-fastmcp-database-server/contracts/my_new_tool.json`
5. Add tests: `tests/mcp_server/test_my_new_tool.py`

---

## Step 9: Production Deployment (Future)

**NOT part of MVP** - defer to production deployment phase.

**Considerations**:
- Disable `echo=True` in database engine (SQL logging)
- Set `DEBUG=False` in `.env`
- Use managed secrets (AWS Secrets Manager, Azure Key Vault)
- Configure log aggregation (Datadog, New Relic)
- Monitor connection pool metrics
- Set up health checks (`/health` endpoint for server status)

---

## Summary Checklist

Before running the server, ensure:

- [ ] `.venv` activated
- [ ] Dependencies installed (`uv pip install ...`)
- [ ] `.env` file created with correct `DATABASE_URL`
- [ ] Neon PostgreSQL database created
- [ ] Connection string includes `postgresql+asyncpg://` and `?sslmode=require`
- [ ] Project structure matches expected layout
- [ ] Tests pass (`uv run pytest`)
- [ ] Server starts without errors (`uv run python -m src.mcp_server.server`)

---

## Quick Reference Commands

```bash
# Activate environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Unix

# Install dependencies
uv pip install fastmcp sqlmodel asyncpg python-dotenv pytest pytest-asyncio

# Run tests
uv run pytest tests/mcp_server/ -v

# Run server
uv run python -m src.mcp_server.server

# Run server with inspector
mcp-inspector uv run python -m src.mcp_server.server

# Check installed packages
uv pip list

# Update dependencies
uv pip install --upgrade fastmcp sqlmodel asyncpg
```

---

## Next Steps

After completing this quickstart:

1. **Verify**: Server runs without errors
2. **Test**: All 5 tools work via MCP Inspector
3. **Implement**: Follow `tasks.md` for implementation tasks
4. **Integrate**: Connect AI Agent Orchestrator (feature 003+)

**Questions?** See `plan.md` Technical Context or `research.md` for library documentation.
