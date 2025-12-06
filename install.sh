#!/bin/bash
#
# SpeakUp MCP Server - One-line installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/zachswift615/speakup-mcp/main/install.sh | bash
#
# Options:
#   --source    Force source installation (skip binary download)
#
# The installer will:
#   1. Try to download pre-built binary (fast, ~140MB, no Python needed)
#   2. Fall back to source installation if binary not available
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SPEAKUP_HOME="${SPEAKUP_HOME:-$HOME/.speakup}"
BIN_DIR="$HOME/.local/bin"
REPO_URL="https://github.com/zachswift615/speakup-mcp"
RELEASE_URL="$REPO_URL/releases/latest/download"

# Parse arguments
FORCE_SOURCE=false
for arg in "$@"; do
    case $arg in
        --source) FORCE_SOURCE=true ;;
    esac
done

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║              SpeakUp MCP Server Installer                 ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Detect OS and architecture
detect_platform() {
    OS="$(uname -s)"
    ARCH="$(uname -m)"

    case "$OS" in
        Darwin) OS="macos" ;;
        Linux)  OS="linux" ;;
        *)      echo -e "${RED}Unsupported OS: $OS${NC}"; exit 1 ;;
    esac

    case "$ARCH" in
        x86_64)       ARCH="x64" ;;
        arm64|aarch64) ARCH="arm64" ;;
        *)            echo -e "${RED}Unsupported architecture: $ARCH${NC}"; exit 1 ;;
    esac

    echo -e "${BLUE}►${NC} Detected: $OS $ARCH"
}

# Check/create bin directory and PATH
setup_path() {
    mkdir -p "$BIN_DIR"

    # Check if already in PATH
    if [[ ":$PATH:" == *":$BIN_DIR:"* ]]; then
        return 0
    fi

    # Detect shell config file
    SHELL_NAME=$(basename "$SHELL")
    case "$SHELL_NAME" in
        bash)
            if [ -f "$HOME/.bash_profile" ]; then
                SHELL_RC="$HOME/.bash_profile"
            else
                SHELL_RC="$HOME/.bashrc"
            fi
            ;;
        zsh)  SHELL_RC="$HOME/.zshrc" ;;
        fish) SHELL_RC="$HOME/.config/fish/config.fish" ;;
        *)    SHELL_RC="$HOME/.profile" ;;
    esac

    # Add to PATH in shell config
    echo -e "${YELLOW}►${NC} Adding $BIN_DIR to PATH in $SHELL_RC"

    if [ "$SHELL_NAME" = "fish" ]; then
        echo "set -gx PATH \"$BIN_DIR\" \$PATH" >> "$SHELL_RC"
    else
        echo "" >> "$SHELL_RC"
        echo "# SpeakUp MCP Server" >> "$SHELL_RC"
        echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$SHELL_RC"
    fi

    export PATH="$BIN_DIR:$PATH"
    echo -e "${GREEN}✓${NC} Added to PATH"
}

# Try binary installation
try_binary_install() {
    if [ "$FORCE_SOURCE" = true ]; then
        return 1
    fi

    echo -e "${YELLOW}►${NC} Checking for pre-built binary..."

    if [ "$OS" = "macos" ]; then
        DMG_NAME="SpeakUp-macos-${ARCH}.dmg"
        DMG_URL="$RELEASE_URL/$DMG_NAME"

        # Check if release exists
        if ! curl -fsSL --head "$DMG_URL" >/dev/null 2>&1; then
            echo -e "${YELLOW}  No pre-built binary available for $OS $ARCH${NC}"
            return 1
        fi

        echo -e "${YELLOW}►${NC} Downloading $DMG_NAME (~140MB)..."
        TMP_DMG="/tmp/SpeakUp.dmg"
        curl -fL --progress-bar "$DMG_URL" -o "$TMP_DMG"

        echo -e "${YELLOW}►${NC} Installing to /Applications..."
        # Mount DMG
        MOUNT_POINT="/tmp/speakup-mount"
        hdiutil attach "$TMP_DMG" -mountpoint "$MOUNT_POINT" -quiet

        # Remove old installation if exists
        [ -d "/Applications/SpeakUp.app" ] && rm -rf "/Applications/SpeakUp.app"

        # Copy app
        cp -R "$MOUNT_POINT/SpeakUp.app" /Applications/

        # Unmount and cleanup
        hdiutil detach "$MOUNT_POINT" -quiet
        rm -f "$TMP_DMG"

        # Create CLI symlink
        ln -sf /Applications/SpeakUp.app/Contents/MacOS/speakup "$BIN_DIR/speakup"

        echo -e "${GREEN}✓${NC} Installed SpeakUp.app to /Applications"
        return 0

    else
        # Linux
        TARBALL_NAME="speakup-linux-${ARCH}.tar.gz"
        TARBALL_URL="$RELEASE_URL/$TARBALL_NAME"

        # Check if release exists
        if ! curl -fsSL --head "$TARBALL_URL" >/dev/null 2>&1; then
            echo -e "${YELLOW}  No pre-built binary available for $OS $ARCH${NC}"
            return 1
        fi

        echo -e "${YELLOW}►${NC} Downloading $TARBALL_NAME (~140MB)..."

        # Create installation directory
        mkdir -p "$SPEAKUP_HOME"

        # Download and extract
        curl -fL --progress-bar "$TARBALL_URL" | tar -xz -C "$SPEAKUP_HOME"

        # Create CLI symlink
        ln -sf "$SPEAKUP_HOME/speakup/speakup" "$BIN_DIR/speakup"

        echo -e "${GREEN}✓${NC} Installed to $SPEAKUP_HOME/speakup"
        return 0
    fi
}

# Source installation (fallback)
source_install() {
    echo -e "${YELLOW}►${NC} Installing from source..."

    INSTALL_DIR="$SPEAKUP_HOME/src"

    # Check for Python 3.10+
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}✗${NC} Python 3.10+ required but not found"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
        echo -e "${RED}✗${NC} Python 3.10+ required (found $PYTHON_VERSION)"
        exit 1
    fi

    echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"

    # Clone or update repository
    mkdir -p "$SPEAKUP_HOME"

    if [ -d "$INSTALL_DIR/.git" ]; then
        echo -e "${YELLOW}►${NC} Updating existing installation..."
        cd "$INSTALL_DIR"
        git pull --quiet
    else
        [ -d "$INSTALL_DIR" ] && rm -rf "$INSTALL_DIR"
        echo -e "${YELLOW}►${NC} Cloning repository..."
        git clone --quiet "$REPO_URL.git" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi

    # Create virtualenv and install
    echo -e "${YELLOW}►${NC} Creating virtual environment..."
    [ -d "$INSTALL_DIR/venv" ] && rm -rf "$INSTALL_DIR/venv"
    python3 -m venv "$INSTALL_DIR/venv"
    source "$INSTALL_DIR/venv/bin/activate"

    echo -e "${YELLOW}►${NC} Installing dependencies..."
    pip install --quiet --upgrade pip
    pip install --quiet -e "$INSTALL_DIR"

    # Download voice files
    echo -e "${YELLOW}►${NC} Downloading voice files (~70MB)..."
    python3 "$INSTALL_DIR/scripts/setup.py" 2>&1 | grep -E "(Downloading|Progress|installed|already)" || true

    # Create CLI wrapper
    cat > "$BIN_DIR/speakup" << EOF
#!/bin/bash
source "$INSTALL_DIR/venv/bin/activate"
exec python -m claude_tts_mcp.cli "\$@"
EOF
    chmod +x "$BIN_DIR/speakup"

    echo -e "${GREEN}✓${NC} Source installation complete"
}

# Start the service
start_service() {
    echo -e "${YELLOW}►${NC} Starting SpeakUp service..."

    # Stop existing service if running
    "$BIN_DIR/speakup" service stop &>/dev/null || true

    "$BIN_DIR/speakup" service start
}

# Print success message
print_success() {
    echo ""
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                  Installation Complete!                   ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
    echo "SpeakUp is now running! Web UI: http://localhost:7849"
    echo ""
    echo -e "${BLUE}Quick Start:${NC}"
    echo "  cd your-project"
    echo "  speakup init my-project-name"
    echo ""
    echo -e "${BLUE}CLI Commands:${NC}"
    echo "  speakup --version      # Show version and build info"
    echo "  speakup init <name>    # Set up TTS in a project"
    echo "  speakup status         # Show queue status"
    echo "  speakup stop           # Stop playback"
    echo "  speakup history        # Show message history"
    echo "  speakup service start  # Start background service"
    echo "  speakup service stop   # Stop background service"
    echo ""
    echo -e "${YELLOW}Note:${NC} Restart your terminal or run:"
    echo "  source ~/.zshrc  # or ~/.bashrc"
    echo ""
}

# Main installation flow
main() {
    detect_platform
    setup_path

    # Try binary first, fall back to source
    if try_binary_install; then
        echo -e "${GREEN}✓${NC} Binary installation successful"
    else
        echo -e "${YELLOW}►${NC} Falling back to source installation..."
        source_install
    fi

    start_service
    print_success
}

main "$@"
