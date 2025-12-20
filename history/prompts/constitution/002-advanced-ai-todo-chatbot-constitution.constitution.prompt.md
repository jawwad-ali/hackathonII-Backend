---
id: 002
title: Advanced AI-Todo Chatbot Constitution
stage: constitution
date: 2025-12-20
surface: agent
model: claude-sonnet-4-5
feature: none
branch: main
user: Ali jawwad
command: /sp.constitution
labels: ["constitution", "ai-todo-chatbot", "mcp", "uv", "gemini", "agents-sdk"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - .specify/memory/constitution.md
tests:
 - N/A
---

## Prompt

Act as a Lead Software Architect. Create a formal CONSTITUTION.md file for our project: 'Advanced AI-Todo Chatbot'. This constitution must serve as the ground truth for all agentic behavior and code generation. Include the following mandatory directives:

Core Mission: Define the app as a conversational CRUD interface for Todo management using OpenAI ChatKit and Agents SDK.

Package & Environment Management: > - Mandate the use of uv exclusively for all dependency management.

Require a strict "Environment-First" rule: The agent must always verify or activate the .venv before suggesting installation or execution commands.

The 'Source of Truth' Protocol (MCP): > - Before writing any implementation code, the agent MUST call the context-7 MCP server to fetch the latest documentation for: FastAPI, OpenAI Agents SDK, OpenAI ChatKit, SQLModel, and Postgres.

Pre-Flight Skills: > - Explicitly mandate the use of Claude Code Skills (SKILLS/SKILL.md) as a prerequisite before the Agents SDK logic begins processing.

Model & Connectivity Architecture: > - Prohibit the use of the standard OpenAI models/endpoints.

Force the use of AsyncOpenAI from the Agents SDK to bridge to Google Gemini.

Primary Model target: gemini-2.5-flash.

## Response snapshot

Created comprehensive constitution (v2.0.0) for Advanced AI-Todo Chatbot with user-specified mandatory directives:

**Six Core Principles (NON-NEGOTIABLE)**:
1. **Environment-First Rule**: Always verify/activate `.venv` before any `uv` or `python` commands
2. **Source of Truth Protocol (MCP)**: Fetch latest docs from context-7 MCP server for FastAPI, Agents SDK, ChatKit, SQLModel, Postgres before ANY implementation
3. **Pre-Flight Skills Requirement**: Execute Claude Code Skills (`/sp.specify`, `/sp.plan`, `/sp.tasks`) before Agents SDK integration
4. **uv-Exclusive Package Management**: uv ONLY for dependencies; pip/poetry/conda PROHIBITED
5. **Model & Connectivity Architecture**: AsyncOpenAI with Gemini endpoint; OpenAI models PROHIBITED; `gemini-2.5-flash` as primary model
6. **Test-First Development**: pytest for all testing; >80% coverage target

**Additional Sections**:
- **Core Mission & Architecture**: Conversational CRUD for Todo management using ChatKit + Agents SDK + FastAPI + SQLModel + PostgreSQL
- **Package & Environment Management**: uv setup, usage, environment variables (.env)
- **Source of Truth Protocol (MCP)**: 3-step workflow (Resolve IDs → Fetch Docs → Document in artifacts)
- **Pre-Flight Skills**: Required execution order and skill outputs as prerequisites
- **Model & Connectivity Architecture**: AsyncOpenAI configuration patterns, prohibited patterns, model selection rationale
- **Development Workflow**: Standard cycle from environment activation through testing
- **Security & Compliance**: Secret management, input validation
- **Governance**: Constitution authority, amendment process, compliance review, ADR workflow

**Key Enforcement Mechanisms**:
- Pre-commit checklist with 8 validation points
- Constitution Check in templates (plan.md, spec.md, tasks.md)
- MCP documentation validation before merge
- Periodic audits (monthly dependency review, quarterly constitution review)

## Outcome

- ✅ Impact: Established project-specific ground truth for Advanced AI-Todo Chatbot with strict compliance requirements
- 🧪 Tests: N/A (constitution is governance documentation)
- 📁 Files: Updated .specify/memory/constitution.md (v1.0.0 → 2.0.0, MAJOR version bump)
- 🔁 Next prompts: Update CLAUDE.md and README.md per Sync Impact Report; then run `/sp.specify` to create first feature spec
- 🧠 Reflection: Constitution successfully captures all user-specified mandatory directives with enforcement mechanisms, rationale, and compliance checklists

## Evaluation notes (flywheel)

- Failure modes observed: None (user requirements fully specified)
- Graders run and results (PASS/FAIL): Manual validation PASS (all user directives captured, no unresolved placeholders, version coherent, comprehensive enforcement)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Validate MCP workflow in practice during `/sp.plan` execution
