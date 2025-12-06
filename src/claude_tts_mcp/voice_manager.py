"""Voice management - download and manage Piper TTS voices."""

import sys
from pathlib import Path
from typing import Optional


def get_bundled_voices_dir() -> Optional[Path]:
    """Find bundled voices directory if running from standalone binary.

    Checks for voices in the following locations:
    1. macOS .app bundle: ../Resources/voices (relative to executable)
    2. Nuitka standalone: ./voices (relative to executable)

    Returns:
        Path to bundled voices directory, or None if not bundled
    """
    exe_path = Path(sys.executable)

    # Check 1: macOS .app bundle
    # Executable is at: SpeakUp.app/Contents/MacOS/speakup
    # Voices are at: SpeakUp.app/Contents/Resources/voices
    if sys.platform == "darwin":
        app_resources = exe_path.parent.parent / "Resources" / "voices"
        if app_resources.exists() and app_resources.is_dir():
            return app_resources

    # Check 2: Nuitka standalone (Linux or non-.app macOS)
    # Voices are at: speakup.dist/voices
    standalone_voices = exe_path.parent / "voices"
    if standalone_voices.exists() and standalone_voices.is_dir():
        return standalone_voices

    return None


def is_bundled_mode() -> bool:
    """Check if running from a bundled standalone binary."""
    return get_bundled_voices_dir() is not None


class VoiceManager:
    """Manages Piper TTS voice downloads and paths."""

    DEFAULT_VOICE = "en_US-lessac-medium"

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize voice manager.

        Args:
            data_dir: Base directory for voice storage. Defaults to ~/.claude-tts
                     If running from bundled binary, uses bundled voices.
        """
        # Check for bundled voices first
        self._bundled_dir = get_bundled_voices_dir()

        if data_dir is None:
            data_dir = Path.home() / ".claude-tts"

        self._data_dir = Path(data_dir)
        self._voices_dir = self._data_dir / "voices"
        self._espeak_dir = self._data_dir / "espeak-ng-data"

        # Create directories (for user data, even in bundled mode)
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
        # Check bundled voices first (for standalone binary)
        if self._bundled_dir is not None:
            bundled_voice_dir = self._bundled_dir / voice_name
            bundled_model = bundled_voice_dir / f"{voice_name}.onnx"
            bundled_tokens = bundled_voice_dir / "tokens.txt"

            if bundled_model.exists() and bundled_tokens.exists():
                # Bundled espeak-ng-data is at same level as voice directories
                bundled_espeak = self._bundled_dir / "espeak-ng-data"
                data_dir = bundled_espeak if bundled_espeak.exists() else self._espeak_dir

                return {
                    "model": bundled_model,
                    "tokens": bundled_tokens,
                    "data_dir": data_dir,
                }

        # Fall back to user-installed voices
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
            List of voice names (bundled + user-installed)
        """
        voices = set()

        # Check bundled voices first
        if self._bundled_dir is not None and self._bundled_dir.exists():
            for voice_dir in self._bundled_dir.iterdir():
                if voice_dir.is_dir() and voice_dir.name != "espeak-ng-data":
                    voice_name = voice_dir.name
                    if self.is_voice_available(voice_name):
                        voices.add(voice_name)

        # Add user-installed voices
        if self._voices_dir.exists():
            for voice_dir in self._voices_dir.iterdir():
                if voice_dir.is_dir():
                    voice_name = voice_dir.name
                    if self.is_voice_available(voice_name):
                        voices.add(voice_name)

        return sorted(list(voices))
