#!/bin/bash
# Run the Planly server

echo "🚀 Starting Planly Server..."
echo ""

# Navigate to server directory
cd "$(dirname "$0")/server" || exit 1

# Check if virtual environment exists
if [ ! -d "../venv" ]; then
    echo "❌ Virtual environment not found. Please run:"
    echo "   python -m venv venv"
    echo "   venv/bin/pip install -r server/requirements.txt"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Using minimal config..."
    cp .env.local .env 2>/dev/null || cp .env.example .env
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Warning: Ollama doesn't seem to be running"
    echo "   Start it with: ollama serve"
    echo "   Or install from: https://ollama.com"
    echo ""
fi

# Run the server
echo "Starting server..."
exec ../venv/bin/python main.py
