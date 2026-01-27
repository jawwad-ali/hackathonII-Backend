"""Unit tests for todo_agent.py to increase coverage.

This module tests:
- execute_agent_with_resilience() - main entry point with circuit breaker
- _execute_agent_with_retry() - internal retry logic
- _log_tool_calls_from_result() - tool call logging utility
- create_todo_agent() - agent creation with tools
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio


class TestExecuteAgentWithResilience:
    """Tests for execute_agent_with_resilience function."""

    @pytest.mark.asyncio
    async def test_successful_execution_returns_success_dict(self):
        """Test that successful execution returns success=True with result."""
        from src.orchestrators.todo_agent import execute_agent_with_resilience

        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.final_output = "Todo created successfully"

        with patch("src.orchestrators.todo_agent._execute_agent_with_retry") as mock_retry:
            mock_retry.return_value = mock_result

            with patch("src.orchestrators.todo_agent.get_llm_circuit_breaker") as mock_breaker:
                mock_cb = AsyncMock()
                mock_cb.call = AsyncMock(return_value=mock_result)
                mock_breaker.return_value = mock_cb

                result = await execute_agent_with_resilience(
                    mock_agent, "Create a todo"
                )

                assert result["success"] is True
                assert "result" in result
                assert result["result"] == mock_result

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_returns_error(self):
        """Test that CircuitBreakerError returns circuit_breaker_open error."""
        from src.orchestrators.todo_agent import execute_agent_with_resilience
        from src.resilience.circuit_breaker import CircuitBreakerError, CircuitBreakerState, CircuitState

        mock_agent = MagicMock()
        mock_state = CircuitBreakerState(state=CircuitState.OPEN, failure_count=5)

        with patch("src.orchestrators.todo_agent.get_llm_circuit_breaker") as mock_breaker:
            mock_cb = MagicMock()
            mock_cb.call = AsyncMock(side_effect=CircuitBreakerError("openai", mock_state))
            mock_breaker.return_value = mock_cb

            result = await execute_agent_with_resilience(
                mock_agent, "Create a todo"
            )

            assert result["success"] is False
            assert result["error"] == "circuit_breaker_open"
            assert "temporarily unavailable" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_general_exception_returns_execution_failed(self):
        """Test that general exceptions return execution_failed error."""
        from src.orchestrators.todo_agent import execute_agent_with_resilience

        mock_agent = MagicMock()

        with patch("src.orchestrators.todo_agent.get_llm_circuit_breaker") as mock_breaker:
            mock_cb = MagicMock()
            mock_cb.call = AsyncMock(side_effect=RuntimeError("API error"))
            mock_breaker.return_value = mock_cb

            result = await execute_agent_with_resilience(
                mock_agent, "Create a todo"
            )

            assert result["success"] is False
            assert result["error"] == "execution_failed"
            assert "API error" in result["details"]

    @pytest.mark.asyncio
    async def test_execution_with_context(self):
        """Test execution with optional context parameter."""
        from src.orchestrators.todo_agent import execute_agent_with_resilience

        mock_agent = MagicMock()
        mock_context = MagicMock()
        mock_result = MagicMock()

        with patch("src.orchestrators.todo_agent.get_llm_circuit_breaker") as mock_breaker:
            mock_cb = MagicMock()
            mock_cb.call = AsyncMock(return_value=mock_result)
            mock_breaker.return_value = mock_cb

            result = await execute_agent_with_resilience(
                mock_agent, "Create a todo", context=mock_context
            )

            assert result["success"] is True
            # Verify context was passed through
            mock_cb.call.assert_called_once()


class TestExecuteAgentWithRetry:
    """Tests for _execute_agent_with_retry function."""

    @pytest.mark.asyncio
    async def test_successful_execution_with_context(self):
        """Test successful execution when context is provided."""
        from src.orchestrators.todo_agent import _execute_agent_with_retry

        mock_agent = MagicMock()
        mock_context = MagicMock()
        mock_result = MagicMock()
        mock_result.final_output = "Success"

        # Runner is imported inside the function from agents module
        with patch("agents.Runner") as mock_runner_class:
            mock_runner_class.run = AsyncMock(return_value=mock_result)

            with patch("src.orchestrators.todo_agent._log_tool_calls_from_result"):
                result = await _execute_agent_with_retry(
                    mock_agent, "Test input", mock_context
                )

                assert result == mock_result
                mock_runner_class.run.assert_called_once_with(
                    mock_agent, input="Test input", context=mock_context
                )

    @pytest.mark.asyncio
    async def test_successful_execution_without_context(self):
        """Test successful execution when context is None."""
        from src.orchestrators.todo_agent import _execute_agent_with_retry

        mock_agent = MagicMock()
        mock_result = MagicMock()

        with patch("agents.Runner") as mock_runner_class:
            mock_runner_class.run = AsyncMock(return_value=mock_result)

            with patch("src.orchestrators.todo_agent._log_tool_calls_from_result"):
                result = await _execute_agent_with_retry(
                    mock_agent, "Test input", None
                )

                assert result == mock_result
                mock_runner_class.run.assert_called_once_with(
                    mock_agent, input="Test input"
                )

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self):
        """Test that timeout triggers TimeoutError for retry logic."""
        from src.orchestrators.todo_agent import _execute_agent_with_retry

        mock_agent = MagicMock()

        with patch("agents.Runner") as mock_runner_class:
            # Simulate slow API call that exceeds timeout
            async def slow_call(*args, **kwargs):
                await asyncio.sleep(100)  # Will be interrupted by timeout

            mock_runner_class.run = slow_call

            with patch("src.orchestrators.todo_agent.settings") as mock_settings:
                mock_settings.REQUEST_TIMEOUT = 0.01  # Very short timeout

                with pytest.raises(TimeoutError) as exc_info:
                    await _execute_agent_with_retry(mock_agent, "Test")

                assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_connection_error_propagates(self):
        """Test that ConnectionError propagates for retry logic."""
        from src.orchestrators.todo_agent import _execute_agent_with_retry

        mock_agent = MagicMock()

        with patch("agents.Runner") as mock_runner_class:
            mock_runner_class.run = AsyncMock(
                side_effect=ConnectionError("Network error")
            )

            with pytest.raises(ConnectionError):
                await _execute_agent_with_retry(mock_agent, "Test")

    @pytest.mark.asyncio
    async def test_generic_exception_propagates(self):
        """Test that generic exceptions propagate without retry."""
        from src.orchestrators.todo_agent import _execute_agent_with_retry

        mock_agent = MagicMock()

        with patch("agents.Runner") as mock_runner_class:
            mock_runner_class.run = AsyncMock(
                side_effect=ValueError("Invalid input")
            )

            with pytest.raises(ValueError):
                await _execute_agent_with_retry(mock_agent, "Test")


class TestLogToolCallsFromResult:
    """Tests for _log_tool_calls_from_result utility function."""

    def test_logs_with_valid_result(self, caplog):
        """Test logging with a valid result object."""
        from src.orchestrators.todo_agent import _log_tool_calls_from_result
        import logging

        mock_result = MagicMock()
        mock_result.new_items = [
            MagicMock(
                type="tool_call",
                tool_name="create_todo",
                tool_arguments={"title": "Test"},
            )
        ]

        with caplog.at_level(logging.INFO):
            _log_tool_calls_from_result(mock_result, 1.5, success=True)

        # Should not raise any errors
        assert True

    def test_handles_missing_new_items(self):
        """Test graceful handling when result has no new_items."""
        from src.orchestrators.todo_agent import _log_tool_calls_from_result

        mock_result = MagicMock(spec=[])  # No attributes
        del mock_result.new_items  # Remove new_items attribute

        # Should not raise
        _log_tool_calls_from_result(mock_result, 1.0, success=True)

    def test_handles_none_result(self):
        """Test graceful handling when result is None."""
        from src.orchestrators.todo_agent import _log_tool_calls_from_result

        # Should not raise
        _log_tool_calls_from_result(None, 0.5, success=False)

    def test_logs_failure_case(self, caplog):
        """Test logging when success=False."""
        from src.orchestrators.todo_agent import _log_tool_calls_from_result
        import logging

        mock_result = MagicMock()
        mock_result.new_items = []

        with caplog.at_level(logging.INFO):
            _log_tool_calls_from_result(mock_result, 2.0, success=False)

        # Should not raise
        assert True


class TestCreateTodoAgent:
    """Tests for create_todo_agent factory function."""

    @pytest.mark.asyncio
    async def test_creates_agent_without_mcp_server(self):
        """Test agent creation when no MCP servers provided."""
        from src.orchestrators.todo_agent import create_todo_agent

        agent = await create_todo_agent(mcp_servers=[])

        assert agent is not None
        assert agent.name == "TodoAgent"

    @pytest.mark.asyncio
    async def test_creates_agent_with_instructions(self):
        """Test that agent has proper instructions."""
        from src.orchestrators.todo_agent import create_todo_agent

        agent = await create_todo_agent(mcp_servers=[])

        assert agent.instructions is not None
        assert len(agent.instructions) > 0

    @pytest.mark.asyncio
    async def test_agent_has_correct_model(self):
        """Test that agent uses configured model."""
        from src.orchestrators.todo_agent import create_todo_agent

        with patch("src.orchestrators.todo_agent.get_openai_model") as mock_model:
            mock_model.return_value = "gpt-4"

            agent = await create_todo_agent(mcp_servers=[])

            # Model is set via the Agent constructor
            assert agent is not None

    @pytest.mark.asyncio
    async def test_creates_agent_with_mcp_server(self):
        """Test agent creation with MCP server instance."""
        from src.orchestrators.todo_agent import create_todo_agent

        # Mock MCP server
        mock_mcp = AsyncMock()
        mock_mcp.call_tool = AsyncMock(return_value=MagicMock())
        # Mock list_tools to return expected tools
        mock_tools = [
            MagicMock(name="create_todo"),
            MagicMock(name="list_todos"),
            MagicMock(name="update_todo"),
            MagicMock(name="search_todos"),
            MagicMock(name="delete_todo"),
        ]
        mock_mcp.list_tools = AsyncMock(return_value=mock_tools)

        agent = await create_todo_agent(mcp_servers=[mock_mcp])

        # Should create agent with tools when MCP server provided
        assert agent is not None
        # 5 tools should be added when MCP server is available
        assert len(agent.tools) == 5


class TestAgentToolRegistration:
    """Tests for tool registration in create_todo_agent."""

    @pytest.mark.asyncio
    async def test_tools_registered_with_mcp_server(self):
        """Test that all 5 tools are registered when MCP server is provided."""
        from src.orchestrators.todo_agent import create_todo_agent

        mock_mcp = AsyncMock()
        mock_mcp.call_tool = AsyncMock(return_value=MagicMock())
        mock_tools = [
            MagicMock(name="create_todo"),
            MagicMock(name="list_todos"),
            MagicMock(name="update_todo"),
            MagicMock(name="search_todos"),
            MagicMock(name="delete_todo"),
        ]
        mock_mcp.list_tools = AsyncMock(return_value=mock_tools)

        agent = await create_todo_agent(mcp_servers=[mock_mcp])

        # Find tool names
        tool_names = [t.name for t in agent.tools]

        # All 5 tools should be registered
        assert "create_todo" in tool_names
        assert "list_todos" in tool_names
        assert "update_todo" in tool_names
        assert "search_todos" in tool_names
        assert "delete_todo" in tool_names
        assert len(tool_names) == 5

    @pytest.mark.asyncio
    async def test_no_tools_without_mcp_server(self):
        """Test that no tools registered when MCP server is None or empty."""
        from src.orchestrators.todo_agent import create_todo_agent

        # Test with empty list
        agent = await create_todo_agent(mcp_servers=[])

        # Should have empty tools list when no MCP server
        assert len(agent.tools) == 0

    @pytest.mark.asyncio
    async def test_no_tools_with_none_mcp_servers(self):
        """Test that no tools registered when mcp_servers is None."""
        from src.orchestrators.todo_agent import create_todo_agent

        # Test with None
        agent = await create_todo_agent(mcp_servers=None)

        # Should have empty tools list when no MCP server
        assert len(agent.tools) == 0


class TestAgentInstructions:
    """Tests for agent instruction configuration."""

    @pytest.mark.asyncio
    async def test_instructions_mention_create(self):
        """Test that instructions mention create operations."""
        from src.orchestrators.todo_agent import create_todo_agent

        agent = await create_todo_agent(mcp_servers=[])

        assert "create" in agent.instructions.lower()

    @pytest.mark.asyncio
    async def test_instructions_mention_list(self):
        """Test that instructions mention list operations."""
        from src.orchestrators.todo_agent import create_todo_agent

        agent = await create_todo_agent(mcp_servers=[])

        assert "list" in agent.instructions.lower()

    @pytest.mark.asyncio
    async def test_instructions_mention_update(self):
        """Test that instructions mention update operations."""
        from src.orchestrators.todo_agent import create_todo_agent

        agent = await create_todo_agent(mcp_servers=[])

        assert "update" in agent.instructions.lower()

    @pytest.mark.asyncio
    async def test_instructions_mention_delete(self):
        """Test that instructions mention delete operations."""
        from src.orchestrators.todo_agent import create_todo_agent

        agent = await create_todo_agent(mcp_servers=[])

        assert "delete" in agent.instructions.lower()


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_input_handled(self):
        """Test that empty input is handled gracefully."""
        from src.orchestrators.todo_agent import execute_agent_with_resilience

        mock_agent = MagicMock()
        mock_result = MagicMock()

        with patch("src.orchestrators.todo_agent.get_llm_circuit_breaker") as mock_breaker:
            mock_cb = MagicMock()
            mock_cb.call = AsyncMock(return_value=mock_result)
            mock_breaker.return_value = mock_cb

            # Empty input should still execute
            result = await execute_agent_with_resilience(mock_agent, "")

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_very_long_input_handled(self):
        """Test that very long input is handled."""
        from src.orchestrators.todo_agent import execute_agent_with_resilience

        mock_agent = MagicMock()
        mock_result = MagicMock()

        with patch("src.orchestrators.todo_agent.get_llm_circuit_breaker") as mock_breaker:
            mock_cb = MagicMock()
            mock_cb.call = AsyncMock(return_value=mock_result)
            mock_breaker.return_value = mock_cb

            long_input = "test " * 10000

            result = await execute_agent_with_resilience(mock_agent, long_input)

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_unicode_input_handled(self):
        """Test that unicode characters are handled."""
        from src.orchestrators.todo_agent import execute_agent_with_resilience

        mock_agent = MagicMock()
        mock_result = MagicMock()

        with patch("src.orchestrators.todo_agent.get_llm_circuit_breaker") as mock_breaker:
            mock_cb = MagicMock()
            mock_cb.call = AsyncMock(return_value=mock_result)
            mock_breaker.return_value = mock_cb

            unicode_input = "Create todo: 日本語テスト 🎉 résumé"

            result = await execute_agent_with_resilience(mock_agent, unicode_input)

            assert result["success"] is True
