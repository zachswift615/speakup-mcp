#!/bin/bash
#
# Create macOS .app bundle from Nuitka standalone output
#
set -euo pipefail

APP_NAME="SpeakUp"
BUILD_DIR="${BUILD_DIR:-build}"
NUITKA_DIST="$BUILD_DIR/speakup.dist"
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"
CONTENTS="$APP_BUNDLE/Contents"
MACOS="$CONTENTS/MacOS"
FRAMEWORKS="$CONTENTS/Frameworks"
RESOURCES="$CONTENTS/Resources"
VOICES_DIR="${VOICES_DIR:-build/voices}"

echo "Creating macOS app bundle..."
echo "  Nuitka output: $NUITKA_DIST"
echo "  App bundle: $APP_BUNDLE"

# Verify Nuitka output exists
if [ ! -d "$NUITKA_DIST" ]; then
    echo "Error: Nuitka dist directory not found at $NUITKA_DIST"
    echo "Run 'nuitka --standalone' first"
    exit 1
fi

# Clean and create app bundle structure
rm -rf "$APP_BUNDLE"
mkdir -p "$MACOS" "$FRAMEWORKS" "$RESOURCES/voices"

# Copy main binary to MacOS
echo "  Copying main binary..."
cp "$NUITKA_DIST/speakup" "$MACOS/speakup"

# Copy all libraries to Frameworks
echo "  Copying frameworks and libraries..."
find "$NUITKA_DIST" -type f \( -name "*.dylib" -o -name "*.so" \) -exec cp {} "$FRAMEWORKS/" \;

# Copy Python packages (needed for imports)
echo "  Copying Python packages..."
for pkg in "$NUITKA_DIST"/*; do
    if [ -d "$pkg" ] && [ "$(basename "$pkg")" != "__pycache__" ]; then
        cp -R "$pkg" "$FRAMEWORKS/"
    fi
done

# Copy Info.plist
if [ -f "macos/Info.plist" ]; then
    cp "macos/Info.plist" "$CONTENTS/Info.plist"
else
    echo "Warning: macos/Info.plist not found, creating minimal version"
    cat > "$CONTENTS/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>speakup</string>
    <key>CFBundleIdentifier</key>
    <string>com.speakup.cli</string>
    <key>CFBundleName</key>
    <string>SpeakUp</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST
fi

# Create PkgInfo
echo -n "APPL????" > "$CONTENTS/PkgInfo"

# Copy voice files if they exist
if [ -d "$VOICES_DIR" ]; then
    echo "  Copying voice files..."
    cp -R "$VOICES_DIR"/* "$RESOURCES/voices/"
else
    echo "Warning: Voice directory not found at $VOICES_DIR"
    echo "  Run scripts/download-voices.sh first"
fi

# Copy icon if it exists
if [ -f "macos/speakup.icns" ]; then
    cp "macos/speakup.icns" "$RESOURCES/speakup.icns"
fi

# Update library paths to use @executable_path
echo "  Updating library paths..."
for lib in "$FRAMEWORKS"/*.dylib "$FRAMEWORKS"/*.so 2>/dev/null; do
    if [ -f "$lib" ]; then
        install_name_tool -add_rpath "@executable_path/../Frameworks" "$MACOS/speakup" 2>/dev/null || true
    fi
done

# Show bundle size
echo ""
BUNDLE_SIZE=$(du -sh "$APP_BUNDLE" | cut -f1)
echo "App bundle created: $APP_BUNDLE ($BUNDLE_SIZE)"
