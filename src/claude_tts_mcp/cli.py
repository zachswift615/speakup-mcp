"""CLI commands for SpeakUp."""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from .service import DEFAULT_PORT, get_service_pid, PID_FILE

SERVICE_URL = f"http://127.0.0.1:{DEFAULT_PORT}"

CLAUDE_MD_SNIPPET = '''## Voice/TTS (Text-to-Speech)

Use `mcp__tts__speak_tool` to speak to the user aloud. Use it liberally - for thinking
out loud, narrating what you're doing, conversing naturally, or any time voice adds to
the experience.

**Parameters:**
- `text` (required): What to say
- `tone`: neutral | excited | concerned | calm | urgent (default: neutral)
- `speed`: 0.5 to 2.0 (default: 1.0)
- `interrupt`: Stop current speech before starting (default: true)

**Example uses:**
- Thinking through a problem out loud
- Announcing task completion or updates
- Reading errors or warnings aloud
- Conversational back-and-forth

**Tone guide:**
- `calm` - explanations, walkthroughs
- `urgent` - errors, critical issues
- `excited` - successes, good news
- `concerned` - warnings, risky operations

Use `mcp__tts__stop_tool` to stop speech mid-playback.
'''


def api_call(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """Make API call to service."""
    url = f"{SERVICE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}

    if data:
        body = json.dumps(data).encode()
        req = Request(url, data=body, headers=headers, method=method)
    else:
        req = Request(url, headers=headers, method=method)

    try:
        with urlopen(req, timeout=5) as response:
            return json.loads(response.read())
    except URLError as e:
        return {"error": f"Service not reachable: {e}"}


def is_service_running() -> bool:
    """Check if service is running and responsive."""
    try:
        result = api_call("/api/health")
        return result.get("status") == "ok"
    except Exception:
        return False


def cmd_status(args):
    """Show queue status."""
    if not is_service_running():
        print("Service is not running.")
        print(f"Start it with: speakup service")
        return 1

    result = api_call("/api/status")
    if "error" in result:
        print(f"Error: {result['error']}")
        return 1

    playing = result.get("playing")
    queued = result.get("queued", [])

    print("=== SpeakUp Status ===\n")

    if playing:
        print(f"NOW PLAYING:")
        print(f"  [{playing['project']}] {playing['text'][:60]}...")
    else:
        print("NOW PLAYING: (nothing)")

    print(f"\nQUEUE ({len(queued)}):")
    if queued:
        for msg in queued[:5]:
            text = msg['text'][:50] + "..." if len(msg['text']) > 50 else msg['text']
            print(f"  [{msg['project']}] {text}")
        if len(queued) > 5:
            print(f"  ... and {len(queued) - 5} more")
    else:
        print("  (empty)")

    return 0


def cmd_history(args):
    """Show message history."""
    if not is_service_running():
        print("Service is not running.")
        return 1

    result = api_call("/api/history")
    if "error" in result:
        print(f"Error: {result['error']}")
        return 1

    messages = result.get("messages", [])
    limit = args.limit or 20

    print("=== SpeakUp History ===\n")

    if not messages:
        print("No history yet.")
        return 0

    for msg in messages[:limit]:
        status = msg['status'].upper()
        created = msg.get('created_at', '')
        # Handle both ISO format (with T) and SQLite format (with space)
        if 'T' in created:
            time_str = created.split('T')[1].split('.')[0]
        elif ' ' in created:
            time_str = created.split(' ')[1].split('.')[0]
        else:
            time_str = created[:8] if created else ''
        text = msg['text'][:60] + "..." if len(msg['text']) > 60 else msg['text']
        print(f"[{time_str}] [{status:7}] {msg['project']}: {text}")

    return 0


def cmd_stop(args):
    """Stop playback and clear queue."""
    if not is_service_running():
        print("Service is not running.")
        return 1

    result = api_call("/api/stop", method="POST")
    if "error" in result:
        print(f"Error: {result['error']}")
        return 1

    cleared = result.get("cleared", 0)
    print(f"Stopped. Cleared {cleared} message(s) from queue.")
    return 0


def cmd_service(args):
    """Start the service."""
    if args.action == "start":
        if is_service_running():
            print(f"Service already running (PID {get_service_pid()})")
            print(f"Web UI: http://127.0.0.1:{DEFAULT_PORT}")
            return 0

        print("Starting SpeakUp service...")
        # Start service in background
        subprocess.Popen(
            [sys.executable, "-m", "claude_tts_mcp.service"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # Wait for it to start
        for _ in range(20):
            time.sleep(0.25)
            if is_service_running():
                print(f"Service started (PID {get_service_pid()})")
                print(f"Web UI: http://127.0.0.1:{DEFAULT_PORT}")
                return 0

        print("Failed to start service. Check logs.")
        return 1

    elif args.action == "stop":
        pid = get_service_pid()
        if not pid:
            print("Service is not running.")
            return 0

        print(f"Stopping service (PID {pid})...")
        try:
            os.kill(pid, signal.SIGTERM)
            # Wait for it to stop
            for _ in range(20):
                time.sleep(0.25)
                if not get_service_pid():
                    print("Service stopped.")
                    return 0
            print("Service did not stop gracefully.")
            return 1
        except ProcessLookupError:
            print("Service already stopped.")
            PID_FILE.unlink(missing_ok=True)
            return 0

    elif args.action == "restart":
        cmd_service(argparse.Namespace(action="stop"))
        time.sleep(0.5)
        return cmd_service(argparse.Namespace(action="start"))

    elif args.action == "status":
        pid = get_service_pid()
        if pid and is_service_running():
            print(f"Service is running (PID {pid})")
            print(f"Web UI: http://127.0.0.1:{DEFAULT_PORT}")
            return 0
        else:
            print("Service is not running.")
            return 1


def cmd_init(args):
    """Initialize SpeakUp in a project directory."""
    project_name = args.project_name
    announce = args.announce or "prefix"
    cwd = Path.cwd()

    print(f"Initializing SpeakUp for project: {project_name}\n")

    # 1. Create or update .mcp.json
    mcp_path = cwd / ".mcp.json"
    mcp_config = {}

    if mcp_path.exists():
        try:
            mcp_config = json.loads(mcp_path.read_text())
            print(f"Found existing .mcp.json")
        except json.JSONDecodeError:
            print(f"Warning: .mcp.json exists but is invalid JSON, will overwrite")
            mcp_config = {}

    # Ensure mcpServers key exists
    if "mcpServers" not in mcp_config:
        mcp_config["mcpServers"] = {}

    # Add or update tts server config
    mcp_config["mcpServers"]["tts"] = {
        "command": "python",
        "args": ["-m", "claude_tts_mcp.server"],
        "env": {
            "SPEAKUP_PROJECT": project_name,
            "SPEAKUP_ANNOUNCE": announce
        }
    }

    mcp_path.write_text(json.dumps(mcp_config, indent=2) + "\n")
    print(f"  Updated .mcp.json with TTS config")

    # 2. Create or update .claude/CLAUDE.md
    claude_dir = cwd / ".claude"
    claude_md_path = claude_dir / "CLAUDE.md"

    claude_dir.mkdir(exist_ok=True)

    if claude_md_path.exists():
        existing_content = claude_md_path.read_text()
        if "mcp__tts__speak_tool" in existing_content:
            print(f"  .claude/CLAUDE.md already has TTS instructions (skipped)")
        else:
            # Append the snippet
            with open(claude_md_path, "a") as f:
                f.write("\n" + CLAUDE_MD_SNIPPET)
            print(f"  Appended TTS instructions to .claude/CLAUDE.md")
    else:
        claude_md_path.write_text(CLAUDE_MD_SNIPPET)
        print(f"  Created .claude/CLAUDE.md with TTS instructions")

    print(f"\nDone! SpeakUp is configured for '{project_name}'")
    print(f"\nNext steps:")
    print(f"  1. Restart Claude Code to load the new MCP config")
    print(f"  2. Claude will now speak with the '{project_name}' prefix")

    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="speakup",
        description="SpeakUp TTS control"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize SpeakUp in a project")
    init_parser.add_argument("project_name", help="Name for this project (used in announcements)")
    init_parser.add_argument(
        "--announce",
        choices=["prefix", "full", "none"],
        default="prefix",
        help="Announcement style (default: prefix)"
    )
    init_parser.set_defaults(func=cmd_init)

    # status command
    status_parser = subparsers.add_parser("status", help="Show queue status")
    status_parser.set_defaults(func=cmd_status)

    # history command
    history_parser = subparsers.add_parser("history", help="Show message history")
    history_parser.add_argument("-n", "--limit", type=int, help="Number of messages")
    history_parser.set_defaults(func=cmd_history)

    # stop command
    stop_parser = subparsers.add_parser("stop", help="Stop playback and clear queue")
    stop_parser.set_defaults(func=cmd_stop)

    # service command
    service_parser = subparsers.add_parser("service", help="Manage the TTS service")
    service_parser.add_argument(
        "action",
        choices=["start", "stop", "restart", "status"],
        help="Service action"
    )
    service_parser.set_defaults(func=cmd_service)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
