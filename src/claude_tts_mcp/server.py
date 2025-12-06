"""MCP Server for Claude TTS - thin client that talks to SpeakUp service."""

import json
import os
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from fastmcp import FastMCP

from .service import DEFAULT_PORT, get_service_pid

SERVICE_URL = f"http://127.0.0.1:{DEFAULT_PORT}"


def _api_call(endpoint: str, method: str = "GET", data: dict = None, timeout: float = 30) -> dict:
    """Make API call to service."""
    url = f"{SERVICE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}

    if data:
        body = json.dumps(data).encode()
        req = Request(url, data=body, headers=headers, method=method)
    else:
        req = Request(url, headers=headers, method=method)

    try:
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read())
    except URLError as e:
        return {"error": f"Service not reachable: {e}"}
    except Exception as e:
        return {"error": str(e)}


def _is_service_running() -> bool:
    """Check if service is running and responsive."""
    try:
        result = _api_call("/api/health", timeout=2)
        return result.get("status") == "ok"
    except Exception:
        return False


def _start_service() -> bool:
    """Start the service in background. Returns True if successful."""
    if _is_service_running():
        return True

    # Start service in background
    subprocess.Popen(
        [sys.executable, "-m", "claude_tts_mcp.service"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    # Wait for it to start
    for _ in range(40):  # 10 seconds max
        time.sleep(0.25)
        if _is_service_running():
            return True

    return False


def _ensure_service() -> bool:
    """Ensure service is running, starting it if needed."""
    if _is_service_running():
        return True
    return _start_service()


def speak(
    text: str,
    tone: str = "neutral",
    speed: float = 1.0,
    interrupt: bool = True,
) -> dict:
    """Speak text aloud with optional emotional tone.

    Args:
        text: Text to speak
        tone: Emotional tone (neutral, excited, concerned, calm, urgent)
        speed: Speech rate multiplier (0.5-2.0, default 1.0)
        interrupt: If True, stops any current speech before starting

    Returns:
        Dict with success status and queue position
    """
    # Handle empty text
    if not text.strip():
        return {"success": True, "duration_ms": 0}

    # Ensure service is running
    if not _ensure_service():
        return {"success": False, "error": "Failed to start SpeakUp service"}

    # Get configuration from environment
    project = os.environ.get("SPEAKUP_PROJECT", "claude")
    announce = os.environ.get("SPEAKUP_ANNOUNCE", "prefix")

    # Stop current playback if interrupt requested
    if interrupt:
        _api_call("/api/stop", method="POST")

    # Send speak request to service
    result = _api_call("/api/speak", method="POST", data={
        "text": text,
        "tone": tone,
        "speed": speed,
        "project": project,
        "announce": announce,
    })

    if "error" in result:
        return {"success": False, "error": result["error"]}

    return {
        "success": True,
        "message_id": result.get("message_id"),
        "queue_position": result.get("queue_position", 0),
    }


def stop() -> dict:
    """Stop any currently playing speech.

    Returns:
        Dict with success status
    """
    if not _is_service_running():
        return {"success": True}

    result = _api_call("/api/stop", method="POST")

    if "error" in result:
        return {"success": False, "error": result["error"]}

    return {"success": True, "cleared": result.get("cleared", 0)}


def create_server() -> FastMCP:
    """Create and configure the MCP server.

    Returns:
        Configured FastMCP server instance
    """
    mcp = FastMCP("claude-tts")

    @mcp.tool()
    def speak_tool(
        text: str,
        tone: str = "neutral",
        speed: float = 1.0,
        interrupt: bool = True,
    ) -> dict:
        """Speak text aloud with optional emotional tone.

        Args:
            text: Text to speak
            tone: Emotional tone (neutral, excited, concerned, calm, urgent)
            speed: Speech rate multiplier (0.5-2.0, default 1.0)
            interrupt: If True, stops any current speech before starting

        Returns:
            Dict with success status and duration_ms
        """
        return speak(text=text, tone=tone, speed=speed, interrupt=interrupt)

    @mcp.tool()
    def stop_tool() -> dict:
        """Stop any currently playing speech.

        Returns:
            Dict with success status
        """
        return stop()

    return mcp


def main():
    """Main entry point for the MCP server."""
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
