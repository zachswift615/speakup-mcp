"""Voice management - download and manage Piper TTS voices."""

from pathlib import Path
from typing import Optional


class VoiceManager:
    """Manages Piper TTS voice downloads and paths."""

    DEFAULT_VOICE = "en_US-lessac-medium"

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize voice manager.

        Args:
            data_dir: Base directory for voice storage. Defaults to ~/.claude-tts
        """
        if data_dir is None:
            data_dir = Path.home() / ".claude-tts"

        self._data_dir = Path(data_dir)
        self._voices_dir = self._data_dir / "voices"
        self._espeak_dir = self._data_dir / "espeak-ng-data"

        # Create directories
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._voices_dir.mkdir(parents=True, exist_ok=True)

    @property
    def data_dir(self) -> Path:
        """Get the base data directory."""
        return self._data_dir

    @property
    def espeak_data_dir(self) -> Path:
        """Get the espeak-ng-data directory path."""
        return self._espeak_dir

    @property
    def default_voice(self) -> str:
        """Get the default voice name."""
        return self.DEFAULT_VOICE

    def get_voice_paths(self, voice_name: str) -> Optional[dict[str, Path]]:
        """Get paths to voice model files.

        Args:
            voice_name: Name of the voice (e.g., 'en_US-lessac-medium')

        Returns:
            Dict with 'model', 'tokens', and 'data_dir' paths, or None if not available
        """
        voice_dir = self._voices_dir / voice_name
        model_path = voice_dir / f"{voice_name}.onnx"
        tokens_path = voice_dir / "tokens.txt"

        if not model_path.exists() or not tokens_path.exists():
            return None

        # Check for bundled espeak-ng-data first, fall back to global
        bundled_data = voice_dir / "espeak-ng-data"
        data_dir = bundled_data if bundled_data.exists() else self._espeak_dir

        return {
            "model": model_path,
            "tokens": tokens_path,
            "data_dir": data_dir,
        }

    def is_voice_available(self, voice_name: str) -> bool:
        """Check if a voice is downloaded and available.

        Args:
            voice_name: Name of the voice

        Returns:
            True if voice files exist
        """
        return self.get_voice_paths(voice_name) is not None

    def list_available_voices(self) -> list[str]:
        """List all downloaded voices.

        Returns:
            List of voice names
        """
        voices = []
        if not self._voices_dir.exists():
            return voices

        for voice_dir in self._voices_dir.iterdir():
            if voice_dir.is_dir():
                voice_name = voice_dir.name
                if self.is_voice_available(voice_name):
                    voices.append(voice_name)

        return voices
