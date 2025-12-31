"""
Integration tests for MCP connection and health check endpoints.

T009: Test successful MCP connection startup
T010: Test MCP connection failure and degraded mode
T011: Test health check endpoint with various circuit breaker states

NOTE: These tests are written FIRST (TDD approach) and should FAIL before implementation.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import time

from src.main import app
from src.mcp.client import get_mcp_circuit_breaker
from src.config import get_gemini_circuit_breaker


class TestMCPConnectionStartup:
    """
    T009: Integration test for MCP connection startup.

    Tests:
    - Successful MCP connection initialization
    - Tool discovery count (should discover 5 tools)
    - Connection state stored in app.state.mcp_server
    """

    @pytest.mark.asyncio
    async def test_successful_mcp_connection_startup(self):
        """
        Test that MCP server connects successfully on startup and discovers all tools.

        Expected behavior:
        - MCP connection initializes without errors
        - app.state.mcp_server is not None
        - 5 tools are discovered (create_todo, list_todos, update_todo, search_todos, delete_todo)
        - Initialization completes in <2 seconds (per spec requirement)
        """
        # Mock MCPServerStdio to avoid actual subprocess spawn
        mock_mcp_server = AsyncMock()
        mock_mcp_server.__aenter__ = AsyncMock(return_value=mock_mcp_server)
        mock_mcp_server.__aexit__ = AsyncMock(return_value=None)

        # Mock list_tools to return 5 expected tools
        mock_tools = [
            MagicMock(name="create_todo"),
            MagicMock(name="list_todos"),
            MagicMock(name="update_todo"),
            MagicMock(name="search_todos"),
            MagicMock(name="delete_todo"),
        ]
        mock_mcp_server.list_tools = AsyncMock(return_value=mock_tools)

        with patch('src.mcp.client.MCPServerStdio', return_value=mock_mcp_server):
            with patch('src.main.initialize_mcp_connection', return_value=mock_mcp_server):
                # Create test client (triggers lifespan startup)
                client = TestClient(app)

                # Verify MCP server is stored in app state
                assert hasattr(app.state, 'mcp_server'), "app.state.mcp_server should exist"
                assert app.state.mcp_server is not None, "app.state.mcp_server should not be None"

                # Verify it's the mock server we created
                assert app.state.mcp_server == mock_mcp_server

                # Verify tool discovery was called
                mock_mcp_server.list_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcp_connection_discovers_correct_tool_count(self):
        """
        Test that exactly 5 tools are discovered from MCP server.

        Expected tools:
        1. create_todo
        2. list_todos
        3. update_todo
        4. search_todos
        5. delete_todo
        """
        # Mock MCPServerStdio
        mock_mcp_server = AsyncMock()
        mock_mcp_server.__aenter__ = AsyncMock(return_value=mock_mcp_server)
        mock_mcp_server.__aexit__ = AsyncMock(return_value=None)

        # Mock exactly 5 tools
        expected_tool_names = ["create_todo", "list_todos", "update_todo", "search_todos", "delete_todo"]
        mock_tools = [MagicMock(name=name) for name in expected_tool_names]
        mock_mcp_server.list_tools = AsyncMock(return_value=mock_tools)

        with patch('src.mcp.client.MCPServerStdio', return_value=mock_mcp_server):
            # Import and call get_discovered_tools directly
            from src.mcp.client import get_discovered_tools

            discovered_tools = await get_discovered_tools(mock_mcp_server)

            # Verify count
            assert len(discovered_tools) == 5, f"Expected 5 tools, got {len(discovered_tools)}"

            # Verify tool names
            assert set(discovered_tools) == set(expected_tool_names), \
                f"Expected tools {expected_tool_names}, got {discovered_tools}"

    @pytest.mark.asyncio
    async def test_mcp_connection_initialization_time(self):
        """
        Test that MCP connection initializes within performance requirements.

        Per spec: Tool discovery should complete in <2 seconds on startup.
        """
        # Mock MCPServerStdio with realistic delay
        mock_mcp_server = AsyncMock()
        mock_mcp_server.__aenter__ = AsyncMock(return_value=mock_mcp_server)
        mock_mcp_server.__aexit__ = AsyncMock(return_value=None)

        # Add small delay to simulate real initialization
        async def delayed_init():
            import asyncio
            await asyncio.sleep(0.1)  # 100ms delay
            return mock_mcp_server

        mock_mcp_server.list_tools = AsyncMock(return_value=[
            MagicMock(name="create_todo"),
            MagicMock(name="list_todos"),
            MagicMock(name="update_todo"),
            MagicMock(name="search_todos"),
            MagicMock(name="delete_todo"),
        ])

        with patch('src.mcp.client.MCPServerStdio', return_value=mock_mcp_server):
            from src.mcp.client import initialize_mcp_connection, get_discovered_tools

            start_time = time.time()

            mcp_server = await initialize_mcp_connection()
            if mcp_server:
                await get_discovered_tools(mcp_server)

            elapsed_time = time.time() - start_time

            # Verify initialization time is under 2 seconds
            assert elapsed_time < 2.0, \
                f"MCP initialization took {elapsed_time:.2f}s, should be < 2s"


class TestMCPConnectionFailure:
    """
    T010: Integration test for MCP connection failure scenarios.

    Tests:
    - MCP connection failure handling
    - Degraded mode activation (app.state.mcp_server = None)
    - App continues running despite MCP failure
    - Error logging is triggered
    """

    @pytest.mark.asyncio
    async def test_mcp_connection_failure_enters_degraded_mode(self):
        """
        Test that app enters degraded mode when MCP connection fails.

        Expected behavior:
        - initialize_mcp_connection returns None
        - app.state.mcp_server is set to None
        - App continues running (no crash)
        - Warning is logged about degraded mode
        """
        # Mock initialize_mcp_connection to return None (failure)
        with patch('src.main.initialize_mcp_connection', return_value=None):
            # Create test client (triggers lifespan startup)
            client = TestClient(app)

            # Verify app state reflects degraded mode
            assert hasattr(app.state, 'mcp_server'), "app.state.mcp_server should exist"
            assert app.state.mcp_server is None, "app.state.mcp_server should be None in degraded mode"

            # Verify app is still running (can make requests)
            response = client.get("/health")
            assert response.status_code == 200, "App should still respond to health checks in degraded mode"

    @pytest.mark.asyncio
    async def test_mcp_connection_exception_handling(self):
        """
        Test that unexpected exceptions during MCP initialization are handled gracefully.

        Expected behavior:
        - Exception during initialization is caught
        - app.state.mcp_server is set to None
        - App continues running
        - Error is logged
        """
        # Mock initialize_mcp_connection to raise exception
        with patch('src.main.initialize_mcp_connection', side_effect=Exception("MCP server unreachable")):
            # Create test client (triggers lifespan startup)
            client = TestClient(app)

            # Verify app state reflects degraded mode
            assert hasattr(app.state, 'mcp_server'), "app.state.mcp_server should exist"
            assert app.state.mcp_server is None, "app.state.mcp_server should be None after exception"

            # Verify app is still running
            response = client.get("/")
            assert response.status_code == 200, "App should still respond after MCP initialization exception"

    @pytest.mark.asyncio
    async def test_degraded_mode_logs_warning(self, caplog):
        """
        Test that degraded mode entry is logged as a warning.

        Expected behavior:
        - Warning log entry contains "degraded mode"
        - Log includes reason for degraded mode
        """
        import logging

        with patch('src.main.initialize_mcp_connection', return_value=None):
            with caplog.at_level(logging.WARNING):
                # Create test client (triggers lifespan startup)
                client = TestClient(app)

                # Verify warning was logged
                assert any("degraded mode" in record.message.lower() for record in caplog.records), \
                    "Warning about degraded mode should be logged"


class TestHealthCheckEndpoint:
    """
    T011: Integration test for health check endpoint.

    Tests:
    - Health check returns correct status with MCP up
    - Health check returns degraded status with MCP down
    - Health check always returns HTTP 200 (per spec)
    - Circuit breaker states are included in response
    """

    def test_health_check_returns_healthy_when_all_up(self):
        """
        Test health check returns "healthy" status when all services are operational.

        Expected behavior:
        - HTTP 200 status code
        - response.status == "healthy"
        - Both circuit breakers in "closed" state
        """
        # Mock both circuit breakers as closed (healthy)
        with patch('src.main.get_mcp_circuit_breaker') as mock_mcp_breaker, \
             patch('src.main.get_gemini_circuit_breaker') as mock_gemini_breaker:

            # Create mock circuit breaker states (both closed)
            mock_mcp_state = MagicMock()
            mock_mcp_state.state.value = "closed"
            mock_mcp_state.failure_count = 0
            mock_mcp_state.last_failure_time = None

            mock_gemini_state = MagicMock()
            mock_gemini_state.state.value = "closed"
            mock_gemini_state.failure_count = 0
            mock_gemini_state.last_failure_time = None

            mock_mcp_breaker.return_value.get_state.return_value = mock_mcp_state
            mock_gemini_breaker.return_value.get_state.return_value = mock_gemini_state

            client = TestClient(app)
            response = client.get("/health")

            # Verify HTTP status code is always 200
            assert response.status_code == 200, "Health check should return HTTP 200"

            # Verify response body
            data = response.json()
            assert data["status"] == "healthy", "Status should be 'healthy' when all services are up"
            assert "circuit_breakers" in data, "Response should include circuit_breakers"
            assert data["circuit_breakers"]["mcp_server"]["state"] == "closed"
            assert data["circuit_breakers"]["gemini_api"]["state"] == "closed"

    def test_health_check_returns_degraded_when_mcp_down(self):
        """
        Test health check returns "degraded" status when MCP is down.

        Expected behavior:
        - HTTP 200 status code (NOT 503)
        - response.status == "degraded"
        - MCP circuit breaker in "open" state
        - Gemini circuit breaker in "closed" state
        """
        with patch('src.main.get_mcp_circuit_breaker') as mock_mcp_breaker, \
             patch('src.main.get_gemini_circuit_breaker') as mock_gemini_breaker:

            # Mock MCP circuit breaker as open (unhealthy)
            mock_mcp_state = MagicMock()
            mock_mcp_state.state.value = "open"
            mock_mcp_state.failure_count = 5
            mock_mcp_state.last_failure_time = None

            # Mock Gemini circuit breaker as closed (healthy)
            mock_gemini_state = MagicMock()
            mock_gemini_state.state.value = "closed"
            mock_gemini_state.failure_count = 0
            mock_gemini_state.last_failure_time = None

            mock_mcp_breaker.return_value.get_state.return_value = mock_mcp_state
            mock_gemini_breaker.return_value.get_state.return_value = mock_gemini_state

            client = TestClient(app)
            response = client.get("/health")

            # T011: Verify HTTP 200 is returned even when MCP is down (graceful degradation)
            assert response.status_code == 200, \
                "Health check should return HTTP 200 even when MCP is down (per spec SC-013)"

            # Verify degraded status
            data = response.json()
            assert data["status"] == "degraded", \
                "Status should be 'degraded' when MCP is down but Gemini is up"
            assert data["circuit_breakers"]["mcp_server"]["state"] == "open"
            assert data["circuit_breakers"]["gemini_api"]["state"] == "closed"

    def test_health_check_returns_unhealthy_when_both_down(self):
        """
        Test health check returns "unhealthy" status when both services are down.

        Expected behavior:
        - HTTP 200 status code (still returns 200 per updated spec)
        - response.status == "unhealthy"
        - Both circuit breakers in "open" state
        """
        with patch('src.main.get_mcp_circuit_breaker') as mock_mcp_breaker, \
             patch('src.main.get_gemini_circuit_breaker') as mock_gemini_breaker:

            # Mock both circuit breakers as open
            mock_mcp_state = MagicMock()
            mock_mcp_state.state.value = "open"
            mock_mcp_state.failure_count = 5
            mock_mcp_state.last_failure_time = None

            mock_gemini_state = MagicMock()
            mock_gemini_state.state.value = "open"
            mock_gemini_state.failure_count = 3
            mock_gemini_state.last_failure_time = None

            mock_mcp_breaker.return_value.get_state.return_value = mock_mcp_state
            mock_gemini_breaker.return_value.get_state.return_value = mock_gemini_state

            client = TestClient(app)
            response = client.get("/health")

            # T011: Verify HTTP 200 is returned (updated per T008 requirements)
            assert response.status_code == 200, \
                "Health check should return HTTP 200 even when both services are down (per T008)"

            # Verify unhealthy status
            data = response.json()
            assert data["status"] == "unhealthy", \
                "Status should be 'unhealthy' when both services are down"
            assert data["circuit_breakers"]["mcp_server"]["state"] == "open"
            assert data["circuit_breakers"]["gemini_api"]["state"] == "open"

    def test_health_check_includes_metrics(self):
        """
        Test that health check response includes request metrics.

        Expected fields:
        - total_requests
        - successful_requests
        - failed_requests
        - success_rate
        """
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify metrics section exists
        assert "metrics" in data, "Health check response should include metrics"

        # Verify required metric fields
        metrics = data["metrics"]
        assert "total_requests" in metrics
        assert "successful_requests" in metrics
        assert "failed_requests" in metrics
        assert "success_rate" in metrics

        # Verify metric types
        assert isinstance(metrics["total_requests"], int)
        assert isinstance(metrics["successful_requests"], int)
        assert isinstance(metrics["failed_requests"], int)
        assert isinstance(metrics["success_rate"], (int, float))

    def test_health_check_includes_uptime(self):
        """
        Test that health check response includes uptime information.

        Expected fields:
        - uptime_seconds (integer)
        - timestamp (ISO 8601 format)
        """
        client = TestClient(app)

        # Wait a moment to ensure uptime > 0
        time.sleep(0.1)

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()

        # Verify uptime field exists and is positive
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], int)
        assert data["uptime_seconds"] >= 0

        # Verify timestamp exists and is in ISO format
        assert "timestamp" in data
        assert isinstance(data["timestamp"], str)
        # Basic ISO format check (contains 'T' and timezone info)
        assert 'T' in data["timestamp"]
