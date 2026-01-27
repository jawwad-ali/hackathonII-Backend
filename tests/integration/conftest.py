"""Pytest configuration and fixtures for integration tests.

This module provides fixtures specific to integration testing:
- Mock MCP servers
- Agent fixtures
- Streaming test utilities
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import json

from src.main import app
from src.resilience.circuit_breaker import CircuitState


@pytest.fixture(name="client")
def client_fixture():
    """FastAPI test client for integration tests."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_successful_list_response():
    """Mock successful list_todos response."""
    return json.dumps({
        "todos": [
            {"id": 1, "title": "Task 1", "status": "active"},
            {"id": 2, "title": "Task 2", "status": "active"},
        ],
        "total": 2,
        "limit": 2,
        "offset": 0
    })


@pytest.fixture
def mock_successful_delete_response():
    """Mock successful delete_todo response."""
    return json.dumps({
        "success": True,
        "deleted_id": 1,
        "message": "Todo deleted successfully"
    })


@pytest.fixture
def mock_empty_list_response():
    """Mock empty list_todos response."""
    return json.dumps({
        "todos": [],
        "total": 0,
        "limit": 0,
        "offset": 0
    })


@pytest.fixture
def reset_mcp_circuit_breaker():
    """Reset MCP circuit breaker to CLOSED state."""
    from src.mcp.client import get_mcp_circuit_breaker

    breaker = get_mcp_circuit_breaker()
    breaker.state.state = CircuitState.CLOSED
    breaker.state.failure_count = 0

    yield breaker

    # Cleanup
    breaker.state.state = CircuitState.CLOSED
    breaker.state.failure_count = 0


@pytest.fixture
def reset_llm_circuit_breaker():
    """Reset LLM circuit breaker to CLOSED state."""
    from src.config import get_llm_circuit_breaker

    breaker = get_llm_circuit_breaker()
    breaker.state.state = CircuitState.CLOSED
    breaker.state.failure_count = 0

    yield breaker

    # Cleanup
    breaker.state.state = CircuitState.CLOSED
    breaker.state.failure_count = 0


@pytest.fixture
def sse_parser():
    """Utility to parse SSE events from response text."""
    def parse(response_text: str):
        """Parse SSE response text into list of events."""
        events = []
        for line in response_text.split('\n'):
            line = line.strip()
            if line.startswith('data:'):
                data = line[5:].strip()
                if data:
                    try:
                        events.append(json.loads(data))
                    except json.JSONDecodeError:
                        events.append({"raw": data})
        return events
    return parse
