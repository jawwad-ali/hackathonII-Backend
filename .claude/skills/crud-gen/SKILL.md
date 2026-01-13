---
name: crud-gen
description: Generate production-ready FastAPI CRUD endpoints with SQLModel. Creates complete Create, Read, Update, Delete operations following project patterns.
---

# FastAPI CRUD Generator

## Purpose
Auto-scaffold complete CRUD endpoints for SQLModel entities with pagination, validation, error handling, and proper session management.

## Core Rules
1. **Context7 First**: Query `/websites/fastapi_tiangolo` and `/websites/sqlmodel_tiangolo` for latest patterns
2. **uv Only**: Never suggest pip commands
3. **Async Pattern**: All operations use `async def` with proper session handling
4. **Type Safety**: Use Python 3.10+ union types (`int | None`) and `Annotated`
5. **Response Models**: Separate Create, Update, Public schemas

## Workflow
1. **Analyze Target**: Identify SQLModel entity to scaffold
2. **Query Docs**: Fetch Context7 patterns for FastAPI + SQLModel CRUD
3. **Generate Schemas**:
   ```python
   class TodoBase(SQLModel):
       title: str = Field(max_length=200, index=True)
       description: str | None = None

   class TodoCreate(TodoBase):
       pass

   class TodoUpdate(SQLModel):
       title: str | None = None
       description: str | None = None
       status: TodoStatus | None = None

   class TodoPublic(TodoBase):
       id: int
       status: TodoStatus
       created_at: datetime
   ```

4. **Generate Endpoints**:
   - `POST /{resource}/` - Create with validation
   - `GET /{resource}/` - List with pagination (offset, limit ≤100)
   - `GET /{resource}/{id}` - Get by ID with 404 handling
   - `PATCH /{resource}/{id}` - Partial update with `model_dump(exclude_unset=True)`
   - `DELETE /{resource}/{id}` - Soft or hard delete

5. **Add Dependencies**:
   ```python
   SessionDep = Annotated[Session, Depends(get_session)]
   ```

6. **Include Error Handling**:
   - 404 for not found
   - 422 for validation errors
   - Proper session commit/rollback

## Output Format
- Complete router file with all 5 CRUD operations
- Includes imports, schemas, and endpoints
- Ready to integrate into existing FastAPI app

## Example Usage
User: "Generate CRUD for the Todo model"
Action: Query Context7 → Generate TodoCreate, TodoUpdate, TodoPublic → Create 5 endpoints → Return complete code

## Quality Checks
- ✓ All endpoints use SessionDep
- ✓ Pagination on list (default limit=100, max=100)
- ✓ HTTPException for 404 errors
- ✓ model_validate() for create
- ✓ model_dump(exclude_unset=True) for update
- ✓ session.refresh() after mutations
