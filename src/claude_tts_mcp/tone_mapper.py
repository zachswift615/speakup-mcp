"""Maps semantic tones to sherpa-onnx synthesis parameters."""

from dataclasses import dataclass


@dataclass
class ToneParams:
    """Parameters for sherpa-onnx TTS synthesis."""

    noise_scale: float
    noise_scale_w: float
    length_scale: float


# Preset mappings: tone name -> base parameters
_TONE_PRESETS = {
    "neutral": ToneParams(noise_scale=0.667, noise_scale_w=0.8, length_scale=1.0),
    "excited": ToneParams(noise_scale=0.8, noise_scale_w=0.9, length_scale=0.9),
    "concerned": ToneParams(noise_scale=0.5, noise_scale_w=0.6, length_scale=1.1),
    "calm": ToneParams(noise_scale=0.4, noise_scale_w=0.5, length_scale=1.15),
    "urgent": ToneParams(noise_scale=0.7, noise_scale_w=0.85, length_scale=0.85),
}


class ToneMapper:
    """Converts semantic tone names to synthesis parameters."""

    def get_params(self, tone: str, speed: float = 1.0) -> ToneParams:
        """Get synthesis parameters for a tone.

        Args:
            tone: Semantic tone name (neutral, excited, concerned, calm, urgent)
            speed: Speech rate multiplier (0.5-2.0, default 1.0)

        Returns:
            ToneParams with noise_scale, noise_scale_w, length_scale
        """
        base = _TONE_PRESETS.get(tone, _TONE_PRESETS["neutral"])

        # Speed affects length_scale inversely (faster = lower length_scale)
        adjusted_length = base.length_scale / speed

        return ToneParams(
            noise_scale=base.noise_scale,
            noise_scale_w=base.noise_scale_w,
            length_scale=adjusted_length,
        )

    def available_tones(self) -> list[str]:
        """List all available tone names."""
        return list(_TONE_PRESETS.keys())
