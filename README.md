# SpeakUp MCP Server

An MCP server that gives Claude Code text-to-speech capabilities with support for multiple simultaneous instances, message queuing, and a web UI for monitoring.

## Features

- **Centralized queue** - Multiple Claude Code instances share one audio output, no overlapping
- **Project identification** - Each message announces which project it's from
- **Web UI** - Monitor queue, history, and stop playback at http://localhost:7849
- **CLI control** - `speakup status`, `speakup stop`, `speakup history`
- **5 emotional tones** - neutral, excited, concerned, calm, urgent
- **Streaming playback** - Audio starts immediately, doesn't wait for full synthesis
- **Persistent history** - SQLite storage of all messages

## Architecture

```
Claude Code #1        Claude Code #2        Claude Code #3
     │                     │                     │
     ▼                     ▼                     ▼
MCP Server #1         MCP Server #2         MCP Server #3
(thin client)         (thin client)         (thin client)
     │                     │                     │
     └─────────────────────┼─────────────────────┘
                           ▼
              ┌────────────────────────┐
              │   SpeakUp Service      │
              │   localhost:7849       │
              │   ─────────────────    │
              │   • FIFO queue         │
              │   • SQLite history     │
              │   • Web UI             │
              │   • Streaming playback │
              └────────────────────────┘
```

## Quick Setup

```bash
# Clone and install
git clone https://github.com/zachswift615/speakup-mcp.git
cd speakup-mcp
pip install -e .

# Download voice files (~70MB)
python scripts/setup.py
```

## Claude Code Configuration

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "tts": {
      "command": "python",
      "args": ["-m", "claude_tts_mcp.server"],
      "env": {
        "SPEAKUP_PROJECT": "my-project-name",
        "SPEAKUP_ANNOUNCE": "prefix"
      }
    }
  }
}
```

### Environment Variables

| Variable | Values | Description |
|----------|--------|-------------|
| `SPEAKUP_PROJECT` | any string | Project name shown in messages (default: "claude") |
| `SPEAKUP_ANNOUNCE` | `prefix`, `full`, `none` | How to announce the project |

**Announce modes:**
- `prefix` - "my-project: Hello world" (default)
- `full` - "This is Claude from my-project: Hello world"
- `none` - "Hello world" (no announcement)

## CLI Commands

```bash
# Service management
speakup service start     # Start the background service
speakup service stop      # Stop the service
speakup service status    # Check if service is running

# Playback control
speakup stop              # Stop current playback and clear queue
speakup status            # Show what's playing and queued
speakup history           # Show recent messages
speakup history -n 50     # Show last 50 messages
```

## Web UI

Open http://localhost:7849 to see:

- **Now Playing** - Current message being spoken
- **Queue** - Messages waiting to play
- **History** - Recent messages with status (played/skipped)
- **Stop All** button - Stop playback and clear queue

The service auto-starts when the first MCP tool is invoked.

## Usage

Once configured, Claude Code can use the TTS tools:

```python
# Simple speech
speak(text="Hello world!")

# With emotional tone
speak(text="All tests passed!", tone="excited")

# Warning
speak(text="Found 3 errors", tone="concerned")

# Fast speech
speak(text="Quick update", speed=1.5)

# Stop current speech and clear queue
stop()
```

### Tones

| Tone | Effect |
|------|--------|
| `neutral` | Default, clear speech |
| `excited` | More variation, slightly faster |
| `concerned` | Steadier, slower |
| `calm` | Very steady, relaxed pace |
| `urgent` | Energetic, fast |

## CLAUDE.md Integration

Add this to your project's `CLAUDE.md` to encourage Claude to use TTS effectively:

```markdown
## Voice/TTS (Text-to-Speech)

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
```

## Why Use This?

### Multi-Instance Support

Running multiple Claude Code windows? Messages queue up instead of talking over each other. Each message is prefixed with its project name so you know which instance is speaking.

### Subagent Visibility

When using subagent-driven development, you typically have limited visibility into what agents are doing. With TTS instructions in your CLAUDE.md, subagents announce their progress as they work - giving you real-time audio feedback without watching the terminal.

### Token Efficient

The MCP interface is minimal:
- **Responses**: `{"success": true, "message_id": 1, "queue_position": 0}`

No verbose payloads, no unnecessary metadata.

### Streaming Playback

Audio begins playing immediately as it's synthesized, rather than waiting for full generation. This reduces time-to-first-sound significantly for longer text.

## Data Storage

- **History database**: `~/.speakup/history.db` (SQLite)
- **Service PID file**: `~/.speakup/service.pid`
- **Voice models**: `~/.claude-tts/voices/`

## Manual Voice Setup

If you prefer manual setup, download the default voice:

```bash
mkdir -p ~/.claude-tts/voices/en_US-lessac-medium
cd ~/.claude-tts/voices/en_US-lessac-medium
curl -LO https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-en_US-lessac-medium.tar.bz2
tar -xjf vits-piper-en_US-lessac-medium.tar.bz2 --strip-components=1
rm vits-piper-en_US-lessac-medium.tar.bz2
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

## Project Structure

```
src/claude_tts_mcp/
├── server.py           # MCP server (thin client)
├── service.py          # Background service with HTTP API + Web UI
├── cli.py              # CLI commands (speakup)
├── queue_manager.py    # Message queue and playback coordination
├── history.py          # SQLite history storage
├── streaming_player.py # Streaming audio playback
├── sherpa_engine.py    # sherpa-onnx TTS wrapper
├── tone_mapper.py      # Tone → synthesis parameters
└── voice_manager.py    # Voice model management
```

## Requirements

- Python 3.10+
- macOS (Linux/Windows support planned)
- Audio output device

## License

MIT
