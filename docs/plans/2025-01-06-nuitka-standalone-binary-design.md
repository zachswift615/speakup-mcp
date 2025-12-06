# Nuitka Standalone Binary Design

## Overview

Create standalone single-file distributions of SpeakUp that require no Python installation. Users download, extract (or install DMG), and run.

**Target Size:** ~140MB (includes Python runtime, all dependencies, default voice)

## Platform Strategy

| Platform | Format | Distribution |
|----------|--------|--------------|
| macOS arm64 | Signed/notarized .app in DMG | Primary |
| macOS x64 | Signed/notarized .app in DMG | Secondary |
| Linux x64 | tar.gz with standalone directory | Secondary |

## Why Nuitka (Not PyOxidizer)

- PyOxidizer abandoned (March 2024), only supports Python 3.8-3.10
- Nuitka actively maintained, supports Python 3.13
- Compiles Python to C, then native binary (faster startup)
- `--standalone` mode bundles all dependencies

## Build Architecture

### Nuitka Output
```
build/speakup.dist/
├── speakup                    # Main binary
├── libpython3.13.dylib        # Python runtime
├── sherpa_onnx/               # Native TTS libs
├── numpy/                     # Compiled extensions
└── ... other .so/.dylib files
```

### macOS App Bundle
```
SpeakUp.app/Contents/
├── Info.plist
├── PkgInfo
├── MacOS/
│   └── speakup               # Main binary (moved from dist)
├── Frameworks/               # All Nuitka libs
│   ├── libpython3.13.dylib
│   └── ...
└── Resources/
    └── voices/               # Bundled default voice
        ├── en_US-lessac-medium.onnx
        ├── tokens.txt
        └── espeak-ng-data/
```

### Linux Distribution
```
speakup-linux-x64.tar.gz
└── speakup/
    ├── speakup              # Main binary
    ├── lib/                 # Native libs
    └── voices/              # Bundled voice
```

## CI/CD Pipeline

### Workflow Trigger
```yaml
on:
  push:
    tags: ['v*']
  workflow_dispatch:
```

### Job Structure

```
┌─────────────────────────────────────────────────────────────┐
│  build-macos-arm64 (macos-14)                               │
│    ├── Install Python 3.13 + Nuitka                         │
│    ├── Download voice files                                  │
│    ├── nuitka --standalone --macos-create-app-bundle        │
│    ├── Create .app bundle with voices                        │
│    ├── Sign with Developer ID                                │
│    ├── Notarize with Apple                                   │
│    ├── Create DMG                                            │
│    └── Upload artifact                                       │
├─────────────────────────────────────────────────────────────┤
│  build-macos-x64 (macos-13)                                 │
│    └── Same as above, Intel runner                          │
├─────────────────────────────────────────────────────────────┤
│  build-linux-x64 (ubuntu-22.04)                             │
│    ├── Install Python 3.13 + Nuitka                         │
│    ├── Download voice files                                  │
│    ├── nuitka --standalone                                   │
│    ├── Package as tar.gz                                     │
│    └── Upload artifact                                       │
├─────────────────────────────────────────────────────────────┤
│  release (needs: all builds)                                │
│    ├── Download all artifacts                                │
│    └── Create GitHub Release with all binaries              │
└─────────────────────────────────────────────────────────────┘
```

### Secrets (Reused from speak2 repo)
- `APPLE_DEVELOPER_ID_APPLICATION_P12` - Base64-encoded signing certificate
- `APPLE_DEVELOPER_ID_APPLICATION_PASSWORD` - P12 password
- `APPLE_SIGNING_IDENTITY` - Signing identity string
- `APPLE_ID` - Apple ID for notarization
- `APPLE_ID_PASSWORD` - App-specific password
- `APPLE_TEAM_ID` - Apple Team ID

## Code Changes

### Resource Detection (voice_manager.py)
```python
def get_voice_directory() -> Path:
    """Find voice files - bundled or user-installed."""

    # Check 1: Running from macOS .app bundle?
    if sys.platform == "darwin":
        app_resources = Path(sys.executable).parent.parent / "Resources" / "voices"
        if app_resources.exists():
            return app_resources

    # Check 2: Running from Nuitka standalone (Linux)?
    exe_dir = Path(sys.executable).parent
    standalone_voices = exe_dir / "voices"
    if standalone_voices.exists():
        return standalone_voices

    # Check 3: Normal pip install - use ~/.speakup/voices
    return Path.home() / ".speakup" / "voices"
```

### Files to Modify
| File | Change |
|------|--------|
| `voice_manager.py` | Add `get_voice_directory()` with bundle detection |
| `sherpa_engine.py` | Use `get_voice_directory()` for model paths |
| `cli.py` | Add `--version` flag showing build type |

### Principle
- **Voice files** come from bundle (read-only)
- **User data** (history, config, queue) stays in `~/.speakup` (read-write)

## Install Script

### New Simplified Flow
```bash
#!/bin/bash
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "$ARCH" in
    x86_64)  ARCH="x64" ;;
    arm64|aarch64) ARCH="arm64" ;;
esac

RELEASE_URL="https://github.com/zachswift615/speakup-mcp/releases/latest/download"

if [ "$OS" = "darwin" ]; then
    # macOS: Download DMG, mount, copy to /Applications
    curl -L "$RELEASE_URL/SpeakUp-macos-$ARCH.dmg" -o /tmp/SpeakUp.dmg
    hdiutil attach /tmp/SpeakUp.dmg -mountpoint /tmp/speakup-mount
    cp -R "/tmp/speakup-mount/SpeakUp.app" /Applications/
    hdiutil detach /tmp/speakup-mount
    ln -sf /Applications/SpeakUp.app/Contents/MacOS/speakup ~/.local/bin/speakup
else
    # Linux: Download tar.gz, extract to ~/.local
    curl -L "$RELEASE_URL/speakup-linux-$ARCH.tar.gz" | tar -xz -C ~/.local/
    ln -sf ~/.local/speakup/speakup ~/.local/bin/speakup
fi

echo "✓ SpeakUp installed! Run: speakup --help"
```

### Benefits Over Current Install
- No Python/venv required
- No git clone
- No pip install
- ~5 second install vs ~2 minutes

## File Structure

### New Files
```
ai_voice/
├── .github/workflows/
│   └── release.yml              # CI/CD pipeline
├── scripts/
│   ├── create-app-bundle.sh     # macOS .app bundling
│   ├── create-dmg.sh            # DMG creation
│   └── download-voices.sh       # Fetch voice files for build
├── macos/
│   ├── Info.plist               # App metadata
│   ├── speakup.entitlements     # Hardened runtime entitlements
│   └── speakup.icns             # App icon (optional)
└── nuitka.conf                  # Nuitka build configuration (optional)
```

### Modified Files
```
├── install.sh                   # Simplified binary installer
└── src/claude_tts_mcp/
    ├── voice_manager.py         # Bundle detection
    ├── sherpa_engine.py         # Use voice_manager paths
    └── cli.py                   # --version with build info
```

## Deliverables

| Artifact | Size | Platform |
|----------|------|----------|
| `SpeakUp-macos-arm64.dmg` | ~140MB | macOS Apple Silicon |
| `SpeakUp-macos-x64.dmg` | ~140MB | macOS Intel |
| `speakup-linux-x64.tar.gz` | ~140MB | Linux x64 |

## Estimated Build Times

| Platform | Time |
|----------|------|
| macOS (each arch) | 15-20 min (includes notarization) |
| Linux | 10-15 min |
| Total pipeline | ~25 min (parallel builds) |

## Future Enhancements

1. **Additional voices**: `speakup voices download <name>`
2. **Auto-update**: `speakup update`
3. **Linux arm64**: Add when GitHub runners available
4. **Windows**: Future consideration

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Nuitka fails with sherpa-onnx | Test locally first; fall back to PyInstaller |
| Binary too large (>200MB) | Offer "lite" version without bundled voice |
| Notarization issues | Use existing speak2 patterns that work |
| Build takes too long | Cache Nuitka compilation between runs |
