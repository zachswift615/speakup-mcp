"""Tests for StreamingPlayer - streaming audio playback with sounddevice."""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from claude_tts_mcp.streaming_player import StreamingPlayer


class TestStreamingPlayer:
    """Test StreamingPlayer streams audio and supports interruption."""

    def test_start_initializes_stream(self):
        """start() should initialize the audio stream."""
        player = StreamingPlayer()

        with patch("claude_tts_mcp.streaming_player.sd.OutputStream") as mock_stream_class, \
             patch("claude_tts_mcp.streaming_player.threading.Thread") as mock_thread_class:
            mock_stream = MagicMock()
            mock_stream_class.return_value = mock_stream
            mock_thread = MagicMock()
            mock_thread_class.return_value = mock_thread

            player.start(sample_rate=22050)

            mock_stream_class.assert_called_once()
            mock_stream.start.assert_called_once()
            mock_thread.start.assert_called_once()
            assert player.is_playing() is True

    def test_feed_queues_samples(self):
        """feed() should queue samples for playback."""
        player = StreamingPlayer()
        player._playing = True
        player._interrupted = False

        samples = np.zeros(1000, dtype=np.float32)
        result = player.feed(samples)

        assert result is True
        assert not player._queue.empty()

    def test_feed_returns_false_when_interrupted(self):
        """feed() should return False when playback is interrupted."""
        player = StreamingPlayer()
        player._playing = True
        player._interrupted = True

        samples = np.zeros(1000, dtype=np.float32)
        result = player.feed(samples)

        assert result is False

    def test_stop_sets_interrupted(self):
        """stop() should set interrupted flag."""
        player = StreamingPlayer()
        player._playing = True
        player._interrupted = False
        player._playback_thread = None  # Don't create real thread

        player.stop()

        assert player._interrupted is True

    def test_is_playing_reflects_state(self):
        """is_playing() should return current playback state."""
        player = StreamingPlayer()

        assert player.is_playing() is False

        player._playing = True
        assert player.is_playing() is True

    def test_finish_returns_duration(self):
        """finish() should return total duration of played audio."""
        player = StreamingPlayer()
        player._sample_rate = 22050
        player._total_samples = 22050  # 1 second of audio
        player._playing = True
        player._playback_thread = None

        with patch.object(player, "_cleanup"):
            duration = player.finish()

        assert duration == pytest.approx(1000, rel=0.01)

    def test_feed_tracks_total_samples(self):
        """feed() should track total samples for duration calculation."""
        player = StreamingPlayer()
        player._playing = True
        player._interrupted = False
        player._total_samples = 0

        samples = np.zeros(1000, dtype=np.float32)
        player.feed(samples)

        assert player._total_samples == 1000
