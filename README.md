# SpeakUp MCP Server

An MCP server that gives Claude Code (or any other coding agent) text-to-speech capabilities using sherpa-onnx with Piper voices.

## Features

- **`speak`** tool - synthesize and play text with emotional tones
- **`stop`** tool - interrupt current speech
- **5 tones**: neutral, excited, concerned, calm, urgent
- **Interruptible** - new speech can stop current playback
- **Speed control** - 0.5x to 2.0x speech rate

## Quick Setup

```bash
# Install dependencies
pip install -e .

# Run the setup script to download voice files (~70MB)
python scripts/setup.py
```

## Manual Installation

```bash
# Install from source
pip install -e .

# Or install dev dependencies for testing
pip install -e ".[dev]"
```

## Voice Setup (Manual)

If you prefer manual setup, the server expects voices in `~/.claude-tts/voices/`.

### Download the default voice (en_US-lessac-medium)

```bash
mkdir -p ~/.claude-tts/voices/en_US-lessac-medium
cd ~/.claude-tts/voices/en_US-lessac-medium
curl -LO https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-en_US-lessac-medium.tar.bz2
tar -xjf vits-piper-en_US-lessac-medium.tar.bz2 --strip-components=1
rm vits-piper-en_US-lessac-medium.tar.bz2
```

## Claude Code Configuration

Add to `~/.claude/settings.json` or each project's `.mcp.json`:

```json
{
  "mcpServers": {
    "tts": {
      "command": "python",
      "args": ["-m", "claude_tts_mcp.server"]
    }
  }
}
```

Or if using uvx:

```json
{
  "mcpServers": {
    "tts": {
      "command": "uvx",
      "args": ["--from", "/path/to/ai_voice", "claude-tts-mcp"]
    }
  }
}
```

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

# Stop current speech
stop()
```

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

### Token Efficient

The MCP interface is designed to be minimal:
- **Tool definitions**: ~60 words total for both tools
- **Responses**: `{"success": true, "duration_ms": 1234}` (~40 characters)

No verbose payloads, no unnecessary metadata - just the essentials.

### Subagent Visibility

When using subagent-driven development, you typically have limited visibility into what agents are doing. With TTS instructions in your CLAUDE.md, subagents announce their progress as they work - giving you real-time audio feedback on task execution without needing to watch the terminal.

### Streaming Playback

Audio begins playing immediately as it's synthesized, rather than waiting for full generation. This reduces time-to-first-sound significantly for longer text.

### Tones

| Tone | Effect |
|------|--------|
| `neutral` | Default, clear speech |
| `excited` | More variation, slightly faster |
| `concerned` | Steadier, slower |
| `calm` | Very steady, relaxed pace |
| `urgent` | Energetic, fast |

## Development

```bash
# Run tests
pytest tests/ -v

# Run specific test file
pytest tests/test_tone_mapper.py -v
```

## Project Structure

```
src/claude_tts_mcp/
├── server.py           # MCP server entry point
├── tone_mapper.py      # Tone → parameter mapping
├── sherpa_engine.py    # sherpa-onnx wrapper
├── streaming_player.py # Streaming audio playback
└── voice_manager.py    # Voice path management
```

## Requirements

- Python 3.10+
- macOS, Linux, or Windows
- Audio output device

## License

MIT
