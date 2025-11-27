"""Audio playback with interrupt support using afplay (macOS)."""

import subprocess
import tempfile
import threading
import wave
import numpy as np


class AudioPlayer:
    """Plays audio samples with support for interruption using afplay."""

    def __init__(self):
        self._playing = False
        self._process: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def play(
        self, samples: np.ndarray, sample_rate: int, interrupt: bool = True
    ) -> float:
        """Play audio samples.

        Args:
            samples: Audio samples as float32 numpy array
            sample_rate: Sample rate in Hz
            interrupt: If True, stop any current playback first

        Returns:
            Duration of audio in milliseconds
        """
        if len(samples) == 0:
            return 0

        if interrupt and self._playing:
            self.stop()

        duration_ms = (len(samples) / sample_rate) * 1000

        # Convert float32 samples to int16 for WAV file
        samples_int16 = (samples * 32767).astype(np.int16)

        # Write to temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            with wave.open(f, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)  # 16-bit
                wav.setframerate(sample_rate)
                wav.writeframes(samples_int16.tobytes())

        with self._lock:
            self._playing = True

        try:
            # Use afplay (macOS) to play the audio
            self._process = subprocess.Popen(
                ["afplay", temp_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._process.wait()
        finally:
            with self._lock:
                self._playing = False
                self._process = None
            # Clean up temp file
            try:
                import os
                os.unlink(temp_path)
            except OSError:
                pass

        return duration_ms

    def stop(self) -> None:
        """Stop any currently playing audio."""
        with self._lock:
            if self._process is not None:
                self._process.terminate()
                self._process = None

    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._playing
