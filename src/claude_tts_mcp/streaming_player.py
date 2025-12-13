"""Streaming audio player using sounddevice."""

import queue
import threading
import numpy as np
import sounddevice as sd


# Track the last used device to detect changes
_last_device_name: str | None = None


def get_current_output_device() -> tuple[int, str]:
    """Get current default output device (index, name)."""
    device_idx = sd.default.device[1]
    device_info = sd.query_devices(device_idx)
    return device_idx, device_info['name']


def get_system_default_output() -> str | None:
    """Query macOS for the actual system default output device name."""
    import subprocess
    try:
        # Use system_profiler to get current audio output
        result = subprocess.run(
            ['system_profiler', 'SPAudioDataType', '-json'],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            audio_data = data.get('SPAudioDataType', [])
            for item in audio_data:
                devices = item.get('_items', [])
                for device in devices:
                    # Look for default output device
                    if device.get('coreaudio_default_audio_output_device') == 'spaudio_yes':
                        return device.get('_name')
    except Exception:
        pass
    return None


def get_output_device_with_refresh() -> tuple[int, str]:
    """Get output device, refreshing device list if system default changed.

    This checks the actual macOS system default and refreshes sounddevice's
    cached device list when a new device is plugged in (like headphones).
    """
    global _last_device_name

    # First, get what sounddevice currently thinks is the default
    try:
        current_idx, current_name = get_current_output_device()
    except Exception:
        current_name = None
        current_idx = None

    # Check the actual macOS system default
    system_default = get_system_default_output()

    # Refresh if: first call, sounddevice name changed, OR system default differs
    needs_refresh = (
        _last_device_name is None or
        current_name != _last_device_name or
        (system_default and system_default != current_name)
    )

    if needs_refresh:
        try:
            sd._terminate()
            sd._initialize()
            current_idx, current_name = get_current_output_device()
        except Exception:
            pass

    _last_device_name = current_name
    return current_idx, current_name


class StreamingPlayer:
    """Streams audio chunks to output as they arrive."""

    def __init__(self):
        self._stream: sd.OutputStream | None = None
        self._queue: queue.Queue[np.ndarray | None] = queue.Queue()
        self._playing = False
        self._interrupted = False
        self._lock = threading.Lock()
        self._playback_thread: threading.Thread | None = None
        self._total_samples = 0
        self._sample_rate = 22050

    def start(self, sample_rate: int) -> None:
        """Start the audio stream for receiving chunks.

        Args:
            sample_rate: Audio sample rate in Hz
        """
        with self._lock:
            if self._playing:
                self.stop()

            self._sample_rate = sample_rate
            self._queue = queue.Queue()
            self._interrupted = False
            self._total_samples = 0
            self._playing = True

            # Get output device, only refreshing if device changed
            # This avoids killing streams that might still be flushing
            default_device, device_name = get_output_device_with_refresh()

            self._stream = sd.OutputStream(
                samplerate=sample_rate,
                channels=1,
                dtype=np.float32,
                blocksize=1024,
                device=default_device,
            )
            self._stream.start()

            self._playback_thread = threading.Thread(target=self._playback_loop)
            self._playback_thread.start()

    def feed(self, samples: np.ndarray) -> bool:
        """Feed audio samples to the player.

        Args:
            samples: Audio samples as float32 numpy array

        Returns:
            True to continue receiving samples, False if interrupted
        """
        if self._interrupted:
            return False

        if len(samples) > 0:
            self._queue.put(samples)
            with self._lock:
                self._total_samples += len(samples)

        return not self._interrupted

    def finish(self) -> float:
        """Signal that all audio has been fed, wait for playback to complete.

        Returns:
            Total duration in milliseconds
        """
        self._queue.put(None)  # Sentinel to signal end

        if self._playback_thread is not None:
            self._playback_thread.join()

        with self._lock:
            duration_ms = (self._total_samples / self._sample_rate) * 1000
            self._cleanup()
            return duration_ms

    def stop(self) -> None:
        """Stop playback immediately."""
        with self._lock:
            self._interrupted = True

        # Clear the queue
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            pass

        self._queue.put(None)  # Ensure playback loop exits

        if self._playback_thread is not None:
            self._playback_thread.join(timeout=0.5)

        with self._lock:
            self._cleanup()

    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._playing

    def _playback_loop(self) -> None:
        """Background thread that writes audio chunks to the stream."""
        while True:
            try:
                samples = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if samples is None:  # Sentinel
                break

            if self._interrupted:
                break

            try:
                if self._stream is not None:
                    self._stream.write(samples)
            except sd.PortAudioError:
                break

        # Wait for the stream buffer to drain before returning
        # This prevents the next message from cutting off the tail of this one
        if self._stream is not None and not self._interrupted:
            try:
                # Calculate remaining buffer time and wait
                # blocksize=1024 at 22050 Hz = ~46ms per block
                # Give it a bit extra to ensure complete playback
                import time
                time.sleep(0.15)  # 150ms should cover the buffer
            except Exception:
                pass

    def _cleanup(self) -> None:
        """Clean up stream resources. Must be called with lock held."""
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except sd.PortAudioError:
                pass
            self._stream = None

        self._playing = False
        self._playback_thread = None
