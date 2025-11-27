"""Tests for VoiceManager - download and manage Piper voices."""

import pytest
from pathlib import Path
from unittest.mock import patch
from claude_tts_mcp.voice_manager import VoiceManager


class TestVoiceManager:
    """Test VoiceManager handles voice download and paths."""

    def test_data_dir_defaults_to_home_claude_tts(self, tmp_path):
        """Data directory should default to ~/.claude-tts."""
        with patch("claude_tts_mcp.voice_manager.Path.home") as mock_home:
            mock_home.return_value = tmp_path
            manager = VoiceManager()

            assert manager.data_dir == tmp_path / ".claude-tts"

    def test_data_dir_created_on_init(self, tmp_path):
        """Data directory should be created if it doesn't exist."""
        manager = VoiceManager(data_dir=tmp_path / "tts-data")

        assert (tmp_path / "tts-data").exists()
        assert (tmp_path / "tts-data" / "voices").exists()

    def test_get_voice_path_returns_model_paths(self, tmp_path):
        """get_voice_path should return paths to model files."""
        manager = VoiceManager(data_dir=tmp_path)

        # Create fake voice files
        voice_dir = tmp_path / "voices" / "en_US-hfc_male-medium"
        voice_dir.mkdir(parents=True)
        (voice_dir / "en_US-hfc_male-medium.onnx").touch()
        (voice_dir / "tokens.txt").touch()

        paths = manager.get_voice_paths("en_US-hfc_male-medium")

        assert paths["model"] == voice_dir / "en_US-hfc_male-medium.onnx"
        assert paths["tokens"] == voice_dir / "tokens.txt"

    def test_get_voice_path_returns_none_if_not_downloaded(self, tmp_path):
        """get_voice_path should return None if voice not present."""
        manager = VoiceManager(data_dir=tmp_path)

        paths = manager.get_voice_paths("nonexistent-voice")

        assert paths is None

    def test_is_voice_available(self, tmp_path):
        """is_voice_available should check if voice files exist."""
        manager = VoiceManager(data_dir=tmp_path)

        # Not available initially
        assert manager.is_voice_available("en_US-hfc_male-medium") is False

        # Create voice files
        voice_dir = tmp_path / "voices" / "en_US-hfc_male-medium"
        voice_dir.mkdir(parents=True)
        (voice_dir / "en_US-hfc_male-medium.onnx").touch()
        (voice_dir / "tokens.txt").touch()

        # Now available
        assert manager.is_voice_available("en_US-hfc_male-medium") is True

    def test_espeak_data_dir_path(self, tmp_path):
        """Should provide path to espeak-ng-data directory."""
        manager = VoiceManager(data_dir=tmp_path)

        assert manager.espeak_data_dir == tmp_path / "espeak-ng-data"

    def test_default_voice_name(self, tmp_path):
        """Should have a default voice name."""
        manager = VoiceManager(data_dir=tmp_path)

        assert manager.default_voice == "en_US-lessac-medium"

    def test_manually_installed_voice_is_detected(self, tmp_path):
        """Manually placed voice files should be detected as available."""
        manager = VoiceManager(data_dir=tmp_path)

        # Simulate manually installing a voice
        voice_dir = tmp_path / "voices" / "en_US-test-medium"
        voice_dir.mkdir(parents=True)
        (voice_dir / "en_US-test-medium.onnx").write_bytes(b"fake model")
        (voice_dir / "tokens.txt").write_text("fake tokens")

        # Verify the voice is now available
        assert manager.is_voice_available("en_US-test-medium") is True
        paths = manager.get_voice_paths("en_US-test-medium")
        assert paths is not None

    def test_list_available_voices(self, tmp_path):
        """list_available_voices should return installed voice names."""
        manager = VoiceManager(data_dir=tmp_path)

        # No voices initially
        assert manager.list_available_voices() == []

        # Add some voices
        (tmp_path / "voices" / "voice1").mkdir(parents=True)
        (tmp_path / "voices" / "voice1" / "voice1.onnx").touch()
        (tmp_path / "voices" / "voice1" / "tokens.txt").touch()

        (tmp_path / "voices" / "voice2").mkdir(parents=True)
        (tmp_path / "voices" / "voice2" / "voice2.onnx").touch()
        (tmp_path / "voices" / "voice2" / "tokens.txt").touch()

        voices = manager.list_available_voices()
        assert set(voices) == {"voice1", "voice2"}
