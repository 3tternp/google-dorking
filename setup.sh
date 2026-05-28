#!/bin/bash

# Quick Setup Script for Google Dorking Tool
# This script automates the initial setup process

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════╗"
echo "║     Google Dorking Tool - Quick Setup Script           ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
echo "✓ Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "  Found Python $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "✓ Creating virtual environment..."
    python3 -m venv venv
    echo "  Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "✓ Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1

# Install dependencies
echo "✓ Installing dependencies..."
pip install -r requirements.txt > /dev/null 2>&1
echo "  Dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "✓ Creating .env configuration file..."
    cp .env.example .env
    echo "  .env file created - please review and update if needed"
else
    echo "✓ .env file already exists"
fi

# Check for Redis
echo "✓ Checking Redis installation..."
if command -v redis-cli &> /dev/null; then
    echo "  Redis found"
    if redis-cli ping > /dev/null 2>&1; then
        echo "  Redis is running ✓"
    else
        echo "  WARNING: Redis is not running"
        echo "  Start Redis with: redis-server"
    fi
else
    echo "  WARNING: Redis not found"
    echo "  Install Redis:"
    echo "    Ubuntu/Debian: sudo apt-get install redis-server"
    echo "    macOS: brew install redis"
    echo "    Docker: docker run -d -p 6379:6379 redis:latest"
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║            Setup Complete! ✓                           ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "1. Review and update .env if needed"
echo "2. Start Redis (if not already running)"
echo "3. In Terminal 1, run: python run.py"
echo "4. In Terminal 2, run: python worker.py"
echo "5. Open browser to: http://localhost:5000"
echo ""
echo "For detailed instructions, see README.md"
echo ""
