"""
AI Agent Orchestrator for Todo Management
FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

# Import configuration
from src.config import settings

# Configure logger
logger = logging.getLogger(__name__)


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


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Returns service status and basic configuration info.

    Returns:
        dict: Health status with service information
    """
    return {
        "status": "healthy",
        "service": "ai-agent-orchestrator",
        "version": "0.1.0",
        "gemini_model": settings.GEMINI_MODEL,
    }


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
