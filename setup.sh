#!/bin/bash
set -e

echo ""
echo "🎙️  Speech Coach — Setup"
echo "=========================="

# Check macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "❌ Speech Coach requires macOS (Apple Silicon)"
    exit 1
fi

# Check Homebrew
if ! command -v brew &>/dev/null; then
    echo "❌ Homebrew not found. Install it first: https://brew.sh"
    exit 1
fi

# Install Ollama
if command -v ollama &>/dev/null; then
    echo "✅ Ollama already installed"
else
    echo "📦 Installing Ollama..."
    brew install ollama
fi

# Pull Phi3 Mini
echo ""
echo "📥 Pulling Phi3 Mini model (~2GB)..."
echo "   This may take a few minutes depending on your connection."
echo ""
ollama pull phi3:mini

# Create SpeechCoach directory
INSTALL_DIR="$HOME/SpeechCoach"
mkdir -p "$INSTALL_DIR/reports"
echo ""
echo "📁 Created $INSTALL_DIR"

# Copy scripts
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/coach.py" "$INSTALL_DIR/coach.py"
cp "$SCRIPT_DIR/progress.py" "$INSTALL_DIR/progress.py"
echo "✅ Copied coach.py and progress.py"

# Create virtualenv
echo ""
echo "🐍 Creating Python virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --quiet --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install --quiet requests

echo ""
echo "=========================="
echo "✅ Setup complete!"
echo ""
echo "To start Speech Coach:"
echo ""
echo "  Terminal 1:  ollama serve"
echo "  Terminal 2:  source ~/SpeechCoach/venv/bin/activate"
echo "               python3 ~/SpeechCoach/coach.py"
echo ""
echo "Make sure Muesli is running, then speak. Type 'done' for your report."
echo ""
