#!/bin/bash
#
# SpeakUp MCP Server - One-line installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/zachswift615/speakup-mcp/main/install.sh | bash
#
# Or after cloning:
#   ./install.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="${SPEAKUP_INSTALL_DIR:-$HOME/.speakup}"
REPO_URL="https://github.com/zachswift615/speakup-mcp.git"
BIN_DIR="$HOME/.local/bin"

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║              SpeakUp MCP Server Installer                 ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Detect OS
OS="$(uname -s)"
case "$OS" in
    Darwin) OS="macos" ;;
    Linux)  OS="linux" ;;
    *)      echo -e "${RED}Unsupported OS: $OS${NC}"; exit 1 ;;
esac

echo -e "${BLUE}►${NC} Detected OS: $OS"

# Check for Python 3.10+
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
            echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"
            PYTHON_CMD="python3"
            return 0
        fi
    fi

    echo -e "${RED}✗${NC} Python 3.10+ required but not found"
    echo "  Install Python 3.10+ and try again"
    exit 1
}

# Check/create bin directory and PATH
setup_path() {
    mkdir -p "$BIN_DIR"

    # Check if already in PATH
    if [[ ":$PATH:" == *":$BIN_DIR:"* ]]; then
        echo -e "${GREEN}✓${NC} $BIN_DIR already in PATH"
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
    echo -e "${GREEN}✓${NC} Added to PATH (restart terminal or run: source $SHELL_RC)"
}

# Clone or update repository
setup_repo() {
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}►${NC} Updating existing installation..."
        cd "$INSTALL_DIR"
        git pull --quiet
    else
        echo -e "${YELLOW}►${NC} Cloning repository to $INSTALL_DIR..."
        git clone --quiet "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
    echo -e "${GREEN}✓${NC} Repository ready"
}

# Create virtualenv and install
setup_venv() {
    echo -e "${YELLOW}►${NC} Creating virtual environment..."

    if [ -d "$INSTALL_DIR/venv" ]; then
        rm -rf "$INSTALL_DIR/venv"
    fi

    $PYTHON_CMD -m venv "$INSTALL_DIR/venv"
    source "$INSTALL_DIR/venv/bin/activate"

    echo -e "${YELLOW}►${NC} Installing dependencies..."
    pip install --quiet --upgrade pip
    pip install --quiet -e "$INSTALL_DIR"

    echo -e "${GREEN}✓${NC} Dependencies installed"
}

# Download voice files
setup_voice() {
    echo -e "${YELLOW}►${NC} Downloading voice files (~70MB)..."
    $PYTHON_CMD "$INSTALL_DIR/scripts/setup.py" 2>&1 | grep -E "(Downloading|Progress|installed|already)"
    echo -e "${GREEN}✓${NC} Voice files ready"
}

# Create CLI symlinks
setup_cli() {
    echo -e "${YELLOW}►${NC} Setting up CLI commands..."

    # Create wrapper scripts that activate venv
    cat > "$BIN_DIR/speakup" << EOF
#!/bin/bash
source "$INSTALL_DIR/venv/bin/activate"
exec python -m claude_tts_mcp.cli "\$@"
EOF
    chmod +x "$BIN_DIR/speakup"

    cat > "$BIN_DIR/speakup-service" << EOF
#!/bin/bash
source "$INSTALL_DIR/venv/bin/activate"
exec python -m claude_tts_mcp.service "\$@"
EOF
    chmod +x "$BIN_DIR/speakup-service"

    echo -e "${GREEN}✓${NC} CLI commands installed: speakup, speakup-service"
}

# Start the service
start_service() {
    echo -e "${YELLOW}►${NC} Starting SpeakUp service..."
    source "$INSTALL_DIR/venv/bin/activate"

    # Stop existing service if running
    if "$BIN_DIR/speakup" service status &>/dev/null; then
        "$BIN_DIR/speakup" service stop &>/dev/null || true
    fi

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
    check_python
    setup_path
    setup_repo
    setup_venv
    setup_voice
    setup_cli
    start_service
    print_success
}

main "$@"
