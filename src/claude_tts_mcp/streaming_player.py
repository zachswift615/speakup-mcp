"""Streaming audio player using sounddevice."""

import queue
import threading
import numpy as np
import sounddevice as sd


def refresh_audio_devices() -> None:
    """Refresh sounddevice's audio device list.

    Call this ONLY when no audio streams are active, as it
    terminates and reinitializes PortAudio.
    """
    try:
        sd._terminate()
        sd._initialize()
    except Exception:
        pass


def get_current_output_device() -> tuple[int, str]:
    """Get current default output device (index, name)."""
    device_idx = sd.default.device[1]
    device_info = sd.query_devices(device_idx)
    return device_idx, device_info['name']


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

            # Refresh device list before starting playback
            # This picks up Bluetooth headphones that connected since last playback
            refresh_audio_devices()

            # Get the current default output device
            default_device, device_name = get_current_output_device()

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
