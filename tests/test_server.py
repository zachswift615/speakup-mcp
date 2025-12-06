"""Tests for MCP Server - speak and stop tools."""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from claude_tts_mcp.server import create_server, speak, stop
from claude_tts_mcp.tone_mapper import ToneMapper


class TestServerTools:
    """Test MCP server tools."""

    @pytest.fixture
    def mock_engine(self):
        """Create a mock SherpaEngine."""
        engine = MagicMock()
        engine.sample_rate = 22050
        engine.is_loaded = True
        return engine

    @pytest.fixture
    def mock_player(self):
        """Create a mock StreamingPlayer."""
        player = MagicMock()
        player.finish.return_value = 1000.0  # 1 second duration
        player.is_playing.return_value = False
        player.feed.return_value = True
        return player

    @pytest.fixture
    def mock_voice_manager(self, tmp_path):
        """Create a mock VoiceManager with fake voice."""
        manager = MagicMock()
        manager.default_voice = "en_US-lessac-medium"
        manager.is_voice_available.return_value = True
        manager.get_voice_paths.return_value = {
            "model": tmp_path / "model.onnx",
            "tokens": tmp_path / "tokens.txt",
            "data_dir": tmp_path / "espeak-ng-data",
        }
        manager.espeak_data_dir = tmp_path / "espeak-ng-data"
        return manager

    @pytest.fixture
    def tone_mapper(self):
        """Create a real ToneMapper (it's simple enough to use directly)."""
        return ToneMapper()

    def test_speak_returns_success_with_duration(self, mock_engine, mock_player, mock_voice_manager, tone_mapper):
        """speak() should return success and duration."""
        with patch("claude_tts_mcp.server._engine", mock_engine), \
             patch("claude_tts_mcp.server._player", mock_player), \
             patch("claude_tts_mcp.server._voice_manager", mock_voice_manager), \
             patch("claude_tts_mcp.server._tone_mapper", tone_mapper):

            result = speak(text="Hello world")

            assert result["success"] is True
            assert "duration_ms" in result
            mock_engine.synthesize_streaming.assert_called_once()
            mock_player.start.assert_called_once()
            mock_player.finish.assert_called_once()

    def test_speak_uses_tone_mapper(self, mock_engine, mock_player, mock_voice_manager, tone_mapper):
        """speak() should pass tone to ToneMapper."""
        with patch("claude_tts_mcp.server._engine", mock_engine), \
             patch("claude_tts_mcp.server._player", mock_player), \
             patch("claude_tts_mcp.server._voice_manager", mock_voice_manager), \
             patch("claude_tts_mcp.server._tone_mapper", tone_mapper):

            speak(text="Exciting news!", tone="excited")

            # Verify synthesize_streaming was called with params that have excited characteristics
            call_args = mock_engine.synthesize_streaming.call_args
            params = call_args.args[1]  # Second arg is ToneParams
            # Excited tone should have length_scale < 1.0 (faster)
            assert params.length_scale < 1.0

    def test_speak_applies_speed_multiplier(self, mock_engine, mock_player, mock_voice_manager, tone_mapper):
        """speak() should apply speed parameter."""
        with patch("claude_tts_mcp.server._engine", mock_engine), \
             patch("claude_tts_mcp.server._player", mock_player), \
             patch("claude_tts_mcp.server._voice_manager", mock_voice_manager), \
             patch("claude_tts_mcp.server._tone_mapper", tone_mapper):

            speak(text="Fast talking", speed=2.0)

            call_args = mock_engine.synthesize_streaming.call_args
            params = call_args.args[1]
            # Speed 2.0 should halve the length_scale
            assert params.length_scale == pytest.approx(0.5, rel=0.01)

    def test_speak_with_interrupt_stops_current(self, mock_engine, mock_player, mock_voice_manager, tone_mapper):
        """speak() with interrupt=True should stop current playback."""
        mock_player.is_playing.return_value = True

        with patch("claude_tts_mcp.server._engine", mock_engine), \
             patch("claude_tts_mcp.server._player", mock_player), \
             patch("claude_tts_mcp.server._voice_manager", mock_voice_manager), \
             patch("claude_tts_mcp.server._tone_mapper", tone_mapper):

            speak(text="Interrupt!", interrupt=True)

            mock_player.stop.assert_called_once()

    def test_speak_empty_text_returns_success(self, mock_engine, mock_player, mock_voice_manager):
        """speak() with empty text should return success with 0 duration."""
        with patch("claude_tts_mcp.server._engine", mock_engine), \
             patch("claude_tts_mcp.server._player", mock_player), \
             patch("claude_tts_mcp.server._voice_manager", mock_voice_manager):

            result = speak(text="")

            assert result["success"] is True
            assert result["duration_ms"] == 0

    def test_stop_halts_playback(self, mock_player):
        """stop() should halt current playback."""
        with patch("claude_tts_mcp.server._player", mock_player):

            result = stop()

            mock_player.stop.assert_called_once()
            assert result["success"] is True

    def test_speak_returns_error_if_engine_not_loaded(self, mock_player, mock_voice_manager):
        """speak() should return error if engine fails to load."""
        mock_engine = MagicMock()
        mock_engine.is_loaded = False

        with patch("claude_tts_mcp.server._engine", mock_engine), \
             patch("claude_tts_mcp.server._player", mock_player), \
             patch("claude_tts_mcp.server._voice_manager", mock_voice_manager):

            result = speak(text="Test")

            assert result["success"] is False
            assert "error" in result


class TestServerInitialization:
    """Test server initialization."""

    def test_create_server_returns_fastmcp_instance(self):
        """create_server should return a FastMCP instance."""
        with patch("claude_tts_mcp.server.VoiceManager"), \
             patch("claude_tts_mcp.server.SherpaEngine"), \
             patch("claude_tts_mcp.server.StreamingPlayer"):

            server = create_server()

            # FastMCP instances have a 'name' attribute
            assert hasattr(server, "name")
            assert server.name == "claude-tts"
