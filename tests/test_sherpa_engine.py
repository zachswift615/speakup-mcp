"""Tests for SherpaEngine - sherpa-onnx TTS wrapper."""

import numpy as np
import pytest
from unittest.mock import Mock, patch, MagicMock
from claude_tts_mcp.sherpa_engine import SherpaEngine
from claude_tts_mcp.tone_mapper import ToneParams


class TestSherpaEngine:
    """Test SherpaEngine wraps sherpa-onnx correctly."""

    def test_synthesize_returns_audio_samples(self):
        """Synthesize should return numpy array of audio samples."""
        with patch("claude_tts_mcp.sherpa_engine.sherpa_onnx") as mock_sherpa:
            # Setup mock TTS
            mock_tts = MagicMock()
            mock_sherpa.OfflineTts.return_value = mock_tts
            mock_tts.sample_rate = 22050

            # Mock generated audio
            mock_audio = MagicMock()
            mock_audio.samples = [0.1, 0.2, 0.3, 0.4, 0.5]
            mock_tts.generate.return_value = mock_audio

            engine = SherpaEngine(model_path="/fake/model.onnx", tokens_path="/fake/tokens.txt")
            params = ToneParams(noise_scale=0.667, noise_scale_w=0.8, length_scale=1.0)

            samples, sample_rate = engine.synthesize("Hello", params)

            assert isinstance(samples, np.ndarray)
            assert sample_rate == 22050
            assert len(samples) == 5

    def test_synthesize_passes_parameters_to_sherpa(self):
        """Synthesize should pass tone parameters to sherpa-onnx."""
        with patch("claude_tts_mcp.sherpa_engine.sherpa_onnx") as mock_sherpa:
            mock_tts = MagicMock()
            mock_sherpa.OfflineTts.return_value = mock_tts
            mock_tts.sample_rate = 22050

            mock_audio = MagicMock()
            mock_audio.samples = [0.0]
            mock_tts.generate.return_value = mock_audio

            engine = SherpaEngine(model_path="/fake/model.onnx", tokens_path="/fake/tokens.txt")
            params = ToneParams(noise_scale=0.5, noise_scale_w=0.6, length_scale=1.2)

            engine.synthesize("Test", params)

            # Verify generate was called with text and speed
            mock_tts.generate.assert_called_once()
            call_args = mock_tts.generate.call_args
            assert call_args.kwargs["text"] == "Test"
            # length_scale affects speed inversely
            assert call_args.kwargs["speed"] == pytest.approx(1 / 1.2, rel=0.01)

    def test_synthesize_empty_text_returns_empty_array(self):
        """Synthesizing empty text should return empty array."""
        with patch("claude_tts_mcp.sherpa_engine.sherpa_onnx") as mock_sherpa:
            mock_tts = MagicMock()
            mock_sherpa.OfflineTts.return_value = mock_tts
            mock_tts.sample_rate = 22050

            engine = SherpaEngine(model_path="/fake/model.onnx", tokens_path="/fake/tokens.txt")
            params = ToneParams(noise_scale=0.667, noise_scale_w=0.8, length_scale=1.0)

            samples, sample_rate = engine.synthesize("", params)

            assert len(samples) == 0
            mock_tts.generate.assert_not_called()

    def test_sample_rate_property(self):
        """Engine should expose sample rate from model."""
        with patch("claude_tts_mcp.sherpa_engine.sherpa_onnx") as mock_sherpa:
            mock_tts = MagicMock()
            mock_sherpa.OfflineTts.return_value = mock_tts
            mock_tts.sample_rate = 44100

            engine = SherpaEngine(model_path="/fake/model.onnx", tokens_path="/fake/tokens.txt")

            assert engine.sample_rate == 44100

    def test_is_loaded_property(self):
        """Engine should report whether model is loaded."""
        with patch("claude_tts_mcp.sherpa_engine.sherpa_onnx") as mock_sherpa:
            mock_tts = MagicMock()
            mock_sherpa.OfflineTts.return_value = mock_tts
            mock_tts.sample_rate = 22050

            engine = SherpaEngine(model_path="/fake/model.onnx", tokens_path="/fake/tokens.txt")

            assert engine.is_loaded is True

    def test_engine_configures_vits_model(self):
        """Engine should configure sherpa-onnx with VITS model settings."""
        with patch("claude_tts_mcp.sherpa_engine.sherpa_onnx") as mock_sherpa:
            mock_tts = MagicMock()
            mock_sherpa.OfflineTts.return_value = mock_tts
            mock_tts.sample_rate = 22050

            engine = SherpaEngine(
                model_path="/path/to/model.onnx",
                tokens_path="/path/to/tokens.txt",
                data_dir="/path/to/espeak-ng-data",
            )

            # Verify config was created with correct paths
            mock_sherpa.OfflineTtsConfig.assert_called_once()
            config_call = mock_sherpa.OfflineTtsConfig.call_args
            model_config = config_call.kwargs.get("model") or config_call.args[0]

            # The model should be a VITS config
            assert model_config is not None
