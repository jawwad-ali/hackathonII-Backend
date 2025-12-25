"""
AI Agent Orchestrator for Todo Management
FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime, timezone
import time

# Import configuration
from src.config import settings, get_gemini_circuit_breaker

# Import MCP client for circuit breaker access
from src.mcp.client import get_mcp_circuit_breaker

# Import API routes
from src.api.routes import router as chat_router

# Configure logger
logger = logging.getLogger(__name__)

# Track application startup time for uptime calculation
_startup_time: float = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting AI Agent Orchestrator...")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Log Level: {settings.LOG_LEVEL}")

    yield

    # Shutdown
    logger.info("Shutting down AI Agent Orchestrator...")


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

# Include API routers
app.include_router(chat_router)


@app.get("/health")
async def health_check():
    """
    Health check endpoint with circuit breaker status.

    Returns detailed service health status including circuit breaker states,
    uptime metrics, and external dependency health. Used for monitoring,
    load balancer health checks, and SLO compliance verification.

    Returns:
        dict: HealthResponse per openapi.yaml schema with:
            - status: "healthy" | "degraded" | "unhealthy"
            - timestamp: Current server time (ISO 8601 UTC)
            - uptime_seconds: Time since service started
            - circuit_breakers: MCP and Gemini circuit breaker states
            - metrics: Request statistics (placeholder for Phase 6)

    Status Codes:
        200: Service is healthy (all circuit breakers closed/half-open)
        503: Service is unhealthy (both circuit breakers open)
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

    # Build metrics (placeholder for Phase 6 - Observability)
    # Will be populated with actual request tracking in T041
    metrics = {
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "success_rate": 0.0
    }

    # Build HealthResponse per openapi.yaml schema
    response = {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds,
        "circuit_breakers": circuit_breakers,
        "metrics": metrics
    }

    return response


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
