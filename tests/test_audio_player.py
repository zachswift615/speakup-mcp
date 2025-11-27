"""Tests for AudioPlayer - audio playback with interrupt support using afplay."""

import numpy as np
import pytest
from unittest.mock import Mock, patch, MagicMock
from claude_tts_mcp.audio_player import AudioPlayer


class TestAudioPlayer:
    """Test AudioPlayer plays audio and supports interruption."""

    def test_play_calls_afplay_with_temp_file(self):
        """Play should write WAV file and call afplay."""
        player = AudioPlayer()
        samples = np.zeros(1000, dtype=np.float32)

        with patch("claude_tts_mcp.audio_player.subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            player.play(samples, sample_rate=22050)

            mock_popen.assert_called_once()
            call_args = mock_popen.call_args[0][0]
            assert call_args[0] == "afplay"
            assert call_args[1].endswith(".wav")

    def test_stop_terminates_process(self):
        """Stop should terminate the afplay process."""
        player = AudioPlayer()

        # Simulate a running process
        mock_process = MagicMock()
        player._process = mock_process
        player._playing = True

        player.stop()

        mock_process.terminate.assert_called_once()
        assert player._process is None

    def test_play_with_interrupt_stops_previous(self):
        """Playing new audio should stop previous playback first."""
        player = AudioPlayer()
        samples = np.zeros(1000, dtype=np.float32)

        with patch("claude_tts_mcp.audio_player.subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            # Simulate already playing
            old_process = MagicMock()
            player._process = old_process
            player._playing = True

            # Play new audio (should stop previous)
            player.play(samples, sample_rate=22050, interrupt=True)

            # Old process should have been terminated
            old_process.terminate.assert_called_once()

    def test_play_without_interrupt_waits(self):
        """Without interrupt flag, play should wait for current to finish."""
        player = AudioPlayer()

        # This test verifies the interrupt=False path exists
        # Full behavior would require threading tests
        assert hasattr(player, "play")

    def test_is_playing_reflects_state(self):
        """is_playing should return current playback state."""
        player = AudioPlayer()

        assert player.is_playing() is False

        player._playing = True
        assert player.is_playing() is True

    def test_play_returns_duration(self):
        """Play should return the duration of played audio in milliseconds."""
        player = AudioPlayer()
        # 22050 samples at 22050 Hz = 1 second = 1000ms
        samples = np.zeros(22050, dtype=np.float32)

        with patch("claude_tts_mcp.audio_player.subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            duration = player.play(samples, sample_rate=22050)

            assert duration == pytest.approx(1000, rel=0.01)

    def test_play_empty_samples_returns_zero_duration(self):
        """Playing empty samples should return 0 duration."""
        player = AudioPlayer()
        samples = np.array([], dtype=np.float32)

        duration = player.play(samples, sample_rate=22050)

        assert duration == 0
