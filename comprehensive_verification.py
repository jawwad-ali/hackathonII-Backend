"""Comprehensive System Verification - Check EVERYTHING"""
import os
import sys
from pathlib import Path

print("="*80)
print(" COMPREHENSIVE SYSTEM VERIFICATION ".center(80))
print("="*80)
print("\nChecking all components from environment to logs to functionality...\n")

results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def test_check(category, check_name, condition, details=""):
    """Record test result"""
    if condition:
        results["passed"].append(f"{category}: {check_name}")
        print(f"[PASS] {category}: {check_name}")
        if details:
            print(f"       {details}")
    else:
        results["failed"].append(f"{category}: {check_name}")
        print(f"[FAIL] {category}: {check_name}")
        if details:
            print(f"       {details}")
    return condition

def test_warning(category, check_name, details=""):
    """Record warning"""
    results["warnings"].append(f"{category}: {check_name}")
    print(f"[WARN] {category}: {check_name}")
    if details:
        print(f"       {details}")

# ============================================================================
# 1. ENVIRONMENT FILES CHECK
# ============================================================================
print("\n" + "="*80)
print("1. ENVIRONMENT FILES")
print("="*80)

# Check .env exists
env_exists = os.path.exists(".env")
test_check("Environment", ".env file exists", env_exists,
           "Found at project root" if env_exists else "Missing - server may use defaults")

# Check .env.example exists
env_example_exists = os.path.exists(".env.example")
test_check("Environment", ".env.example file exists", env_example_exists,
           "Template available for new developers")

if env_example_exists:
    with open(".env.example", "r", encoding="utf-8") as f:
        env_example_content = f.read()

    # Check critical variables are documented
    critical_vars = [
        "GEMINI_API_KEY",
        "GEMINI_BASE_URL",
        "GEMINI_MODEL",
        "MCP_SERVER_COMMAND",
        "MCP_SERVER_ARGS",
        "MCP_SERVER_TIMEOUT",
        "MCP_TRANSPORT_TYPE",  # Our new addition!
        "APP_HOST",
        "APP_PORT",
        "LOG_LEVEL"
    ]

    for var in critical_vars:
        test_check("Environment", f"{var} documented in .env.example",
                   var in env_example_content)

# ============================================================================
# 2. CONFIGURATION LOADING
# ============================================================================
print("\n" + "="*80)
print("2. CONFIGURATION LOADING")
print("="*80)

try:
    from src.config import settings
    test_check("Config", "Settings module imports", True, "src.config loads successfully")

    # Check all critical settings
    config_checks = {
        "GEMINI_API_KEY": settings.GEMINI_API_KEY,
        "GEMINI_BASE_URL": settings.GEMINI_BASE_URL,
        "GEMINI_MODEL": settings.GEMINI_MODEL,
        "MCP_TRANSPORT_TYPE": settings.MCP_TRANSPORT_TYPE,
        "MCP_SERVER_COMMAND": settings.MCP_SERVER_COMMAND,
        "MCP_SERVER_ARGS": settings.MCP_SERVER_ARGS,
        "MCP_SERVER_TIMEOUT": settings.MCP_SERVER_TIMEOUT,
        "APP_HOST": settings.APP_HOST,
        "APP_PORT": settings.APP_PORT,
        "LOG_LEVEL": settings.LOG_LEVEL,
    }

    for key, value in config_checks.items():
        test_check("Config", f"{key} loaded", value is not None,
                   f"Value: {value if key != 'GEMINI_API_KEY' else '***HIDDEN***'}")

    # Validate specific values
    test_check("Config", "MCP_TRANSPORT_TYPE is valid",
               settings.MCP_TRANSPORT_TYPE in ["stdio", "sse"],
               f"Value: {settings.MCP_TRANSPORT_TYPE}")

    test_check("Config", "LOG_LEVEL is valid",
               settings.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
               f"Value: {settings.LOG_LEVEL}")

    test_check("Config", "MCP_SERVER_TIMEOUT is reasonable",
               0 < settings.MCP_SERVER_TIMEOUT <= 30,
               f"Value: {settings.MCP_SERVER_TIMEOUT}s")

except Exception as e:
    test_check("Config", "Settings module imports", False, f"Error: {e}")

# ============================================================================
# 3. LOGGING SYSTEM
# ============================================================================
print("\n" + "="*80)
print("3. LOGGING SYSTEM")
print("="*80)

try:
    from src.observability.logging import logger, setup_logging
    test_check("Logging", "Logging module imports", True)

    # Test logger functionality
    import logging
    test_logger = logging.getLogger("test_verification")

    # Verify logger can log at different levels
    test_logger.info("Test INFO log")
    test_logger.debug("Test DEBUG log")
    test_logger.warning("Test WARNING log")

    test_check("Logging", "Logger can write logs", True,
               "Successfully wrote test logs at multiple levels")

    # Check if structured logging is configured
    import inspect
    logging_source = inspect.getsource(setup_logging) if hasattr(setup_logging, '__call__') else ""

    has_json_logging = "json" in logging_source.lower() or "JsonFormatter" in logging_source
    test_check("Logging", "Structured JSON logging configured", has_json_logging,
               "JSON formatter for machine-readable logs")

except Exception as e:
    test_check("Logging", "Logging module imports", False, f"Error: {e}")

# ============================================================================
# 4. MCP CLIENT COMPONENTS
# ============================================================================
print("\n" + "="*80)
print("4. MCP CLIENT COMPONENTS")
print("="*80)

try:
    from src.mcp import client
    test_check("MCP", "MCP client module imports", True)

    # Check for critical functions
    has_init = hasattr(client, "initialize_mcp_connection")
    test_check("MCP", "initialize_mcp_connection function exists", has_init)

    has_circuit_breaker = hasattr(client, "get_mcp_circuit_breaker")
    test_check("MCP", "get_mcp_circuit_breaker function exists", has_circuit_breaker)

    has_tools = hasattr(client, "get_discovered_tools")
    test_check("MCP", "get_discovered_tools function exists", has_tools)

    # Verify conditional transport logic
    import inspect
    init_source = inspect.getsource(client._initialize_mcp_connection_with_retry)

    test_check("MCP", "Conditional transport logic present",
               "if transport_type ==" in init_source,
               "Supports stdio and sse transports")

    test_check("MCP", "stdio transport implemented",
               'if transport_type == "stdio"' in init_source)

    test_check("MCP", "sse transport placeholder",
               'elif transport_type == "sse"' in init_source)

    test_check("MCP", "Security requirement documented",
               "127.0.0.1" in init_source and "0.0.0.0" in init_source,
               "localhost-only binding requirement documented")

except Exception as e:
    test_check("MCP", "MCP client module imports", False, f"Error: {e}")

# ============================================================================
# 5. CIRCUIT BREAKERS
# ============================================================================
print("\n" + "="*80)
print("5. CIRCUIT BREAKERS")
print("="*80)

try:
    from src.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
    test_check("Circuit Breaker", "Circuit breaker module imports", True)

    from src.config import get_mcp_circuit_breaker, get_gemini_circuit_breaker

    # Get circuit breakers
    mcp_cb = get_mcp_circuit_breaker()
    gemini_cb = get_gemini_circuit_breaker()

    test_check("Circuit Breaker", "MCP circuit breaker available", mcp_cb is not None)
    test_check("Circuit Breaker", "Gemini circuit breaker available", gemini_cb is not None)

    # Check states
    mcp_state = mcp_cb.get_state()
    gemini_state = gemini_cb.get_state()

    test_check("Circuit Breaker", "MCP breaker has state", mcp_state is not None,
               f"State: {mcp_state.state.value}")
    test_check("Circuit Breaker", "Gemini breaker has state", gemini_state is not None,
               f"State: {gemini_state.state.value}")

except Exception as e:
    test_check("Circuit Breaker", "Circuit breaker system", False, f"Error: {e}")

# ============================================================================
# 6. METRICS SYSTEM
# ============================================================================
print("\n" + "="*80)
print("6. METRICS SYSTEM")
print("="*80)

try:
    from src.observability.metrics import Metrics
    test_check("Metrics", "Metrics module imports", True)

    # Create test metrics instance
    test_metrics = Metrics()

    # Verify metrics tracking
    test_metrics.increment_total_requests()
    test_metrics.increment_successful_requests()

    stats = test_metrics.get_stats()

    test_check("Metrics", "Metrics can track requests", stats['total_requests'] > 0,
               f"Total: {stats['total_requests']}, Success: {stats['successful_requests']}")

    test_check("Metrics", "Success rate calculation", 'success_rate' in stats,
               f"Success rate: {stats['success_rate']:.2%}")

except Exception as e:
    test_check("Metrics", "Metrics system", False, f"Error: {e}")

# ============================================================================
# 7. API ROUTES
# ============================================================================
print("\n" + "="*80)
print("7. API ROUTES")
print("="*80)

try:
    from src.api import routes
    test_check("API Routes", "Routes module imports", True)

    # Check if FastAPI app exists
    from src.main import app
    test_check("API Routes", "FastAPI app exists", app is not None)

    # Get registered routes
    route_paths = [route.path for route in app.routes]

    expected_routes = ["/", "/health", "/chat/stream", "/docs", "/openapi.json"]
    for route_path in expected_routes:
        test_check("API Routes", f"Route {route_path} registered",
                   route_path in route_paths)

except Exception as e:
    test_check("API Routes", "API routes system", False, f"Error: {e}")

# ============================================================================
# 8. API SCHEMAS
# ============================================================================
print("\n" + "="*80)
print("8. API SCHEMAS")
print("="*80)

try:
    from src.api.schemas import ChatRequest, ChatResponse, HealthResponse, ErrorResponse
    test_check("API Schemas", "Schema module imports", True)

    # Test schema creation
    test_request = ChatRequest(message="Test message", request_id="test_123")
    test_check("API Schemas", "ChatRequest schema works",
               test_request.message == "Test message")

    test_check("API Schemas", "ChatRequest has required fields",
               hasattr(test_request, 'message') and hasattr(test_request, 'request_id'))

except Exception as e:
    test_check("API Schemas", "API schemas", False, f"Error: {e}")

# ============================================================================
# 9. MCP SERVER COMPONENTS
# ============================================================================
print("\n" + "="*80)
print("9. MCP SERVER COMPONENTS")
print("="*80)

try:
    # Check MCP server directory structure
    mcp_server_path = Path("src/mcp_server")
    test_check("MCP Server", "MCP server directory exists", mcp_server_path.exists())

    # Check for critical MCP server files
    critical_files = {
        "server.py": "MCP server entry point",
        "models.py": "SQLModel entities",
        "database.py": "Database connection",
        "tools/": "CRUD tool implementations"
    }

    for file_path, description in critical_files.items():
        full_path = mcp_server_path / file_path
        test_check("MCP Server", f"{file_path} exists", full_path.exists(), description)

    # Check for all 5 CRUD tools
    tools_path = mcp_server_path / "tools"
    if tools_path.exists():
        expected_tools = [
            "create_todo.py",
            "list_todos.py",
            "update_todo.py",
            "search_todos.py",
            "delete_todo.py"
        ]

        for tool in expected_tools:
            tool_path = tools_path / tool
            test_check("MCP Server", f"Tool {tool} exists", tool_path.exists())

except Exception as e:
    test_check("MCP Server", "MCP server components", False, f"Error: {e}")

# ============================================================================
# 10. DOCUMENTATION
# ============================================================================
print("\n" + "="*80)
print("10. DOCUMENTATION")
print("="*80)

docs_to_check = {
    "CLAUDE.md": "Project instructions for Claude Code",
    "README.md": "Project README",
    ".env.example": "Environment variable template",
    "specs/003-agent-mcp-integration/spec.md": "Feature specification",
    "specs/003-agent-mcp-integration/plan.md": "Implementation plan",
    "specs/003-agent-mcp-integration/tasks.md": "Task breakdown",
    "specs/003-agent-mcp-integration/quickstart.md": "Setup guide"
}

for doc_path, description in docs_to_check.items():
    test_check("Documentation", f"{doc_path} exists",
               os.path.exists(doc_path), description)

# Check quickstart.md for SSE documentation (our T035 work)
if os.path.exists("specs/003-agent-mcp-integration/quickstart.md"):
    with open("specs/003-agent-mcp-integration/quickstart.md", "r", encoding="utf-8") as f:
        quickstart_content = f.read()

    test_check("Documentation", "SSE Transport Configuration section exists",
               "SSE Transport Configuration" in quickstart_content,
               "T035 documentation present")

    test_check("Documentation", "Security requirements documented",
               "127.0.0.1" in quickstart_content and "0.0.0.0" in quickstart_content,
               "localhost-only binding explained")

# ============================================================================
# 11. PROJECT STRUCTURE
# ============================================================================
print("\n" + "="*80)
print("11. PROJECT STRUCTURE")
print("="*80)

critical_dirs = {
    "src/": "Source code root",
    "src/api/": "API endpoints",
    "src/agents/": "AI agent logic",
    "src/mcp/": "MCP client",
    "src/mcp_server/": "MCP server",
    "src/resilience/": "Circuit breaker & retry",
    "src/observability/": "Logging & metrics",
    "tests/": "Test suite",
    "specs/": "Feature specifications",
    ".venv/": "Virtual environment"
}

for dir_path, description in critical_dirs.items():
    test_check("Project Structure", f"{dir_path} exists",
               os.path.isdir(dir_path), description)

# ============================================================================
# 12. DEPENDENCIES
# ============================================================================
print("\n" + "="*80)
print("12. DEPENDENCIES")
print("="*80)

critical_imports = {
    "fastapi": "FastAPI framework",
    "openai": "OpenAI SDK (for Gemini bridge)",
    "fastmcp": "FastMCP server",
    "sqlmodel": "SQLModel ORM",
    "pydantic": "Data validation",
    "tenacity": "Retry logic",
    "pythonjsonlogger": "JSON logging"
}

for module_name, description in critical_imports.items():
    try:
        __import__(module_name)
        test_check("Dependencies", f"{module_name} installed", True, description)
    except ImportError:
        test_check("Dependencies", f"{module_name} installed", False,
                   f"Missing: {description}")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "="*80)
print(" VERIFICATION SUMMARY ".center(80))
print("="*80)

total_checks = len(results["passed"]) + len(results["failed"])
pass_rate = (len(results["passed"]) / total_checks * 100) if total_checks > 0 else 0

print(f"\nTotal Checks: {total_checks}")
print(f"Passed: {len(results['passed'])} ({pass_rate:.1f}%)")
print(f"Failed: {len(results['failed'])}")
print(f"Warnings: {len(results['warnings'])}")

if results["failed"]:
    print("\n" + "="*80)
    print("FAILED CHECKS:")
    print("="*80)
    for failed in results["failed"]:
        print(f"  ✗ {failed}")

if results["warnings"]:
    print("\n" + "="*80)
    print("WARNINGS:")
    print("="*80)
    for warning in results["warnings"]:
        print(f"  ⚠ {warning}")

print("\n" + "="*80)
if len(results["failed"]) == 0:
    print(" ✅ ALL SYSTEMS OPERATIONAL - EVERYTHING WORKING! ".center(80))
    print("="*80)
    print("\nEnvironment: ✓  Logs: ✓  Config: ✓  MCP: ✓  API: ✓  Docs: ✓")
    sys.exit(0)
else:
    print(" ⚠️ SOME ISSUES DETECTED - SEE ABOVE ".center(80))
    print("="*80)
    sys.exit(1)
