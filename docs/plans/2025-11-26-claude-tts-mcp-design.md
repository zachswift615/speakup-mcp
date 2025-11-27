# Claude TTS MCP Server Design

**Date:** 2025-11-26
**Status:** Approved
**Project:** claude-tts-mcp

## Overview

An MCP server that gives Claude Code text-to-speech capabilities using sherpa-onnx with Piper voices. Enables ambient notifications, conversational interaction, and accessibility support.

## Requirements

| Requirement | Decision |
|-------------|----------|
| Primary use case | Multi-purpose: ambient notifications, conversation, accessibility |
| Expression control | Utterance-level tones (word-level deferred to future version) |
| Platform | Python with sherpa-onnx |
| Voice source | Standalone (downloads own Piper voices) |
| Audio output | MCP server plays directly via sounddevice |
| Interruption | Essential - must support immediate stop |
| Default voice | `en_US-hfc_male-medium` |

## MCP Tools Interface

### `speak` - Synthesize and play text

```json
{
  "name": "speak",
  "description": "Speak text aloud with optional emotional tone",
  "inputSchema": {
    "type": "object",
    "properties": {
      "text": {
        "type": "string",
        "description": "Text to speak"
      },
      "tone": {
        "type": "string",
        "enum": ["neutral", "excited", "concerned", "calm", "urgent"],
        "default": "neutral",
        "description": "Emotional tone affecting voice variation and pacing"
      },
      "speed": {
        "type": "number",
        "minimum": 0.5,
        "maximum": 2.0,
        "default": 1.0,
        "description": "Speech rate multiplier"
      },
      "interrupt": {
        "type": "boolean",
        "default": true,
        "description": "If true, stops any current speech before starting"
      }
    },
    "required": ["text"]
  }
}
```

### `stop` - Interrupt current speech

```json
{
  "name": "stop",
  "description": "Stop any currently playing speech immediately"
}
```

### Usage Examples

```python
# Simple notification
speak(text="Build complete!")

# Excited success message
speak(text="All 47 tests passed!", tone="excited")

# Warning about an issue
speak(text="I found 3 security vulnerabilities in the dependencies", tone="concerned")

# Urgent interrupt
speak(text="Stopping! Critical error detected", tone="urgent", interrupt=True)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Server (Python)                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  MCP Layer  │───▶│ ToneMapper   │───▶│ SherpaEngine  │  │
│  │  (FastMCP)  │    │              │    │               │  │
│  └─────────────┘    │ tone → params│    │ sherpa-onnx   │  │
│        │            └──────────────┘    │ synthesis     │  │
│        │                                └───────┬───────┘  │
│        │            ┌──────────────┐            │          │
│        └───────────▶│ AudioPlayer  │◀───────────┘          │
│         (stop)      │              │    (audio samples)    │
│                     │ sounddevice  │                       │
│                     │ async play   │                       │
│                     └──────────────┘                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Components

1. **MCP Layer** - Uses `fastmcp` library for MCP protocol handling. Receives tool calls, returns results.

2. **ToneMapper** - Converts semantic tones to sherpa-onnx parameters:

   | Tone | noise_scale | noise_scale_w | length_scale | Description |
   |------|-------------|---------------|--------------|-------------|
   | neutral | 0.667 | 0.8 | 1.0 | Default, clear |
   | excited | 0.8 | 0.9 | 0.9 | More variation, slightly faster |
   | concerned | 0.5 | 0.6 | 1.1 | Less variation, slower |
   | calm | 0.4 | 0.5 | 1.15 | Steady, relaxed |
   | urgent | 0.7 | 0.85 | 0.85 | Punchy, fast |

3. **SherpaEngine** - Wraps `sherpa-onnx` Python bindings. Loads Piper model once at startup, synthesizes on demand.

4. **AudioPlayer** - Uses `sounddevice` for non-blocking audio playback. Maintains reference to current stream for interrupt support.

### Key Design Decisions

- Single-threaded synthesis (sherpa-onnx isn't thread-safe)
- Async audio playback (non-blocking, interruptible)
- Model loaded once at startup (avoid 1-2s load per utterance)

## Voice Management & Setup

### Voice Storage

```
~/.claude-tts/
├── voices/
│   └── en_US-hfc_male-medium/
│       ├── en_US-hfc_male-medium.onnx
│       └── tokens.txt
├── espeak-ng-data/          # Required for Piper phonemization
└── config.json              # Default voice, custom presets
```

### First-Run Setup

On first launch, the server:
1. Creates `~/.claude-tts/` directory
2. Downloads default voice `en_US-hfc_male-medium` (~60MB)
3. Downloads `espeak-ng-data` (~15MB)
4. Creates default `config.json`

### Config File

```json
{
  "default_voice": "en_US-hfc_male-medium",
  "custom_presets": {},
  "volume": 1.0
}
```

### Installation

```bash
# Install as a uvx tool (recommended)
uvx install claude-tts-mcp

# Or pip
pip install claude-tts-mcp
```

### Claude Code Configuration

```json
// ~/.claude/settings.json
{
  "mcpServers": {
    "tts": {
      "command": "uvx",
      "args": ["claude-tts-mcp"]
    }
  }
}
```

## Error Handling

### Interrupt Behavior

```python
class AudioPlayer:
    def __init__(self):
        self._current_stream = None
        self._lock = threading.Lock()

    def play(self, samples: np.ndarray, sample_rate: int):
        with self._lock:
            if self._current_stream:
                self._current_stream.stop()
            self._current_stream = sd.OutputStream(...)
            self._current_stream.start()

    def stop(self):
        with self._lock:
            if self._current_stream:
                self._current_stream.stop()
                self._current_stream = None
```

### Error Cases

| Situation | Behavior |
|-----------|----------|
| Empty text | Return success, no audio |
| Voice model missing | Auto-download on first use, or clear error message |
| Audio device unavailable | Return error: "No audio output device found" |
| Text too long (>10K chars) | Truncate with warning in response |
| Synthesis fails | Return error with details, don't crash server |

### Response Format

```python
# Success
{"success": True, "duration_ms": 2340}

# Error
{"success": False, "error": "No audio output device available"}
```

### Graceful Degradation

- If `sounddevice` can't find an output device, the server still starts but returns errors on `speak()`
- Model download failures show clear instructions for manual download

## Project Structure

```
claude-tts-mcp/
├── pyproject.toml
├── README.md
├── src/
│   └── claude_tts_mcp/
│       ├── __init__.py
│       ├── server.py          # MCP server entry point
│       ├── tone_mapper.py     # Tone → parameter mapping
│       ├── sherpa_engine.py   # sherpa-onnx wrapper
│       ├── audio_player.py    # sounddevice playback
│       └── voice_manager.py   # Download & manage voices
└── tests/
    ├── test_tone_mapper.py
    ├── test_sherpa_engine.py
    └── test_audio_player.py
```

## Dependencies

```toml
[project]
name = "claude-tts-mcp"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "fastmcp>=0.1.0",        # MCP protocol handling
    "sherpa-onnx>=1.10.0",   # TTS engine
    "sounddevice>=0.4.6",    # Audio playback
    "numpy>=1.24.0",         # Audio array handling
    "httpx>=0.25.0",         # Voice downloads
]

[project.scripts]
claude-tts-mcp = "claude_tts_mcp.server:main"
```

### Notes

1. **sherpa-onnx** - Pre-built wheels available for macOS (arm64, x86_64), Linux, Windows
2. **sounddevice** - Requires PortAudio (auto-bundled on macOS/Windows, `apt install libportaudio2` on Linux)
3. **fastmcp** - Lightweight MCP server library, handles stdio transport

## Future Enhancements (v2+)

- Word-level emphasis via segment-based synthesis
- Multiple voice support with `list_voices()` and `set_voice()`
- Custom tone presets in config
- Audio file output mode (return path instead of play)
- Queue mode for batching utterances
