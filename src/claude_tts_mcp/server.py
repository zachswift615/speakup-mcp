"""MCP Server for Claude TTS - speak and stop tools."""

from typing import Optional
from fastmcp import FastMCP

from .tone_mapper import ToneMapper
from .audio_player import AudioPlayer
from .sherpa_engine import SherpaEngine
from .voice_manager import VoiceManager

# Global instances (initialized lazily)
_voice_manager: Optional[VoiceManager] = None
_engine: Optional[SherpaEngine] = None
_player: Optional[AudioPlayer] = None
_tone_mapper: Optional[ToneMapper] = None


def _init_globals():
    """Initialize global instances if not already done."""
    global _voice_manager, _engine, _player, _tone_mapper

    if _tone_mapper is None:
        _tone_mapper = ToneMapper()

    if _player is None:
        _player = AudioPlayer()

    if _voice_manager is None:
        _voice_manager = VoiceManager()

    if _engine is None and _voice_manager is not None:
        voice_name = _voice_manager.default_voice
        if _voice_manager.is_voice_available(voice_name):
            paths = _voice_manager.get_voice_paths(voice_name)
            if paths:
                _engine = SherpaEngine(
                    model_path=str(paths["model"]),
                    tokens_path=str(paths["tokens"]),
                    data_dir=str(paths["data_dir"]),
                )


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
        Dict with success status and duration_ms
    """
    global _engine, _player, _tone_mapper

    # Handle empty text
    if not text.strip():
        return {"success": True, "duration_ms": 0}

    # Check engine is loaded
    if _engine is None or not _engine.is_loaded:
        return {"success": False, "error": "TTS engine not loaded. Voice may not be installed."}

    # Stop current playback if requested
    if interrupt and _player is not None and _player.is_playing():
        _player.stop()

    # Get tone parameters
    params = _tone_mapper.get_params(tone, speed=speed)

    # Synthesize audio
    samples, sample_rate = _engine.synthesize(text, params)

    # Play audio
    duration_ms = _player.play(samples, sample_rate, interrupt=False)

    return {"success": True, "duration_ms": duration_ms}


def stop() -> dict:
    """Stop any currently playing speech.

    Returns:
        Dict with success status
    """
    global _player

    if _player is not None:
        _player.stop()

    return {"success": True}


def create_server() -> FastMCP:
    """Create and configure the MCP server.

    Returns:
        Configured FastMCP server instance
    """
    _init_globals()

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
