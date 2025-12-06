"""HTTP service for centralized TTS playback."""

import json
import os
import signal
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

from .history import HistoryStore
from .queue_manager import QueueManager, SpeakRequest
from .sherpa_engine import SherpaEngine
from .voice_manager import VoiceManager

DEFAULT_PORT = 7849
PID_FILE = Path.home() / ".speakup" / "service.pid"


class TTSServiceHandler(BaseHTTPRequestHandler):
    """HTTP request handler for TTS service."""

    queue_manager: QueueManager
    history: HistoryStore

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def _send_json(self, data: dict, status: int = 200) -> None:
        """Send JSON response."""
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status: int = 200) -> None:
        """Send HTML response."""
        body = html.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "":
            self._serve_ui()
        elif path == "/api/status":
            self._get_status()
        elif path == "/api/history":
            self._get_history()
        elif path == "/api/health":
            self._send_json({"status": "ok"})
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/speak":
            self._post_speak()
        elif path == "/api/stop":
            self._post_stop()
        else:
            self._send_json({"error": "Not found"}, 404)

    def _get_status(self) -> None:
        """Get queue status."""
        status = self.queue_manager.get_status()
        self._send_json(status)

    def _get_history(self) -> None:
        """Get message history."""
        messages = self.history.get_recent(100)
        self._send_json({"messages": messages})

    def _post_speak(self) -> None:
        """Handle speak request."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        text = data.get("text", "").strip()
        if not text:
            self._send_json({"error": "No text provided"}, 400)
            return

        project = data.get("project", "unknown")
        tone = data.get("tone", "neutral")
        speed = float(data.get("speed", 1.0))
        announce = data.get("announce", "prefix")

        # Add to history first
        message_id = self.history.add_message(project, text, tone)

        # Create and enqueue request
        request = SpeakRequest(
            message_id=message_id,
            project=project,
            text=text,
            tone=tone,
            speed=speed,
            announce=announce,
        )
        self.queue_manager.enqueue(request)

        status = self.queue_manager.get_status()
        self._send_json({
            "success": True,
            "message_id": message_id,
            "queue_position": status["queue_size"],
        })

    def _post_stop(self) -> None:
        """Stop playback and clear queue."""
        cleared = self.queue_manager.stop_and_clear()
        self._send_json({
            "success": True,
            "cleared": cleared,
        })

    def _serve_ui(self) -> None:
        """Serve the web UI."""
        html = WEB_UI_HTML
        self._send_html(html)


WEB_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpeakUp</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 600px; margin: 0 auto; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 20px;
            background: #16213e;
            border-radius: 12px 12px 0 0;
            border-bottom: 1px solid #0f3460;
        }
        h1 { font-size: 1.5rem; font-weight: 600; }
        .stop-btn {
            background: #e94560;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            font-size: 0.9rem;
            transition: background 0.2s;
        }
        .stop-btn:hover { background: #ff6b6b; }
        .stop-btn:active { transform: scale(0.98); }
        section {
            background: #16213e;
            padding: 15px 20px;
            border-bottom: 1px solid #0f3460;
        }
        section:last-child { border-radius: 0 0 12px 12px; border-bottom: none; }
        .section-title {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #888;
            margin-bottom: 10px;
        }
        .now-playing {
            background: #0f3460;
            padding: 12px 15px;
            border-radius: 8px;
            border-left: 3px solid #e94560;
        }
        .now-playing.empty {
            border-left-color: #444;
            color: #666;
            font-style: italic;
        }
        .message {
            padding: 10px 0;
            border-bottom: 1px solid #0f3460;
        }
        .message:last-child { border-bottom: none; }
        .message-project {
            font-weight: 600;
            color: #4fc3f7;
            font-size: 0.85rem;
        }
        .message-text {
            margin-top: 4px;
            color: #ccc;
            font-size: 0.9rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .message-meta {
            font-size: 0.75rem;
            color: #666;
            margin-top: 4px;
        }
        .status-badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.7rem;
            text-transform: uppercase;
        }
        .status-played { background: #2e7d32; }
        .status-skipped { background: #f57c00; }
        .status-queued { background: #1565c0; }
        .status-playing { background: #e94560; }
        .empty-state {
            color: #666;
            font-style: italic;
            padding: 10px 0;
        }
        .queue-count {
            background: #0f3460;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.8rem;
            margin-left: 8px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>SpeakUp</h1>
            <button class="stop-btn" onclick="stopAll()">Stop All</button>
        </header>

        <section>
            <div class="section-title">Now Playing</div>
            <div id="now-playing" class="now-playing empty">Nothing playing</div>
        </section>

        <section>
            <div class="section-title">Queue <span id="queue-count" class="queue-count">0</span></div>
            <div id="queue"></div>
        </section>

        <section>
            <div class="section-title">History</div>
            <div id="history"></div>
        </section>
    </div>

    <script>
        async function fetchStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                updatePlaying(data.playing);
                updateQueue(data.queued);
                document.getElementById('queue-count').textContent = data.queue_size;
            } catch (e) {
                console.error('Failed to fetch status:', e);
            }
        }

        async function fetchHistory() {
            try {
                const res = await fetch('/api/history');
                const data = await res.json();
                updateHistory(data.messages);
            } catch (e) {
                console.error('Failed to fetch history:', e);
            }
        }

        function updatePlaying(playing) {
            const el = document.getElementById('now-playing');
            if (playing) {
                el.className = 'now-playing';
                el.innerHTML = `<span class="message-project">${esc(playing.project)}</span>
                    <div class="message-text">${esc(playing.text)}</div>`;
            } else {
                el.className = 'now-playing empty';
                el.textContent = 'Nothing playing';
            }
        }

        function updateQueue(queued) {
            const el = document.getElementById('queue');
            if (!queued || queued.length === 0) {
                el.innerHTML = '<div class="empty-state">Queue is empty</div>';
                return;
            }
            el.innerHTML = queued.map(m => `
                <div class="message">
                    <span class="message-project">${esc(m.project)}</span>
                    <div class="message-text">${esc(m.text)}</div>
                </div>
            `).join('');
        }

        function updateHistory(messages) {
            const el = document.getElementById('history');
            const played = messages.filter(m => m.status !== 'queued');
            if (played.length === 0) {
                el.innerHTML = '<div class="empty-state">No history yet</div>';
                return;
            }
            el.innerHTML = played.slice(0, 20).map(m => `
                <div class="message">
                    <span class="message-project">${esc(m.project)}</span>
                    <span class="status-badge status-${m.status}">${m.status}</span>
                    <div class="message-text">${esc(m.text)}</div>
                    <div class="message-meta">${formatTime(m.created_at)}</div>
                </div>
            `).join('');
        }

        async function stopAll() {
            try {
                await fetch('/api/stop', { method: 'POST' });
                fetchStatus();
                fetchHistory();
            } catch (e) {
                console.error('Failed to stop:', e);
            }
        }

        function esc(s) {
            if (!s) return '';
            return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }

        function formatTime(ts) {
            if (!ts) return '';
            const d = new Date(ts);
            return d.toLocaleTimeString();
        }

        // Poll for updates
        fetchStatus();
        fetchHistory();
        setInterval(fetchStatus, 1000);
        setInterval(fetchHistory, 3000);
    </script>
</body>
</html>
"""


def write_pid_file() -> None:
    """Write PID file for service discovery."""
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))


def remove_pid_file() -> None:
    """Remove PID file."""
    try:
        PID_FILE.unlink()
    except FileNotFoundError:
        pass


def get_service_pid() -> Optional[int]:
    """Get PID of running service, or None if not running."""
    try:
        pid = int(PID_FILE.read_text().strip())
        # Check if process is actually running
        os.kill(pid, 0)
        return pid
    except (FileNotFoundError, ValueError, ProcessLookupError, PermissionError):
        return None


def run_service(port: int = DEFAULT_PORT) -> None:
    """Run the TTS service."""
    # Check if already running
    existing_pid = get_service_pid()
    if existing_pid:
        print(f"Service already running (PID {existing_pid})")
        sys.exit(1)

    # Initialize components
    voice_manager = VoiceManager()
    voice_name = voice_manager.default_voice

    if not voice_manager.is_voice_available(voice_name):
        print(f"Voice '{voice_name}' not found. Run setup first.")
        sys.exit(1)

    paths = voice_manager.get_voice_paths(voice_name)
    engine = SherpaEngine(
        model_path=str(paths["model"]),
        tokens_path=str(paths["tokens"]),
        data_dir=str(paths["data_dir"]),
    )

    history = HistoryStore()
    queue_manager = QueueManager(engine, history)

    # Attach to handler class
    TTSServiceHandler.queue_manager = queue_manager
    TTSServiceHandler.history = history

    # Start queue processing
    queue_manager.start()

    # Write PID file
    write_pid_file()

    # Setup signal handlers
    def shutdown(signum, frame):
        print("\nShutting down...")
        queue_manager.stop()
        remove_pid_file()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Start HTTP server
    server = HTTPServer(("127.0.0.1", port), TTSServiceHandler)
    print(f"SpeakUp service running on http://127.0.0.1:{port}")

    try:
        server.serve_forever()
    finally:
        queue_manager.stop()
        remove_pid_file()


def main():
    """Entry point for speakup-service command."""
    import argparse
    parser = argparse.ArgumentParser(description="SpeakUp TTS Service")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to listen on")
    args = parser.parse_args()
    run_service(args.port)


if __name__ == "__main__":
    main()
