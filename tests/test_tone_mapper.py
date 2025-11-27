"""Tests for ToneMapper - converts semantic tones to sherpa-onnx parameters."""

import pytest
from claude_tts_mcp.tone_mapper import ToneMapper, ToneParams


class TestToneMapper:
    """Test ToneMapper converts tones to synthesis parameters."""

    def test_neutral_tone_returns_default_parameters(self):
        """Neutral tone should return balanced default parameters."""
        mapper = ToneMapper()

        params = mapper.get_params("neutral")

        assert params.noise_scale == pytest.approx(0.667, rel=0.01)
        assert params.noise_scale_w == pytest.approx(0.8, rel=0.01)
        assert params.length_scale == pytest.approx(1.0, rel=0.01)

    def test_excited_tone_has_more_variation_and_faster(self):
        """Excited tone should have more variation and be slightly faster."""
        mapper = ToneMapper()

        params = mapper.get_params("excited")

        # More variation (higher noise scales)
        assert params.noise_scale > 0.667
        assert params.noise_scale_w > 0.8
        # Faster (lower length_scale)
        assert params.length_scale < 1.0

    def test_concerned_tone_has_less_variation_and_slower(self):
        """Concerned tone should be steadier and slower."""
        mapper = ToneMapper()

        params = mapper.get_params("concerned")

        # Less variation (lower noise scales)
        assert params.noise_scale < 0.667
        assert params.noise_scale_w < 0.8
        # Slower (higher length_scale)
        assert params.length_scale > 1.0

    def test_calm_tone_is_steady_and_relaxed(self):
        """Calm tone should be very steady with minimal variation."""
        mapper = ToneMapper()

        params = mapper.get_params("calm")

        # Very low variation
        assert params.noise_scale < 0.5
        assert params.noise_scale_w < 0.6
        # Relaxed pace
        assert params.length_scale > 1.1

    def test_urgent_tone_is_punchy_and_fast(self):
        """Urgent tone should be energetic and fast."""
        mapper = ToneMapper()

        params = mapper.get_params("urgent")

        # Moderate-high variation for energy
        assert params.noise_scale > 0.6
        # Fast pace
        assert params.length_scale < 0.9

    def test_unknown_tone_defaults_to_neutral(self):
        """Unknown tones should fall back to neutral."""
        mapper = ToneMapper()

        params = mapper.get_params("unknown_tone")
        neutral = mapper.get_params("neutral")

        assert params.noise_scale == neutral.noise_scale
        assert params.noise_scale_w == neutral.noise_scale_w
        assert params.length_scale == neutral.length_scale

    def test_speed_multiplier_affects_length_scale(self):
        """Speed parameter should multiply the length_scale inversely."""
        mapper = ToneMapper()

        # Speed 2.0 = twice as fast = half the length_scale
        params = mapper.get_params("neutral", speed=2.0)

        assert params.length_scale == pytest.approx(0.5, rel=0.01)

    def test_speed_slow_increases_length_scale(self):
        """Slow speed should increase length_scale."""
        mapper = ToneMapper()

        # Speed 0.5 = half as fast = double the length_scale
        params = mapper.get_params("neutral", speed=0.5)

        assert params.length_scale == pytest.approx(2.0, rel=0.01)

    def test_list_available_tones(self):
        """Should be able to list all available tones."""
        mapper = ToneMapper()

        tones = mapper.available_tones()

        assert "neutral" in tones
        assert "excited" in tones
        assert "concerned" in tones
        assert "calm" in tones
        assert "urgent" in tones
