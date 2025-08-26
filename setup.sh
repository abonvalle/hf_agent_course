#!/bin/bash
# Setup script for Final Assignment Template using uv

set -e  # Exit on any error

echo "🚀 Setting up Final Assignment Template with uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Installing uv..."
    
    # Detect OS and install uv accordingly
    if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "darwin"* ]]; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "On Windows, please install uv manually:"
        echo "powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\""
        exit 1
    else
        echo "Unsupported OS. Please install uv manually from https://docs.astral.sh/uv/"
        exit 1
    fi
    
    echo "✅ uv installed successfully!"
else
    echo "✅ uv is already installed"
fi

# Sync dependencies
echo "📦 Installing dependencies..."
uv sync

# Check setup
echo "🔍 Verifying installation..."
uv run python check_setup.py

echo ""
echo "🎉 Setup complete! You can now:"
echo "   • Run the app: uv run python app.py"
echo "   • Add dependencies: uv add package-name"
echo "   • See all commands: make help"
echo ""
echo "Don't forget to create a .env file with your API keys!"
