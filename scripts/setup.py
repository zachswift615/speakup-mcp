#!/usr/bin/env python3
"""Setup script for Claude TTS MCP Server.

Downloads the default Piper voice and espeak-ng-data.
"""

import os
import sys
import tarfile
import tempfile
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    os.system(f"{sys.executable} -m pip install httpx")
    import httpx


# Configuration
DATA_DIR = Path.home() / ".claude-tts"
VOICES_DIR = DATA_DIR / "voices"
ESPEAK_DIR = DATA_DIR / "espeak-ng-data"

# Using lessac-medium (male voice) from sherpa-onnx releases
# This is pre-packaged with tokens.txt for sherpa-onnx compatibility
DEFAULT_VOICE = "en_US-lessac-medium"
VOICE_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-en_US-lessac-medium.tar.bz2"
ESPEAK_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/espeak-ng-data.tar.bz2"


def download_file(url: str, dest_path: Path, description: str) -> bool:
    """Download a file with progress indication."""
    print(f"\nDownloading {description}...")
    print(f"  URL: {url}")

    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=300) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))

            with open(dest_path, "wb") as f:
                downloaded = 0
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = (downloaded / total) * 100
                        print(f"\r  Progress: {pct:.1f}% ({downloaded // 1024 // 1024}MB / {total // 1024 // 1024}MB)", end="")
                print()
        return True
    except Exception as e:
        print(f"\n  Error: {e}")
        return False


def extract_tar(archive_path: Path, dest_dir: Path, strip_components: int = 0):
    """Extract a tar archive."""
    print(f"  Extracting to {dest_dir}...")

    # Determine compression
    if str(archive_path).endswith(".tar.gz") or str(archive_path).endswith(".tgz"):
        mode = "r:gz"
    elif str(archive_path).endswith(".tar.bz2"):
        mode = "r:bz2"
    else:
        mode = "r"

    dest_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive_path, mode) as tar:
        for member in tar.getmembers():
            # Strip leading path components
            if strip_components > 0:
                parts = member.name.split("/")
                if len(parts) <= strip_components:
                    continue
                member.name = "/".join(parts[strip_components:])

            # Skip empty names
            if not member.name:
                continue

            tar.extract(member, dest_dir)

    print("  Done!")


def setup_voice():
    """Download and set up the default voice."""
    voice_dir = VOICES_DIR / DEFAULT_VOICE
    model_file = voice_dir / f"{DEFAULT_VOICE}.onnx"

    if model_file.exists():
        print(f"\nVoice '{DEFAULT_VOICE}' already installed at {voice_dir}")
        return True

    print(f"\nSetting up voice: {DEFAULT_VOICE}")
    voice_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".tar.bz2", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        if not download_file(VOICE_URL, tmp_path, f"voice {DEFAULT_VOICE}"):
            return False

        # sherpa-onnx archives extract to vits-piper-{voice}/ folder
        extract_tar(tmp_path, voice_dir, strip_components=1)

        # Verify installation
        if model_file.exists():
            print(f"  Voice installed successfully!")
            return True
        else:
            # Try alternative naming - might be just model.onnx
            alt_model = voice_dir / "model.onnx"
            if alt_model.exists():
                # Rename to expected name
                alt_model.rename(model_file)
                print(f"  Voice installed successfully!")
                return True
            print(f"  Error: Model file not found after extraction")
            print(f"  Looking for: {model_file}")
            print(f"  Contents: {list(voice_dir.iterdir())}")
            return False
    finally:
        tmp_path.unlink(missing_ok=True)


def setup_espeak():
    """Download and set up espeak-ng-data."""
    # Check if already installed
    if (ESPEAK_DIR / "phontab").exists():
        print(f"\nespeak-ng-data already installed at {ESPEAK_DIR}")
        return True

    print(f"\nSetting up espeak-ng-data")
    ESPEAK_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".tar.bz2", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        if not download_file(ESPEAK_URL, tmp_path, "espeak-ng-data"):
            return False

        extract_tar(tmp_path, ESPEAK_DIR, strip_components=1)

        # Verify installation
        if (ESPEAK_DIR / "phontab").exists():
            print(f"  espeak-ng-data installed successfully!")
            return True
        else:
            print(f"  Error: espeak-ng-data files not found after extraction")
            return False
    finally:
        tmp_path.unlink(missing_ok=True)


def print_claude_config():
    """Print the Claude Code configuration."""
    project_dir = Path(__file__).parent.parent.resolve()

    print("\n" + "=" * 60)
    print("SETUP COMPLETE!")
    print("=" * 60)
    print(f"\nData directory: {DATA_DIR}")
    print(f"Voice: {DEFAULT_VOICE}")
    print("\nTo use with Claude Code, add this to ~/.claude/settings.json:")
    print()
    print('{')
    print('  "mcpServers": {')
    print('    "tts": {')
    print(f'      "command": "{sys.executable}",')
    print(f'      "args": ["-m", "claude_tts_mcp.server"],')
    print(f'      "cwd": "{project_dir}"')
    print('    }')
    print('  }')
    print('}')
    print()
    print("Or run the server manually to test:")
    print(f"  cd {project_dir}")
    print(f"  {sys.executable} -m claude_tts_mcp.server")
    print()


def main():
    """Main setup routine."""
    print("=" * 60)
    print("Claude TTS MCP Server Setup")
    print("=" * 60)
    print(f"\nThis script will download:")
    print(f"  1. Piper voice: {DEFAULT_VOICE} (~60MB)")
    print(f"  2. espeak-ng-data (~15MB)")
    print(f"\nFiles will be installed to: {DATA_DIR}")

    # Create base directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Setup components
    voice_ok = setup_voice()
    espeak_ok = setup_espeak()

    if voice_ok and espeak_ok:
        print_claude_config()
        return 0
    else:
        print("\nSetup incomplete. Please check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
