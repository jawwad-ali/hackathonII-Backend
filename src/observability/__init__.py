"""
Observability Module

Provides structured logging, metrics tracking, and request correlation
for the AI Agent Orchestrator.

Components:
- logging: Structured JSON logging with request ID correlation
- metrics: Performance metrics tracking for requests and dependencies
"""

from src.observability.logging import (
    configure_logging,
    get_logger,
    RequestIDMiddleware,
    get_request_id,
    set_request_id,
)
from src.observability.metrics import metrics_tracker

__all__ = [
    "configure_logging",
    "get_logger",
    "RequestIDMiddleware",
    "get_request_id",
    "set_request_id",
    "metrics_tracker",
]
