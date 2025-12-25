# Claude Code Instructions - AI Agent Orchestrator

> **Project**: AI Agent Orchestrator for Todo Management
> **Purpose**: Conversational CRUD interface using ChatKit, OpenAI Agents SDK, and MCP tools
> **Version**: 1.0.0

This file defines how Claude Code should assist with this project. It combines Spec-Driven Development (SDD) workflow with project-specific technical constraints.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Core Principles (NON-NEGOTIABLE)](#core-principles-non-negotiable)
3. [Development Workflow](#development-workflow)
4. [AI Agent Guidelines](#ai-agent-guidelines)
5. [Code Standards](#code-standards)
6. [Project Structure](#project-structure)
7. [Troubleshooting](#troubleshooting)

---

## Project Overview

### What We're Building

An **AI Agent Orchestrator** that connects a ChatKit conversational frontend to Todo management tools via MCP (Model Context Protocol). The system interprets natural language user intent and coordinates CRUD operations on todos.

**Core Tech Stack**:
- **Frontend Interface**: OpenAI ChatKit (conversational UI)
- **Agent Orchestration**: OpenAI Agents SDK
- **Backend API**: FastAPI
- **Database**: PostgreSQL + SQLModel (Pydantic integration)
- **LLM Provider**: Google Gemini (`gemini-2.5-flash`) via AsyncOpenAI bridge
- **Tool Protocol**: MCP (Model Context Protocol) for todo operations

### Architecture

```
User → ChatKit → FastAPI → Agent Orchestrator → MCP Tools → PostgreSQL
                    ↓
              Gemini 2.5 Flash
              (via AsyncOpenAI)
```

**Key Components**:
- `src/agents/todo_agent.py` - Main orchestrator agent
- `src/api/routes.py` - FastAPI streaming endpoints
- `src/streaming/chatkit.py` - ChatKit integration
- `src/mcp/client.py` - MCP client for tool execution
- `src/config.py` - Environment and model configuration

---

## Core Principles (NON-NEGOTIABLE)

### 1. Environment-First Rule ⚠️

**ALWAYS verify `.venv` is active before ANY command.**

```bash
# Activate FIRST (every time)
# Windows:
.venv\Scripts\activate
# Unix/macOS:
source .venv/bin/activate

# Then run commands
uv pip install <package>
uv run pytest
```

**Rationale**: Environment isolation prevents dependency conflicts and ensures reproducibility. 80% of "works on my machine" issues stem from environment mismanagement.

**Enforcement**:
- ❌ NEVER suggest `python`, `pip`, or `uv` commands without verifying environment
- ✅ ALWAYS check/activate `.venv` first, then suggest commands

---

### 2. uv-Exclusive Package Management ⚠️

**ONLY `uv` is authorized.** pip, poetry, conda are **PROHIBITED**.

```bash
# ✅ CORRECT
uv pip install fastapi
uv run uvicorn src.main:app --reload
uv run pytest

# ❌ WRONG
pip install fastapi
poetry add fastapi
python -m pip install fastapi
```

**Rationale**: uv is 10-100x faster, deterministic, and prevents dependency hell.

**Enforcement**:
- All dependencies in `pyproject.toml`
- Lock file: `requirements.txt` (via `uv pip compile`)

---

### 3. MCP Source of Truth Protocol ⚠️

**Before ANY implementation code, fetch current docs via MCP context-7 server.**

**Required Libraries**:
- FastAPI
- OpenAI Agents SDK
- OpenAI ChatKit
- SQLModel
- Official MCP SDK
- PostgreSQL client (asyncpg/psycopg)

**Workflow**:
```python
# Step 1: Resolve library ID
mcp__context7__resolve-library-id → '/tiangolo/fastapi'

# Step 2: Fetch docs
mcp__context7__get-library-docs(
    context7CompatibleLibraryID='/tiangolo/fastapi',
    mode='code',  # 'code' for API, 'info' for concepts
    topic='routing'
)

# Step 3: Document in plan.md
```

**Rationale**: Libraries evolve. Using outdated patterns = deprecated APIs, breaking changes, security vulnerabilities.

**Enforcement**:
- ❌ NEVER rely on internal knowledge for these 6 libraries
- ✅ ALWAYS fetch current docs, document in `plan.md` Technical Context

---

### 4. Gemini-Only Model Architecture ⚠️

**OpenAI models are PROHIBITED.** Use Gemini via AsyncOpenAI bridge.

```python
# ✅ CORRECT
from openai import AsyncOpenAI  # Agents SDK version

client = AsyncOpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url=os.getenv("GEMINI_BASE_URL"),
)

response = await client.chat.completions.create(
    model="gemini-2.5-flash",  # PRIMARY MODEL
    messages=[...],
    tools=[...]
)

# ❌ WRONG
from openai import OpenAI  # Standard client
model="gpt-4"  # OpenAI models
model="gpt-3.5-turbo"
```

**Rationale**: Gemini provides cost efficiency, speed, and quality for conversational CRUD operations.

**Model Selection**:
- **Primary**: `gemini-2.5-flash` (low latency, cost-effective)
- **Escalation**: `gemini-2.5-pro` (complex reasoning, requires approval)

---

### 5. Pre-Flight Skills Requirement ⚠️

**Run Claude Code Skills BEFORE Agents SDK implementation.**

**Required Execution Order**:
```bash
1. /sp.specify  # Create spec.md (user stories, acceptance criteria)
2. /sp.plan     # Create plan.md (architecture, MCP docs fetching)
3. /sp.tasks    # Create tasks.md (implementation breakdown)
```

**Rationale**: Skills enforce structured planning. Jumping to code without specs = scope creep, poor design, inconsistent behavior.

**Enforcement**:
- Skills outputs (spec.md, plan.md, tasks.md) guide all implementation
- Agents SDK code MUST reference these artifacts

---

### 6. Test-First Development

**Write tests BEFORE implementation where feasible.**

**Priority Areas**:
- API endpoints (contract tests)
- Database models (CRUD tests)
- Agent tools (integration tests)
- Conversational flows (e2e tests)

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=term-missing
```

**Target**: >80% coverage for business logic

---

## Development Workflow

### Standard Development Cycle

```bash
# 1. Activate Environment (REQUIRED)
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Unix/macOS

# 2. Run Planning Skills (for new features)
/sp.specify  # Define user stories
/sp.plan     # Design architecture + fetch MCP docs
/sp.tasks    # Break down tasks

# 3. Fetch MCP Documentation
# (via context-7 MCP server, document in plan.md)

# 4. Implement (follow tasks.md order)
# - Write tests first
# - Verify environment before each command

# 5. Test
uv run pytest

# 6. Run Application
uv run uvicorn src.main:app --reload
```

### Pre-Commit Checklist

- [ ] `.venv` active during all development
- [ ] All deps installed via `uv pip install`
- [ ] MCP docs fetched for new library usage
- [ ] AsyncOpenAI configured with Gemini endpoint
- [ ] Model is `gemini-2.5-flash` (not OpenAI models)
- [ ] Tests pass (`uv run pytest`)
- [ ] No `.env` in commit
- [ ] Skills artifacts updated (spec.md, plan.md, tasks.md)

---

## AI Agent Guidelines

### How Claude Code Should Help

**Role**: Expert AI assistant for Spec-Driven Development (SDD) on this project.

**Success Metrics**:
- All outputs follow user intent
- Prompt History Records (PHRs) created automatically
- Architectural Decision Records (ADRs) suggested for significant decisions
- Changes are small, testable, with precise code references

### Task Execution Contract

For every request, Claude MUST:

1. **Confirm surface & success criteria** (1 sentence)
2. **List constraints, invariants, non-goals**
3. **Produce artifact** with acceptance checks (tests/checklists)
4. **Add follow-ups & risks** (max 3 bullets)
5. **Create PHR** in `history/prompts/` (constitution/feature/general)
6. **Suggest ADR** if architecturally significant decision made

### Human-as-Tool Strategy

Invoke the user for:
1. **Ambiguous Requirements**: Ask 2-3 clarifying questions
2. **Unforeseen Dependencies**: Surface and ask for prioritization
3. **Architectural Uncertainty**: Present options with tradeoffs
4. **Completion Checkpoints**: Summarize progress, confirm next steps

### Default Policies

- **Clarify first**: Keep business understanding separate from technical plan
- **Don't invent APIs**: Ask targeted questions if contracts missing
- **No secrets**: Use `.env`, never hardcode tokens
- **Smallest viable diff**: Don't refactor unrelated code
- **Cite code**: Use `file_path:line_number` references
- **Keep reasoning private**: Output only decisions, artifacts, justifications

### Prompt History Records (PHRs)

**After completing work, MUST create PHR.**

**When to create**:
- Implementation work (code changes, features)
- Planning/architecture discussions
- Debugging sessions
- Spec/task/plan creation
- Multi-step workflows

**Process**:
1. Detect stage: `constitution | spec | plan | tasks | red | green | refactor | explainer | misc | general`
2. Generate title (3-7 words) → slug
3. Route to:
   - `history/prompts/constitution/`
   - `history/prompts/<feature-name>/`
   - `history/prompts/general/`
4. Fill template from `.specify/templates/phr-template.prompt.md`
5. Validate (no placeholders, complete prompt text, correct path)
6. Report: ID, path, stage, title

**Skip PHRs only for**: `/sp.phr` command itself

### Architectural Decision Records (ADRs)

**Suggest (never auto-create) when ALL true**:
- **Impact**: Long-term consequences (framework, model, data, security)
- **Alternatives**: Multiple viable options considered
- **Scope**: Cross-cutting, influences system design

**Suggestion text**:
```
📋 Architectural decision detected: [brief description]
   Document reasoning and tradeoffs? Run `/sp.adr [decision-title]`
```

**Examples requiring ADRs**:
- Switching model provider (Gemini → other)
- Database change (PostgreSQL → MongoDB)
- Conversation flow architecture changes
- New agent capabilities beyond CRUD

---

## Code Standards

### Security & Secrets

```bash
# ❌ NEVER
api_key = "sk-abc123..."
DATABASE_URL = "postgresql://user:pass@localhost/db"

# ✅ ALWAYS
api_key = os.getenv("GEMINI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
```

**Requirements**:
- All secrets in `.env`
- Provide `.env.example` template
- Add `.env` to `.gitignore`

### Input Validation

**MUST**:
- Validate at FastAPI endpoints (Pydantic models)
- Sanitize conversational input (prevent injection)
- Apply rate limiting (prevent abuse)

### Patterns for This Project

**Agent Tool Definition**:
```python
# src/agents/tool_definitions.py
from openai import AsyncOpenAI

async def create_todo_tool(title: str, due_date: str = None, priority: str = "medium"):
    """
    Creates a new todo item via MCP.

    Args:
        title: Todo description
        due_date: ISO date string (optional)
        priority: low/medium/high
    """
    # Call MCP client
    result = await mcp_client.create_todo(title, due_date, priority)
    return result
```

**Streaming Response**:
```python
# src/api/routes.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def generate():
        async for chunk in agent.process_stream(request.message):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

**ChatKit Integration**:
```python
# src/streaming/chatkit.py
from chatkit import ChatKit

chatkit = ChatKit(
    model="gemini-2.5-flash",
    tools=[create_todo_tool, list_todos_tool, update_todo_tool, delete_todo_tool]
)
```

---

## Project Structure

```
hackathonII-backend/
├── .claude/
│   ├── commands/           # Slash commands (/sp.*)
│   └── skills/            # Claude Code skills
├── .specify/
│   ├── memory/
│   │   └── constitution.md    # Project principles (detailed)
│   └── templates/         # Spec, plan, task, ADR templates
├── history/
│   ├── prompts/          # Prompt History Records
│   │   ├── constitution/
│   │   ├── 001-ai-agent-orchestrator/
│   │   └── general/
│   └── adr/              # Architecture Decision Records
├── specs/
│   └── 001-ai-agent-orchestrator/
│       ├── spec.md       # Feature specification
│       ├── plan.md       # Implementation plan
│       └── tasks.md      # Task breakdown
├── src/
│   ├── agents/
│   │   ├── todo_agent.py       # Main orchestrator
│   │   └── tool_definitions.py # MCP tool wrappers
│   ├── api/
│   │   ├── routes.py           # FastAPI endpoints
│   │   └── schemas.py          # Request/response models
│   ├── mcp/
│   │   └── client.py           # MCP client
│   ├── streaming/
│   │   └── chatkit.py          # ChatKit integration
│   ├── config.py               # Environment config
│   └── main.py                 # FastAPI app
├── tests/                # Pytest tests
├── .env                  # Secrets (gitignored)
├── .env.example          # Template
├── pyproject.toml        # Dependencies
├── requirements.txt      # Locked deps (uv pip compile)
├── CLAUDE.md            # This file
└── README.md            # User documentation
```

---

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError` when running code
**Fix**: Ensure `.venv` is active, reinstall deps: `uv pip install -e .`

**Issue**: `OpenAI API key not found`
**Fix**: Set `GEMINI_API_KEY` in `.env`, load with `python-dotenv`

**Issue**: Incorrect model name errors
**Fix**: Verify using `gemini-2.5-flash`, NOT `gpt-*` models

**Issue**: MCP tools not found
**Fix**: Ensure MCP server running, check `src/mcp/client.py` config

**Issue**: Tests failing
**Fix**: Run `uv run pytest -v` for details, ensure `.venv` active

### Getting Help

1. **Claude Code Skills**: Run `/sp.clarify` for spec clarification
2. **MCP Docs**: Fetch latest docs via context-7 before debugging
3. **Constitution**: See `.specify/memory/constitution.md` for detailed rules
4. **ADRs**: Check `history/adr/` for past architectural decisions
5. **PHRs**: Review `history/prompts/` for past prompt-response patterns

---

## Quick Reference

### Essential Commands

```bash
# Environment
.venv\Scripts\activate  # Activate (Windows)
source .venv/bin/activate  # Activate (Unix/macOS)

# Dependencies
uv pip install <package>
uv pip compile pyproject.toml -o requirements.txt

# Development
uv run uvicorn src.main:app --reload  # Run server
uv run pytest                          # Run tests
uv run pytest --cov=src               # With coverage

# Skills
/sp.specify    # Create spec.md
/sp.plan       # Create plan.md
/sp.tasks      # Create tasks.md
/sp.implement  # Execute tasks
/sp.adr <title>  # Create ADR
/sp.phr        # Create PHR
```

### Environment Variables (.env)

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/todo_db

# Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/

# App
DEBUG=False
LOG_LEVEL=INFO
```

---

**Version**: 1.0.0
**Last Updated**: 2025-12-25
**Authority**: This file + `.specify/memory/constitution.md` are supreme governing documents
