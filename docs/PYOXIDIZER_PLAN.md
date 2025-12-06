# PyOxidizer Standalone Binary Plan

## Goal

Create a truly standalone single binary for SpeakUp that includes:
- Python runtime
- All Python dependencies (sherpa-onnx, sounddevice, numpy, etc.)
- Native libraries (onnxruntime, portaudio)
- Default Piper voice (en_US-lessac-medium, ~60MB)
- espeak-ng-data (~15MB)

Users download one file, run it, done.

## Why PyOxidizer

- Embeds Python interpreter into a Rust binary
- Bundles all dependencies including native libs
- Produces truly standalone executables
- No Python installation required on target machine
- Good support for bundling data files

## Target Platforms

| Platform | Architecture | Priority |
|----------|--------------|----------|
| macOS | arm64 (Apple Silicon) | High |
| macOS | x86_64 (Intel) | Medium |
| Linux | x86_64 | Medium |
| Linux | arm64 | Low |
| Windows | x86_64 | Future |

## Estimated Binary Size

- Python runtime: ~15MB
- Dependencies: ~50MB (sherpa-onnx is large)
- Voice model: ~60MB
- espeak-ng-data: ~15MB
- **Total: ~140-150MB compressed**

## Implementation Steps

### Phase 1: PyOxidizer Setup (2-3 hours)

1. Install PyOxidizer
   ```bash
   cargo install pyoxidizer
   # or
   brew install pyoxidizer
   ```

2. Initialize PyOxidizer config
   ```bash
   cd speakup-mcp
   pyoxidizer init-config-file
   ```

3. Create `pyoxidizer.bzl` configuration:
   - Define Python distribution
   - Add package dependencies
   - Configure entry point (cli.py)
   - Set up resource bundling

### Phase 2: Bundle Native Dependencies (3-4 hours)

sherpa-onnx and sounddevice have native libraries that need special handling:

1. **sherpa-onnx**:
   - Includes ONNX Runtime
   - Has platform-specific .so/.dylib files
   - May need to use `pip download` to get wheels with native libs

2. **sounddevice**:
   - Depends on PortAudio
   - On macOS: uses system PortAudio or bundled
   - On Linux: needs libportaudio

3. **numpy**:
   - Has compiled extensions
   - Should work with PyOxidizer's wheel handling

### Phase 3: Bundle Voice Files (1-2 hours)

1. Download voice files during build:
   ```python
   # In build script
   voice_url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-en_US-lessac-medium.tar.bz2"
   espeak_url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/espeak-ng-data.tar.bz2"
   ```

2. Configure PyOxidizer to include as resources:
   ```python
   # In pyoxidizer.bzl
   exe.add_python_resources(exe.pip_install(["speakup-mcp"]))
   exe.add_filesystem_resources(
       prefix="voices",
       path="build/voices"
   )
   ```

3. Update code to find bundled voices:
   ```python
   # voice_manager.py - detect if running from bundle
   if getattr(sys, 'oxidized', False):
       # Running from PyOxidizer bundle
       voice_dir = Path(sys.executable).parent / "voices"
   else:
       # Normal installation
       voice_dir = Path.home() / ".claude-tts" / "voices"
   ```

### Phase 4: GitHub Actions CI (2-3 hours)

Create `.github/workflows/release.yml`:

```yaml
name: Build Release

on:
  push:
    tags: ['v*']
  workflow_dispatch:

jobs:
  build-macos-arm64:
    runs-on: macos-14  # Apple Silicon runner
    steps:
      - uses: actions/checkout@v4
      - uses: actions-rust-lang/setup-rust-toolchain@v1
      - name: Install PyOxidizer
        run: cargo install pyoxidizer
      - name: Download voice files
        run: ./scripts/download-voices.sh
      - name: Build binary
        run: pyoxidizer build --release
      - name: Package
        run: |
          cd build/*/release/install
          tar -czvf speakup-macos-arm64.tar.gz speakup
      - uses: actions/upload-artifact@v4
        with:
          name: speakup-macos-arm64
          path: build/*/release/install/speakup-macos-arm64.tar.gz

  build-macos-x64:
    runs-on: macos-13  # Intel runner
    # ... similar steps

  build-linux-x64:
    runs-on: ubuntu-latest
    # ... similar steps

  release:
    needs: [build-macos-arm64, build-macos-x64, build-linux-x64]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
      - uses: softprops/action-gh-release@v1
        with:
          files: |
            speakup-macos-arm64/speakup-macos-arm64.tar.gz
            speakup-macos-x64/speakup-macos-x64.tar.gz
            speakup-linux-x64/speakup-linux-x64.tar.gz
```

### Phase 5: Update Install Script (1 hour)

Update `install.sh` to detect platform and download pre-built binary:

```bash
# Detect platform
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

# Map architecture names
case "$ARCH" in
    x86_64) ARCH="x64" ;;
    aarch64|arm64) ARCH="arm64" ;;
esac

# Download binary
RELEASE_URL="https://github.com/zachswift615/speakup-mcp/releases/latest/download"
curl -L "$RELEASE_URL/speakup-$OS-$ARCH.tar.gz" | tar -xz -C ~/.local/bin/
```

## File Structure After Implementation

```
speakup-mcp/
├── pyoxidizer.bzl           # PyOxidizer config
├── scripts/
│   ├── download-voices.sh   # Download voices for bundling
│   └── setup.py             # Existing setup
├── .github/
│   └── workflows/
│       └── release.yml      # CI/CD for building releases
└── src/
    └── claude_tts_mcp/
        └── voice_manager.py # Updated to detect bundled mode
```

## Testing Plan

1. **Local build test**:
   ```bash
   pyoxidizer build
   ./build/*/debug/install/speakup --help
   ./build/*/debug/install/speakup service start
   ```

2. **Binary portability test**:
   - Copy binary to clean macOS VM
   - Run without any Python installed
   - Verify TTS works

3. **CI build verification**:
   - Trigger workflow manually
   - Download artifacts
   - Test on each platform

## Future Enhancements

1. **Voice selection at runtime**:
   ```bash
   speakup voices list           # List available voices
   speakup voices download amy   # Download from HuggingFace
   speakup config voice amy      # Set default voice
   ```

2. **Smaller binary option**:
   - Build without bundled voice
   - Download voice on first run
   - Trade-off: smaller download vs. works offline immediately

3. **Auto-update**:
   ```bash
   speakup update  # Check for and install updates
   ```

## Resources

- [PyOxidizer User Guide](https://pyoxidizer.readthedocs.io/)
- [PyOxidizer GitHub](https://github.com/indygreg/PyOxidizer)
- [sherpa-onnx Python wheels](https://github.com/k2-fsa/sherpa-onnx/releases)
- [Piper voices on HuggingFace](https://huggingface.co/rhasspy/piper-voices)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Native lib bundling fails | Fall back to PyInstaller |
| Binary too large (>200MB) | Offer "lite" version without voice |
| sherpa-onnx incompatible | Pin specific version, test thoroughly |
| CI runners don't have right arch | Use self-hosted runners if needed |

## Time Estimate

| Phase | Hours |
|-------|-------|
| PyOxidizer setup | 2-3 |
| Native dependencies | 3-4 |
| Voice bundling | 1-2 |
| GitHub Actions | 2-3 |
| Install script update | 1 |
| Testing | 2-3 |
| **Total** | **11-16 hours** |
