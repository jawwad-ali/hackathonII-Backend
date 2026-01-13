---
name: mcp-scaffold
description: Scaffold FastMCP tool implementations with database integration, error handling, and test session support. Generates production-ready MCP tools.
---

# MCP Tool Scaffolder

## Purpose
Generate FastMCP tool implementations following project conventions with proper error handling, logging, JSON serialization, and test session support.

## Core Rules
1. **Context7 First**: Query FastMCP patterns before generation (if available, else use project patterns)
2. **Tool Decorator**: Use `@mcp.tool()` with descriptive docstrings for LLM
3. **Test Support**: Include `_test_session` parameter for pytest integration
4. **JSON Returns**: Always return `json.dumps()` with success/error structure
5. **Error Handling**: Try-catch with logger.error and fallback response

## Workflow
1. **Identify Operation**: Understand CRUD operation (create/read/update/delete/search)
2. **Read Existing Tools**: Check `src/mcp_server/tools/` for patterns
3. **Generate Tool**:
   ```python
   import json
   import logging
   from typing import Optional
   from sqlmodel import Session, select
   from ..database import engine
   from ..models import Todo, TodoStatus

   logger = logging.getLogger(__name__)

   @mcp.tool()
   def operation_name(
       required_param: str,
       optional_param: str | None = None,
       _test_session: Optional[Session] = None
   ) -> str:
       """
       Clear description of what this tool does for the LLM.

       Args:
           required_param: Description
           optional_param: Description
       """
       session = _test_session or Session(engine)

       try:
           # Database operation
           result = session.exec(select(Todo).where(...)).first()

           if not result:
               return json.dumps({
                   "success": False,
                   "error": "Resource not found"
               })

           session.commit()

           return json.dumps({
               "success": True,
               "data": {
                   "id": result.id,
                   "title": result.title
               }
           })

       except Exception as e:
           logger.error(f"Error in operation_name: {e}")
           if not _test_session:
               session.rollback()
           return json.dumps({
               "success": False,
               "error": str(e)
           })
       finally:
           if not _test_session:
               session.close()
   ```

4. **Register in server.py**: Add import and ensure tool is loaded

## Tool Patterns

### Create Operations
- Validate required fields
- Set defaults (status=ACTIVE, timestamps)
- Return created entity with ID

### Read Operations
- Support filtering (status, date ranges)
- Implement pagination (offset, limit)
- Return list or single entity

### Update Operations
- Check entity exists (404 if not)
- Only update provided fields
- Refresh and return updated entity

### Delete Operations
- Check entity exists
- Soft delete preferred (status=ARCHIVED)
- Return success confirmation

### Search Operations
- Support multiple filters (title, description, status)
- Case-insensitive search with ILIKE
- Return matched count + results

## Output Format
- Complete tool file with imports
- Proper type hints and docstrings
- Error handling and logging
- Test session support
- JSON response structure

## Quality Checks
- ✓ Docstring explains tool purpose for LLM
- ✓ _test_session parameter present
- ✓ Try-except with logger.error
- ✓ Returns JSON with success/error structure
- ✓ Session closed in finally block (if not test)
- ✓ Proper SQLModel query patterns

## Example Usage
User: "Scaffold update_todo MCP tool"
Action: Read existing tools → Generate update_todo.py with validation, error handling, test support → Return complete implementation
