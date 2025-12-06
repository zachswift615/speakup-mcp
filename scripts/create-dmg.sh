#!/bin/bash
#
# Create DMG from signed app bundle
#
set -euo pipefail

APP_NAME="SpeakUp"
BUILD_DIR="${BUILD_DIR:-build}"
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"

# Get version from git tag or default
VERSION="${GITHUB_REF_NAME:-v1.0.0}"
VERSION="${VERSION#v}"  # Remove 'v' prefix if present

# Detect architecture
ARCH=$(uname -m)
case "$ARCH" in
    x86_64) ARCH_SUFFIX="x64" ;;
    arm64)  ARCH_SUFFIX="arm64" ;;
    *)      ARCH_SUFFIX="$ARCH" ;;
esac

DMG_NAME="$APP_NAME-macos-$ARCH_SUFFIX-v$VERSION.dmg"
DMG_PATH="$BUILD_DIR/$DMG_NAME"
VOLUME_NAME="$APP_NAME $VERSION"
DMG_TEMP="$BUILD_DIR/dmg_temp"

echo "Creating DMG..."
echo "  App bundle: $APP_BUNDLE"
echo "  DMG name: $DMG_NAME"
echo "  Volume name: $VOLUME_NAME"

# Verify app bundle exists
if [ ! -d "$APP_BUNDLE" ]; then
    echo "Error: App bundle not found at $APP_BUNDLE"
    exit 1
fi

# Clean up any previous temp directory
rm -rf "$DMG_TEMP"
mkdir -p "$DMG_TEMP"

# Copy app to temp directory
echo "  Copying app bundle..."
cp -R "$APP_BUNDLE" "$DMG_TEMP/"

# Create symlink to Applications
ln -s /Applications "$DMG_TEMP/Applications"

# Create README
cat > "$DMG_TEMP/README.txt" << 'README'
SpeakUp - Text-to-Speech for Claude Code

INSTALLATION:
  Drag SpeakUp.app to your Applications folder.

USAGE:
  From terminal:
    /Applications/SpeakUp.app/Contents/MacOS/speakup --help

  Or add to your PATH:
    ln -sf /Applications/SpeakUp.app/Contents/MacOS/speakup ~/.local/bin/speakup

For more information: https://github.com/zachswift615/speakup-mcp
README

# Create DMG
echo "  Creating DMG image..."
hdiutil create -volname "$VOLUME_NAME" \
    -srcfolder "$DMG_TEMP" \
    -ov -format UDZO \
    "$DMG_PATH"

# Clean up
rm -rf "$DMG_TEMP"

# Show result
DMG_SIZE=$(du -sh "$DMG_PATH" | cut -f1)
echo ""
echo "DMG created: $DMG_PATH ($DMG_SIZE)"
