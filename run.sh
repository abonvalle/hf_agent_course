#!/bin/bash
# Run script for Final Assignment Template using uv

set -e

echo "🔄 Starting Final Assignment Template..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found."
    echo "   Copy .env.example to .env and fill in your API keys."
    echo ""
fi

# Check if virtual environment exists
if [ ! -d .venv ]; then
    echo "📦 Virtual environment not found. Setting up dependencies..."
    uv sync
fi

# Run the application
echo "🚀 Running the application..."
uv run python app.py
