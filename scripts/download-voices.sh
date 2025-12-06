#!/bin/bash
#
# Download voice files for bundling into standalone binary
#
set -euo pipefail

BUILD_DIR="${BUILD_DIR:-build/voices}"
VOICE_NAME="en_US-lessac-medium"
VOICE_URL="https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-${VOICE_NAME}.tar.bz2"
ESPEAK_URL="https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/espeak-ng-data.tar.bz2"

echo "Downloading voice files for bundling..."
echo "  Build directory: $BUILD_DIR"

# Clean and create directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/$VOICE_NAME"
mkdir -p "$BUILD_DIR/espeak-ng-data"

# Download and extract voice
echo ""
echo "Downloading $VOICE_NAME voice (~60MB)..."
curl -L --progress-bar "$VOICE_URL" | tar -xjf - -C "$BUILD_DIR/$VOICE_NAME" --strip-components=1

# Download and extract espeak-ng-data
echo ""
echo "Downloading espeak-ng-data (~15MB)..."
curl -L --progress-bar "$ESPEAK_URL" | tar -xjf - -C "$BUILD_DIR/espeak-ng-data" --strip-components=1

# Verify downloads
echo ""
echo "Verifying downloads..."

if [ -f "$BUILD_DIR/$VOICE_NAME/$VOICE_NAME.onnx" ]; then
    echo "  ✓ Voice model: $VOICE_NAME.onnx"
else
    # Check for alternative naming
    if [ -f "$BUILD_DIR/$VOICE_NAME/model.onnx" ]; then
        mv "$BUILD_DIR/$VOICE_NAME/model.onnx" "$BUILD_DIR/$VOICE_NAME/$VOICE_NAME.onnx"
        echo "  ✓ Voice model: $VOICE_NAME.onnx (renamed)"
    else
        echo "  ✗ Voice model not found!"
        exit 1
    fi
fi

if [ -f "$BUILD_DIR/$VOICE_NAME/tokens.txt" ]; then
    echo "  ✓ Tokens file: tokens.txt"
else
    echo "  ✗ Tokens file not found!"
    exit 1
fi

if [ -f "$BUILD_DIR/espeak-ng-data/phontab" ]; then
    echo "  ✓ espeak-ng-data: phontab"
else
    echo "  ✗ espeak-ng-data not found!"
    exit 1
fi

# Show total size
echo ""
TOTAL_SIZE=$(du -sh "$BUILD_DIR" | cut -f1)
echo "Total voice data size: $TOTAL_SIZE"
echo "Voice files ready for bundling at: $BUILD_DIR"
