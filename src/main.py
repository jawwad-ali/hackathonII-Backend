"""
AI Agent Orchestrator for Todo Management
FastAPI Application Entry Point
"""

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime, timezone
import time

# Import configuration
from src.config import settings, get_gemini_circuit_breaker

# Import MCP client for circuit breaker access and initialization
from src.mcp.client import get_mcp_circuit_breaker, initialize_mcp_connection, get_discovered_tools

# Import observability components
from src.observability import (
    configure_logging,
    get_logger,
    RequestIDMiddleware,
    metrics_tracker,
)

# Import API routes
from src.api.routes import router as chat_router

# Configure structured JSON logging
configure_logging(log_level=settings.LOG_LEVEL)

# Get logger instance
logger = get_logger(__name__)

# Track application startup time for uptime calculation
_startup_time: float = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.

    T005: Initialize MCP connection on startup and store in app.state.mcp_server
    T006: Implement graceful degraded mode handling (set app.state.mcp_server = None on failure)
    """
    # Startup
    logger.info("Starting AI Agent Orchestrator...")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Log Level: {settings.LOG_LEVEL}")

    # T005: Initialize MCP connection on startup
    logger.info("Initializing MCP server connection...")
    startup_start = time.time()

    try:
        # Initialize MCP connection using MCPServerStdio
        # This spawns the FastMCP server as a subprocess with stdio transport
        mcp_server = await initialize_mcp_connection()

        if mcp_server is not None:
            # T005: Store MCP server connection in app.state for endpoint access
            app.state.mcp_server = mcp_server

            initialization_time = time.time() - startup_start

            # T007: Discover and log available tools from MCP server
            try:
                discovered_tools = await get_discovered_tools(mcp_server)
                tools_count = len(discovered_tools)

                logger.info(
                    f"MCP server connection initialized successfully in {initialization_time:.2f}s",
                    extra={
                        "initialization_time_seconds": initialization_time,
                        "mcp_server_name": "TodoDatabaseServer",
                        "transport": "stdio",
                        "discovered_tools_count": tools_count,
                        "discovered_tools": discovered_tools
                    }
                )

                # Log individual tools for detailed observability
                logger.info(
                    f"Discovered {tools_count} MCP tools: {', '.join(discovered_tools)}",
                    extra={
                        "tools": discovered_tools,
                        "tools_count": tools_count
                    }
                )
            except Exception as tool_discovery_error:
                # Tool discovery failed, but connection succeeded
                # Log warning and continue (degraded functionality)
                logger.warning(
                    f"MCP server connected but tool discovery failed: {tool_discovery_error}",
                    extra={
                        "initialization_time_seconds": initialization_time,
                        "tool_discovery_error": str(tool_discovery_error),
                        "error_type": type(tool_discovery_error).__name__
                    }
                )
        else:
            # T006: Graceful degraded mode - MCP connection failed but app continues
            app.state.mcp_server = None
            logger.warning(
                "MCP server connection failed - entering degraded mode",
                extra={
                    "degraded_mode": True,
                    "reason": "MCP initialization returned None"
                }
            )
    except Exception as e:
        # T006: Additional safety - catch any unexpected exceptions
        app.state.mcp_server = None
        logger.error(
            f"Unexpected error during MCP initialization: {e}",
            extra={
                "degraded_mode": True,
                "error": str(e),
                "error_type": type(e).__name__
            }
        )

    logger.info("AI Agent Orchestrator startup complete")

    yield

    # Shutdown
    logger.info("Shutting down AI Agent Orchestrator...")

    # Close MCP connection if it exists
    if hasattr(app.state, 'mcp_server') and app.state.mcp_server is not None:
        try:
            logger.info("Closing MCP server connection...")
            await app.state.mcp_server.__aexit__(None, None, None)
            logger.info("MCP server connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing MCP server connection: {e}")

    logger.info("AI Agent Orchestrator shutdown complete")


# Initialize FastAPI application
app = FastAPI(
    title="AI Agent Orchestrator",
    description="Natural language interface for todo management using OpenAI Agents SDK with Gemini",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Request ID middleware for request correlation
app.add_middleware(RequestIDMiddleware)

# Include API routers
app.include_router(chat_router)


@app.get("/health")
async def health_check(response: Response):
    """
    Health check endpoint with circuit breaker status (T008).

    Returns detailed service health status including circuit breaker states,
    uptime metrics, and external dependency health. Used for monitoring,
    load balancer health checks, and SLO compliance verification.

    T008: Always returns HTTP 200 to enable graceful degradation (per FR-010, SC-013).
    Monitors should check the "status" field in response body for actual health state.

    Args:
        response: FastAPI Response object for setting status code

    Returns:
        dict: HealthResponse schema with:
            - status: "healthy" | "degraded" | "unhealthy"
            - timestamp: Current server time (ISO 8601 UTC)
            - uptime_seconds: Time since service started
            - circuit_breakers: MCP and Gemini circuit breaker states
            - metrics: Request statistics

    Status Codes:
        200: Always returned (check response body "status" field for health state)
            - "healthy": All services operational
            - "degraded": One circuit breaker open (graceful degradation)
            - "unhealthy": Both circuit breakers open (app still responds)
    """
    # Get circuit breaker instances
    mcp_breaker = get_mcp_circuit_breaker()
    gemini_breaker = get_gemini_circuit_breaker()

    # Get circuit breaker states
    mcp_state = mcp_breaker.get_state()
    gemini_state = gemini_breaker.get_state()

    # Calculate uptime
    uptime_seconds = int(time.time() - _startup_time)

    # Convert circuit breaker states to dict format per openapi.yaml
    def breaker_state_to_dict(state) -> dict:
        """Convert CircuitBreakerState to HealthResponse schema format."""
        return {
            "state": state.state.value,  # "closed", "open", or "half_open"
            "failure_count": state.failure_count,
            "last_failure": state.last_failure_time.isoformat() if state.last_failure_time else None
        }

    # Build circuit breaker status dict
    circuit_breakers = {
        "mcp_server": breaker_state_to_dict(mcp_state),
        "gemini_api": breaker_state_to_dict(gemini_state)
    }

    # Determine overall health status
    # - healthy: Both circuit breakers closed or half-open
    # - degraded: One circuit breaker open
    # - unhealthy: Both circuit breakers open
    mcp_open = mcp_state.state.value == "open"
    gemini_open = gemini_state.state.value == "open"

    if mcp_open and gemini_open:
        status = "unhealthy"
    elif mcp_open or gemini_open:
        status = "degraded"
    else:
        status = "healthy"

    # Get metrics from metrics tracker
    metrics_summary = metrics_tracker.get_summary()

    # Calculate success rate
    total_requests = metrics_summary["total_requests"]
    successful_requests = metrics_summary["successful_requests"]
    success_rate = (
        (successful_requests / total_requests * 100.0)
        if total_requests > 0
        else 0.0
    )

    # Build metrics dict per HealthResponse schema
    metrics = {
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": metrics_summary["failed_requests"],
        "success_rate": round(success_rate, 2)
    }

    # T008: Updated health check per spec requirements (FR-010, SC-013)
    # - HTTP 200 with status="healthy": All services operational
    # - HTTP 200 with status="degraded": MCP down but Gemini available (graceful degradation)
    # - HTTP 200 with status="degraded": Gemini down but MCP available (rare case)
    # - HTTP 200 with status="unhealthy": Both down (app still responds for monitoring)
    #
    # Always return HTTP 200 to indicate the app is responding.
    # Load balancers and monitors should check the "status" field in response body.
    response.status_code = 200

    # Log health status for monitoring
    if status == "unhealthy":
        logger.warning(
            "Health check: Service unhealthy - both circuit breakers open",
            extra={
                "status": status,
                "mcp_state": mcp_state.state.value,
                "gemini_state": gemini_state.state.value
            }
        )
    elif status == "degraded":
        logger.info(
            "Health check: Service degraded - one circuit breaker open",
            extra={
                "status": status,
                "mcp_state": mcp_state.state.value,
                "gemini_state": gemini_state.state.value
            }
        )

    # Build HealthResponse per openapi.yaml schema
    health_response = {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds,
        "circuit_breakers": circuit_breakers,
        "metrics": metrics
    }

    return health_response


@app.get("/")
async def root():
    """
    Root endpoint with API information.

    Returns:
        dict: API welcome message and documentation link
    """
    return {
        "message": "AI Agent Orchestrator for Todo Management",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "chat_stream": "/chat/stream",
            "health": "/health",
            "docs": "/docs",
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
