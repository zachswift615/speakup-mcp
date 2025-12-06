"""Queue manager for serialized TTS playback."""

import queue
import threading
from dataclasses import dataclass
from typing import Optional

from .history import HistoryStore
from .streaming_player import StreamingPlayer
from .sherpa_engine import SherpaEngine
from .tone_mapper import ToneMapper


@dataclass
class SpeakRequest:
    """A request to speak text."""
    message_id: int
    project: str
    text: str
    tone: str = "neutral"
    speed: float = 1.0
    announce: str = "prefix"  # prefix, full, none


class QueueManager:
    """Manages serialized TTS playback queue."""

    def __init__(
        self,
        engine: SherpaEngine,
        history: HistoryStore,
    ):
        self._engine = engine
        self._history = history
        self._tone_mapper = ToneMapper()
        self._player = StreamingPlayer()

        self._queue: queue.Queue[SpeakRequest | None] = queue.Queue()
        self._current_request: Optional[SpeakRequest] = None
        self._lock = threading.Lock()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the queue processing worker."""
        with self._lock:
            if self._running:
                return

            self._running = True
            self._worker_thread = threading.Thread(
                target=self._process_queue,
                daemon=True
            )
            self._worker_thread.start()

    def stop(self) -> None:
        """Stop the queue manager."""
        with self._lock:
            self._running = False

        self._queue.put(None)  # Signal worker to exit

        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)

    def enqueue(self, request: SpeakRequest) -> None:
        """Add a speak request to the queue."""
        self._queue.put(request)

    def stop_and_clear(self) -> int:
        """Stop current playback and clear queue. Returns count cleared."""
        # Stop current playback
        self._player.stop()

        # Clear the queue and mark messages as skipped
        cleared = 0
        with self._lock:
            # Mark current as skipped if playing
            if self._current_request:
                self._history.mark_skipped(self._current_request.message_id)
                self._current_request = None
                cleared += 1

        # Drain the queue
        while True:
            try:
                req = self._queue.get_nowait()
                if req is not None:
                    self._history.mark_skipped(req.message_id)
                    cleared += 1
            except queue.Empty:
                break

        return cleared

    def get_status(self) -> dict:
        """Get current queue status."""
        queued = []
        # Snapshot the queue (non-destructive peek isn't easy, so we use history)
        queued_from_db = self._history.get_queued()
        playing = self._history.get_playing()

        return {
            "playing": playing,
            "queued": queued_from_db,
            "queue_size": len(queued_from_db),
        }

    def _process_queue(self) -> None:
        """Worker thread that processes the queue."""
        while self._running:
            try:
                request = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if request is None:  # Shutdown signal
                break

            self._play_request(request)

    def _play_request(self, request: SpeakRequest) -> None:
        """Play a single speak request."""
        with self._lock:
            self._current_request = request

        # Mark as playing in history
        self._history.mark_playing(request.message_id)

        # Build the full text with optional prefix
        full_text = self._build_text(request)

        # Get tone parameters
        params = self._tone_mapper.get_params(request.tone, speed=request.speed)

        # Start streaming player
        self._player.start(self._engine.sample_rate)

        # Synthesize with streaming
        self._engine.synthesize_streaming(full_text, params, callback=self._player.feed)

        # Wait for playback to complete
        duration_ms = self._player.finish()

        # Mark as played (if not interrupted)
        with self._lock:
            if self._current_request and self._current_request.message_id == request.message_id:
                self._history.mark_played(request.message_id, duration_ms)
                self._current_request = None

    def _build_text(self, request: SpeakRequest) -> str:
        """Build full text with optional project announcement."""
        if request.announce == "none" or not request.project:
            return request.text

        if request.announce == "full":
            return f"This is Claude from {request.project}: {request.text}"

        # Default: prefix
        return f"{request.project}: {request.text}"
