"""
Structured JSON Logging with Request ID Correlation

Implements FR-011: Structured JSON logging with request IDs for correlation.

Features:
- JSON-formatted log output using python-json-logger
- Request ID generation and propagation via middleware
- Context-aware logging with automatic request ID injection
- Thread-safe request ID storage using contextvars

Usage:
    # Configure logging at application startup
    configure_logging(log_level="INFO")

    # Get a logger instance
    logger = get_logger(__name__)

    # Add middleware to FastAPI app
    app.add_middleware(RequestIDMiddleware)

    # Log with automatic request ID injection
    logger.info("Processing request", extra={"user_id": 123})
"""

import logging
import uuid
from contextvars import ContextVar
from typing import Optional

from fastapi import Request, Response
from pythonjsonlogger import jsonlogger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# Context variable for storing request ID
# Using contextvars ensures thread-safety in async contexts
_request_id_context: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class RequestIDFilter(logging.Filter):
    """
    Logging filter that injects request ID into log records.

    Automatically adds request_id field to all log entries when available
    from the context variable.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add request_id to log record from context.

        Args:
            record: Log record to augment

        Returns:
            True (always pass the record through)
        """
        request_id = _request_id_context.get()
        if request_id:
            record.request_id = request_id  # type: ignore
        else:
            record.request_id = "no-request-id"  # type: ignore
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter for structured logging.

    Extends pythonjsonlogger to include standard fields:
    - timestamp
    - level
    - logger (module name)
    - message
    - request_id (from context)
    - Any extra fields passed via logger.info(..., extra={...})
    """

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        """
        Add custom fields to the JSON log record.

        Args:
            log_record: Dictionary to be serialized to JSON
            record: Original logging.LogRecord
            message_dict: Dictionary from message string formatting
        """
        super().add_fields(log_record, record, message_dict)

        # Ensure consistent field ordering and naming
        log_record["timestamp"] = record.created
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["message"] = record.getMessage()

        # Add request_id if available (set by RequestIDFilter)
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure structured JSON logging for the application.

    Sets up:
    - JSON formatter for all log handlers
    - Request ID filter for automatic injection
    - Root logger configuration

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Example:
        >>> configure_logging(log_level="DEBUG")
        >>> logger = logging.getLogger(__name__)
        >>> logger.info("Application started")
    """
    # Create JSON formatter
    formatter = CustomJsonFormatter(
        fmt="%(timestamp)s %(level)s %(logger)s %(message)s %(request_id)s"
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create and configure handler
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(RequestIDFilter())

    # Add handler to root logger
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Convenience function that returns a standard Python logger.
    The logger will automatically include request IDs when available.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Logger instance configured for structured logging

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing request", extra={"user_id": 123})
    """
    return logging.getLogger(name)


def get_request_id() -> Optional[str]:
    """
    Get the current request ID from context.

    Returns:
        Current request ID or None if not set

    Example:
        >>> request_id = get_request_id()
        >>> print(f"Current request: {request_id}")
    """
    return _request_id_context.get()


def set_request_id(request_id: str) -> None:
    """
    Set the request ID in context.

    Args:
        request_id: Request ID to set

    Note:
        Typically not called directly - RequestIDMiddleware handles this.

    Example:
        >>> set_request_id("req-12345")
        >>> logger.info("Processing")  # Will include request_id: req-12345
    """
    _request_id_context.set(request_id)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for generating and propagating request IDs.

    Implements FR-011: Request ID generation and correlation.

    Features:
    - Generates UUID4 request IDs for each request
    - Accepts existing X-Request-ID header if provided
    - Injects request ID into logging context
    - Adds X-Request-ID header to responses

    Usage:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> app.add_middleware(RequestIDMiddleware)
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process request and inject request ID.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or endpoint in chain

        Returns:
            HTTP response with X-Request-ID header
        """
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Set request ID in context for logging
        set_request_id(request_id)

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response
