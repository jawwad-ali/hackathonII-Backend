"""Database connection and session management.

This module provides database engine creation, connection pooling,
and session management for the FastMCP database server.

All database operations use synchronous psycopg2 driver with
thread-safe connection pooling.
"""

import logging
import os
from typing import Generator

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

# Configure logger for database operations
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Database connection URL (psycopg2 format)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/todo_db"
)

# Log database initialization
logger.info("Initializing database engine", extra={
    "database_url_prefix": DATABASE_URL.split("@")[1] if "@" in DATABASE_URL else "unknown",
    "pool_size": 2,
    "max_overflow": 8,
    "pool_recycle": 3600
})

# Create database engine with connection pooling
# Configuration:
# - pool_size=2: Minimum number of connections in the pool
# - max_overflow=8: Maximum additional connections (total max = 10)
# - pool_pre_ping=True: Verify connection health before use
# - pool_recycle=3600: Recycle connections after 1 hour (prevents stale connections)
try:
    engine = create_engine(
        DATABASE_URL,
        echo=False,  # Set to True for SQL query logging (useful for debugging)
        pool_size=2,
        max_overflow=8,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {str(e)}", exc_info=True)
    raise


def get_session() -> Generator[Session, None, None]:
    """Provides a database session with automatic cleanup.

    This is a dependency function that yields a SQLModel Session
    with automatic transaction management and connection cleanup.

    Usage:
        def some_function(session: Session = Depends(get_session)):
            # Use session here
            pass

    Yields:
        Session: A SQLModel database session with context manager cleanup
    """
    with Session(engine) as session:
        try:
            yield session
        finally:
            session.close()


def create_db_and_tables() -> None:
    """Creates database tables if they don't exist.

    This function uses SQLModel.metadata.create_all() to create
    all tables defined in SQLModel entities (synchronous operation).

    Should be called during server startup to ensure tables exist.

    Raises:
        Exception: If database connection fails or table creation fails
    """
    try:
        logger.info("Creating database tables if they don't exist")
        SQLModel.metadata.create_all(engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}", exc_info=True)
        raise
