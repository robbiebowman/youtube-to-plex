#!/bin/bash

echo "🚀 YouTube to Plex Downloader - Running Validation"
echo "=================================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Please run: python3 setup.py first"
    exit 1
fi

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment is activated: $VIRTUAL_ENV"
else
    echo "⚠️  Virtual environment not activated. Activating now..."
    source venv/bin/activate
fi

# Install dependencies if needed
echo "📦 Installing/updating dependencies..."
pip install -r requirements.txt

echo ""
echo "🔍 Running validation script..."
echo "=============================="
python validate_setup.py

echo ""
echo "✨ Validation complete!"