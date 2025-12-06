"""Tests for MCP Server - thin client that talks to SpeakUp service."""

import pytest
from unittest.mock import patch, MagicMock
from claude_tts_mcp.server import speak, stop, create_server


class TestServerTools:
    """Test MCP server tools (thin client mode)."""

    @pytest.fixture
    def mock_api_call(self):
        """Mock the _api_call function."""
        with patch("claude_tts_mcp.server._api_call") as mock:
            yield mock

    @pytest.fixture
    def mock_service_running(self):
        """Mock _is_service_running to return True."""
        with patch("claude_tts_mcp.server._is_service_running", return_value=True):
            yield

    def test_speak_returns_success(self, mock_api_call, mock_service_running):
        """speak() should return success with message_id."""
        mock_api_call.return_value = {
            "success": True,
            "message_id": 1,
            "queue_position": 1,
        }

        result = speak(text="Hello world")

        assert result["success"] is True
        assert "message_id" in result

    def test_speak_sends_to_service(self, mock_api_call, mock_service_running):
        """speak() should POST to the service."""
        mock_api_call.return_value = {"success": True, "message_id": 1, "queue_position": 0}

        speak(text="Test message", tone="excited", speed=1.5)

        # Check that speak endpoint was called
        calls = [c for c in mock_api_call.call_args_list if "/api/speak" in str(c)]
        assert len(calls) >= 1

        # Verify the data sent
        speak_call = calls[-1]
        data = speak_call.kwargs.get("data") or speak_call[1].get("data")
        assert data["text"] == "Test message"
        assert data["tone"] == "excited"
        assert data["speed"] == 1.5

    def test_speak_with_interrupt_calls_stop(self, mock_api_call, mock_service_running):
        """speak() with interrupt=True should call stop first."""
        mock_api_call.return_value = {"success": True, "message_id": 1, "queue_position": 0}

        speak(text="Interrupt!", interrupt=True)

        # Should have called /api/stop before /api/speak
        stop_calls = [c for c in mock_api_call.call_args_list if "/api/stop" in str(c)]
        assert len(stop_calls) >= 1

    def test_speak_empty_text_returns_success(self):
        """speak() with empty text should return success with 0 duration."""
        result = speak(text="")

        assert result["success"] is True
        assert result["duration_ms"] == 0

    def test_stop_calls_service(self, mock_api_call, mock_service_running):
        """stop() should call the service."""
        mock_api_call.return_value = {"success": True, "cleared": 2}

        result = stop()

        assert result["success"] is True
        stop_calls = [c for c in mock_api_call.call_args_list if "/api/stop" in str(c)]
        assert len(stop_calls) >= 1

    def test_speak_returns_error_if_service_fails(self, mock_api_call, mock_service_running):
        """speak() should return error if service returns error."""
        mock_api_call.return_value = {"error": "Service error"}

        result = speak(text="Test")

        assert result["success"] is False
        assert "error" in result

    def test_speak_starts_service_if_not_running(self, mock_api_call):
        """speak() should start service if not running."""
        with patch("claude_tts_mcp.server._is_service_running", return_value=False), \
             patch("claude_tts_mcp.server._start_service", return_value=True) as mock_start:
            mock_api_call.return_value = {"success": True, "message_id": 1, "queue_position": 0}

            speak(text="Test")

            mock_start.assert_called_once()


class TestServerInitialization:
    """Test server initialization."""

    def test_create_server_returns_fastmcp_instance(self):
        """create_server should return a FastMCP instance."""
        server = create_server()

        # FastMCP instances have a 'name' attribute
        assert hasattr(server, "name")
        assert server.name == "claude-tts"
