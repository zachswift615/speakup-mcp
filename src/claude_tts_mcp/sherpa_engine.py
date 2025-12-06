"""Sherpa-onnx TTS engine wrapper."""

from typing import Callable
import numpy as np
import sherpa_onnx

from .tone_mapper import ToneParams

AudioCallback = Callable[[np.ndarray], bool]


class SherpaEngine:
    """Wraps sherpa-onnx for TTS synthesis."""

    def __init__(
        self,
        model_path: str,
        tokens_path: str,
        data_dir: str = "",
        lexicon_path: str = "",
    ):
        """Initialize the TTS engine.

        Args:
            model_path: Path to the ONNX model file
            tokens_path: Path to the tokens.txt file
            data_dir: Path to espeak-ng-data directory (for phonemization)
            lexicon_path: Path to lexicon file (optional)
        """
        # Create VITS model config
        vits_config = sherpa_onnx.OfflineTtsVitsModelConfig(
            model=model_path,
            lexicon=lexicon_path,
            tokens=tokens_path,
            data_dir=data_dir,
        )

        # Create model config
        model_config = sherpa_onnx.OfflineTtsModelConfig(
            vits=vits_config,
            num_threads=1,
            debug=False,
            provider="cpu",
        )

        # Create TTS config
        tts_config = sherpa_onnx.OfflineTtsConfig(model=model_config)

        # Create TTS instance
        self._tts = sherpa_onnx.OfflineTts(tts_config)
        self._loaded = self._tts is not None

    def synthesize_streaming(
        self, text: str, params: ToneParams, callback: AudioCallback
    ) -> None:
        """Synthesize text to audio with streaming callback.

        Args:
            text: Text to synthesize
            params: Tone parameters for synthesis
            callback: Called with audio chunks as they're generated.
                      Return True to continue, False to stop.
        """
        if not text.strip():
            return

        speed = 1.0 / params.length_scale

        def sherpa_callback(samples: np.ndarray, progress: float) -> int:
            samples_float = np.array(samples, dtype=np.float32)
            should_continue = callback(samples_float)
            return 1 if should_continue else 0

        self._tts.generate(text=text, sid=0, speed=speed, callback=sherpa_callback)

    def synthesize(self, text: str, params: ToneParams) -> tuple[np.ndarray, int]:
        """Synthesize text to audio (non-streaming).

        Args:
            text: Text to synthesize
            params: Tone parameters for synthesis

        Returns:
            Tuple of (audio samples as float32 array, sample rate)
        """
        if not text.strip():
            return np.array([], dtype=np.float32), self.sample_rate

        speed = 1.0 / params.length_scale
        audio = self._tts.generate(text=text, sid=0, speed=speed)
        samples = np.array(audio.samples, dtype=np.float32)
        return samples, self.sample_rate

    @property
    def sample_rate(self) -> int:
        """Get the sample rate of the loaded model."""
        return self._tts.sample_rate

    @property
    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self._loaded
