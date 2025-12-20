<!--
Sync Impact Report:
Version: 1.0.0 → 2.0.0
Modified Principles:
  - Complete replacement of generic principles with project-specific directives
  - Test-First Development → remains but contextualized for Todo CRUD
  - Added: Core Mission, Package Management, Source of Truth Protocol, Pre-Flight Skills, Model Architecture
Added Sections:
  - Core Mission & Architecture
  - Package & Environment Management (uv-exclusive)
  - Source of Truth Protocol (MCP)
  - Pre-Flight Skills Requirements
  - Model & Connectivity Architecture
  - Development Workflow
Removed Sections:
  - Generic principles (Independent User Stories, Minimal Complexity as standalone)
  - Generic security section (now integrated into specific directives)
Templates Requiring Updates:
  ✅ plan-template.md - Will require MCP verification step in Constitution Check
  ✅ spec-template.md - Must reference conversational CRUD interface patterns
  ✅ tasks-template.md - Must include MCP documentation fetching and uv environment verification
  ⚠ CLAUDE.md - Should reference this constitution for MCP and Skills requirements
  ⚠ README.md - Should document uv setup and environment activation
Follow-up TODOs:
  - Update CLAUDE.md to enforce MCP context-7 calls before implementation
  - Update README.md with uv installation and .venv activation instructions
-->

# Advanced AI-Todo Chatbot Constitution

**Project**: Advanced AI-Todo Chatbot
**Purpose**: Conversational CRUD interface for Todo management using OpenAI ChatKit and Agents SDK

This constitution serves as the **ground truth** for all agentic behavior and code generation. All agents, developers, and automated processes MUST comply with these directives.

## Core Mission & Architecture

### Project Definition

This application is a **conversational CRUD interface for Todo management** built on:
- **OpenAI ChatKit**: Conversational interface layer
- **OpenAI Agents SDK**: Agentic orchestration and tool use
- **FastAPI**: Backend API framework
- **SQLModel**: Database ORM with Pydantic integration
- **PostgreSQL**: Persistent data storage
- **Google Gemini (gemini-2.5-flash)**: Primary LLM model via AsyncOpenAI bridge

**Rationale**: The conversational interface abstracts traditional CRUD operations into natural language interactions, making todo management intuitive and accessible. The Agents SDK enables autonomous task orchestration beyond simple request-response patterns.

## Core Principles

### I. Environment-First Rule (NON-NEGOTIABLE)

The agent MUST **always verify or activate the `.venv`** before suggesting any installation or execution commands.

**Enforcement**:
- Before ANY `uv pip install`, `uv run`, or `python` command: verify `.venv` is active
- If `.venv` is not active, MUST provide activation command first:
  - Windows: `.venv\Scripts\activate`
  - Unix/macOS: `source .venv/bin/activate`
- Never assume environment state; always validate first

**Rationale**: Environment isolation prevents dependency conflicts, ensures reproducible builds, and protects system Python from corruption. This is non-negotiable because environment mismanagement causes 80% of "works on my machine" failures.

### II. Source of Truth Protocol (MCP) (NON-NEGOTIABLE)

**Before writing ANY implementation code**, the agent MUST call the **context-7 MCP server** to fetch the latest documentation for:
1. **FastAPI**
2. **OpenAI Agents SDK**
3. **OpenAI ChatKit**
4. **Official MCP SDK**
5. **SQLModel**
6. **PostgreSQL** (Postgres client libraries)

**Enforcement**:
- Use `mcp__context7__resolve-library-id` to get library IDs
- Use `mcp__context7__get-library-docs` with `mode='code'` for API references
- Use `mcp__context7__get-library-docs` with `mode='info'` for conceptual guides
- Document fetched documentation in plan.md Technical Context section
- NEVER rely on internal knowledge cutoff for these libraries—always fetch current docs

**Rationale**: Libraries evolve rapidly. Using outdated API patterns leads to deprecation warnings, breaking changes, and security vulnerabilities. MCP ensures implementation matches current best practices.

### III. Pre-Flight Skills Requirement (NON-NEGOTIABLE)

The agent MUST use **Claude Code Skills** (`SKILLS/SKILL.md`) as a **prerequisite before the Agents SDK logic begins processing**.

**Enforcement**:
- Check for available skills in `.claude/commands/` or `SKILLS/` directory
- Execute relevant skills (e.g., `/sp.specify`, `/sp.plan`, `/sp.tasks`) before implementation
- Skills establish architectural decisions and task breakdowns that guide Agents SDK integration
- Document skill execution outputs in project artifacts (spec.md, plan.md, tasks.md)

**Rationale**: Skills provide structured workflows for specification, planning, and task decomposition. Running skills first ensures Agents SDK integration aligns with project architecture and requirements rather than ad-hoc implementation.

### IV. uv-Exclusive Package Management (NON-NEGOTIABLE)

**uv** is the ONLY authorized tool for dependency management. pip, poetry, conda, and other package managers are **PROHIBITED**.

**Enforcement**:
- Install dependencies: `uv pip install <package>`
- Run scripts: `uv run <command>`
- Manage project: `uv` commands exclusively
- NEVER suggest `pip install`, `poetry add`, or other package manager commands
- All dependencies MUST be declared in `pyproject.toml`

**Rationale**: uv is 10-100x faster than pip, provides deterministic dependency resolution, and integrates seamlessly with modern Python project standards (PEP 517/518). Mixing package managers causes dependency hell.

### V. Model & Connectivity Architecture (NON-NEGOTIABLE)

**Standard OpenAI models and endpoints are PROHIBITED.** The agent MUST use:
- **AsyncOpenAI** from the OpenAI Agents SDK
- **Bridge to Google Gemini** instead of OpenAI models
- **Primary model target**: `gemini-2.5-flash`

**Enforcement**:
- Import: `from openai import AsyncOpenAI` (Agents SDK version)
- Configure base_url to point to Google Gemini endpoint (via compatible API)
- Set model parameter to `"gemini-2.5-flash"`
- NEVER use `gpt-4`, `gpt-3.5-turbo`, or other OpenAI model identifiers
- Document model configuration in environment variables (`.env`)

**Rationale**: Google Gemini provides cost efficiency, faster response times for flash models, and competitive quality. Using AsyncOpenAI maintains OpenAI SDK compatibility while leveraging alternative model providers.

### VI. Test-First Development

Tests MUST be written before implementation where feasible, especially for:
- **API endpoints**: Contract tests validating request/response schemas
- **Database models**: CRUD operation tests
- **Agent tools**: Integration tests for tool execution
- **Conversational flows**: End-to-end tests simulating user interactions

**Enforcement**:
- Use pytest for all testing
- Test files in `tests/` directory (mirroring `src/` structure)
- Run tests with: `uv run pytest`
- Aim for >80% coverage of business logic

**Rationale**: Test-first ensures correctness, prevents regressions, and creates living documentation. For conversational AI, tests validate intent handling and tool execution reliability.

## Package & Environment Management

### uv Setup & Usage

**Installation** (if not installed):
```bash
# Install uv globally
pip install uv
```

**Project Initialization**:
```bash
# Create virtual environment
uv venv

# Activate environment (REQUIRED before any commands)
# Windows:
.venv\Scripts\activate
# Unix/macOS:
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
# OR install from pyproject.toml
uv pip install -e .
```

**Dependency Management**:
- Add dependencies to `pyproject.toml` under `[project.dependencies]`
- Dev dependencies under `[project.optional-dependencies.dev]`
- Lock dependencies: `uv pip compile pyproject.toml -o requirements.txt`

### Environment Variables

All sensitive configuration MUST use environment variables via `.env`:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/todo_db

# Gemini API
GEMINI_API_KEY=your_gemini_api_key
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/

# Application
DEBUG=False
LOG_LEVEL=INFO
```

**NEVER commit `.env` to version control.** Provide `.env.example` template.

## Source of Truth Protocol (MCP)

### Required MCP Workflow

**Step 1: Resolve Library IDs** (before implementation planning)
```python
# For each core dependency, resolve library ID:
- FastAPI
- OpenAI Agents SDK
- OpenAI ChatKit
- SQLModel
- Postgres (psycopg or asyncpg)
```

**Step 2: Fetch Documentation** (during implementation)
```python
# Use mode='code' for API references (default)
# Use mode='info' for architectural guidance

# Example: FastAPI endpoint patterns
get-library-docs(context7CompatibleLibraryID='/tiangolo/fastapi', mode='code', topic='routing')

# Example: Agents SDK tool creation
get-library-docs(context7CompatibleLibraryID='/openai/openai-agents-sdk', mode='code', topic='tools')
```

**Step 3: Document in Artifacts**
- Record fetched documentation references in `plan.md` Technical Context
- Note version-specific patterns or breaking changes
- Link to official docs for manual review if needed

### Validation

Before merging any implementation PR:
- [ ] MCP documentation fetched for all new library usage
- [ ] Implementation matches fetched API patterns (not internal knowledge)
- [ ] Version compatibility documented in plan.md

## Pre-Flight Skills

### Required Skills Execution Order

1. **`/sp.specify`**: Create feature specification (spec.md)
   - Define user stories as conversational interactions
   - Specify CRUD operations as natural language intents
   - Document acceptance criteria for chatbot responses

2. **`/sp.plan`**: Create implementation plan (plan.md)
   - Fetch MCP documentation for all dependencies (REQUIRED)
   - Design ChatKit conversation flows
   - Design Agents SDK tool architecture
   - Plan database schema (SQLModel models)
   - Plan FastAPI endpoints

3. **`/sp.tasks`**: Generate task list (tasks.md)
   - Include MCP documentation fetching tasks
   - Include environment verification tasks
   - Break down implementation by user story
   - Specify test tasks for each component

### Skill Outputs as Prerequisites

Agents SDK integration MUST reference:
- **User stories** from spec.md (what intents to handle)
- **Architecture decisions** from plan.md (tool design, model configuration)
- **Task breakdown** from tasks.md (implementation order)

**Rationale**: Skills enforce disciplined planning. Jumping directly to Agents SDK code without specification leads to scope creep, inconsistent conversation handling, and poor tool design.

## Model & Connectivity Architecture

### AsyncOpenAI Configuration

```python
from openai import AsyncOpenAI
import os

client = AsyncOpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url=os.getenv("GEMINI_BASE_URL"),  # Gemini endpoint
)

# Usage
response = await client.chat.completions.create(
    model="gemini-2.5-flash",  # PRIMARY MODEL
    messages=[...],
    tools=[...],  # Agent tools
)
```

### Prohibited Patterns

**NEVER**:
```python
# ❌ WRONG: Standard OpenAI client
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ❌ WRONG: OpenAI models
model="gpt-4"
model="gpt-3.5-turbo"

# ❌ WRONG: Synchronous client (use async)
client = OpenAI(...)
```

**ALWAYS**:
```python
# ✅ CORRECT: Agents SDK AsyncOpenAI
from openai import AsyncOpenAI
client = AsyncOpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url=os.getenv("GEMINI_BASE_URL"),
)

# ✅ CORRECT: Gemini model
model="gemini-2.5-flash"
```

### Model Selection Rationale

- **gemini-2.5-flash**: Primary model for conversational CRUD operations
  - Cost-effective for high-volume todo management interactions
  - Low latency for real-time chat responsiveness
  - Sufficient reasoning for tool use (CRUD operations)

**If gemini-2.5-flash is insufficient** (complex reasoning required):
- Escalate to `gemini-2.5-pro` for specific complex operations
- Document escalation criteria in plan.md
- Require explicit user approval for cost increase

## Development Workflow

### Standard Development Cycle

1. **Activate environment**:
   ```bash
   # Windows
   .venv\Scripts\activate
   # Unix/macOS
   source .venv/bin/activate
   ```

2. **Run Skills** (planning phase):
   ```bash
   /sp.specify  # Create spec.md
   /sp.plan     # Create plan.md (includes MCP fetching)
   /sp.tasks    # Create tasks.md
   ```

3. **Fetch MCP Documentation** (before implementation):
   - Use context-7 MCP server for all core dependencies
   - Document fetched docs in plan.md

4. **Implement** (execution phase):
   - Follow tasks.md order
   - Write tests first (when applicable)
   - Verify environment before each command

5. **Test**:
   ```bash
   uv run pytest
   ```

6. **Run Application**:
   ```bash
   uv run uvicorn src.main:app --reload
   ```

### Pre-Commit Checklist

- [ ] Environment was active during all development
- [ ] All dependencies installed via `uv pip install`
- [ ] MCP documentation fetched for new library usage
- [ ] AsyncOpenAI configured with Gemini endpoint
- [ ] Model is `gemini-2.5-flash` (not OpenAI models)
- [ ] Tests pass (`uv run pytest`)
- [ ] No `.env` file in commit
- [ ] Skills execution outputs updated (if changed)

## Security & Compliance

### Secret Management

- **MUST NOT**: Hardcode API keys, database credentials, tokens
- **MUST**: Use environment variables via `.env`
- **MUST**: Provide `.env.example` template (with dummy values)
- **MUST**: Add `.env` to `.gitignore`

### Input Validation

- **MUST**: Validate all user input at FastAPI endpoints
- **MUST**: Sanitize conversational input to prevent injection attacks
- **MUST**: Use Pydantic models for request/response validation
- **MUST**: Apply rate limiting to prevent abuse

## Governance

### Constitution Authority

This constitution is the **supreme governing document** for the Advanced AI-Todo Chatbot project. All code, documentation, and processes MUST comply.

**In case of conflict**: Constitution directives override:
1. General best practices
2. Library recommendations (unless from MCP)
3. Agent internal knowledge
4. Developer preferences

### Amendment Process

1. **Proposal**: Submit amendment with rationale and impact analysis
2. **Review**: Team review (or project owner approval for solo projects)
3. **Version Bump**: Follow semantic versioning:
   - **MAJOR**: Backward-incompatible principle changes (e.g., switching from uv to another tool)
   - **MINOR**: New principles or material expansions
   - **PATCH**: Clarifications, wording improvements
4. **Propagation**: Update dependent templates and documentation
5. **Update Dates**: Set LAST_AMENDED_DATE to current date

### Compliance Review

**Before merge**:
- [ ] Environment-First rule followed (`.venv` verified)
- [ ] MCP documentation fetched for new library usage
- [ ] uv used exclusively (no pip/poetry commands)
- [ ] AsyncOpenAI with Gemini configured (not OpenAI)
- [ ] Skills executed for planning phase
- [ ] Tests written and passing

**Periodic audits**:
- Monthly review of dependency versions (via MCP)
- Quarterly constitution effectiveness review
- Update MCP documentation references when libraries release major versions

### Architectural Decision Records (ADRs)

For architecturally significant decisions:
- **Impact**: Long-term consequences (framework choice, model architecture, data persistence)
- **Alternatives**: Multiple viable options considered
- **Scope**: Cross-cutting system design influence

**Process**: Suggest ADR creation with: `"📋 Architectural decision detected: [brief]. Document? Run /sp.adr [decision-title]"`

Examples requiring ADRs:
- Switching from Gemini to another model provider
- Changing database (PostgreSQL to MongoDB)
- Modifying conversation flow architecture
- Adding new agent capabilities beyond CRUD

**Version**: 2.0.0 | **Ratified**: 2025-12-20 | **Last Amended**: 2025-12-20
