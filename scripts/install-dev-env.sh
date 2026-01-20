#!/usr/bin/env bash
# ==============================================================================
# QuickFile - Development Environment Setup Script (Bash)
#
# Description:
#   Sets up the Python virtual environment (.venv) for development.
#   Installs both production (requirements.txt) and development (requirements-dev.txt) dependencies.
#
# Usage:
#   ./scripts/install-dev-env.sh
#
# Project: QuickFile
# Author:  Dawid 'Dawciobiel' Biel
# Date:    2025-12-25
# Version: 1.0.0
# License: GNU General Public License v3.0
# CLA:     Contributers License Agreement (CLA.md)
#
# Copyright (c) 2025 Dawid Biel. All rights reserved.
# ==============================================================================

set -e  # Exit immediately if a command exits with a non-zero status

# Function to find the correct python command
find_python_command() {
    if command -v python3 &> /dev/null; then
        echo "python3"
    elif command -v python &> /dev/null; then
        echo "python"
    else
        echo "❌ Python is not installed or not in PATH." >&2
        exit 1
    fi
}

PYTHON_CMD=$(find_python_command)

echo "🔧 Setting up development virtual environment (.venv)..."

# Create the virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
  echo "📦 Creating a new virtual environment..."
  "$PYTHON_CMD" -m venv .venv
else
  echo "✅ Virtual environment already exists."
fi

# Activate the environment
source .venv/bin/activate

# Upgrade pip
echo " upgrading pip..."
pip install --upgrade pip

# Install production dependencies
if [ -f "requirements.txt" ]; then
    echo "📥 Installing production dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "⚠️ requirements.txt not found, skipping."
fi

# Install development dependencies
if [ -f "requirements-dev.txt" ]; then
    echo "📥 Installing development dependencies from requirements-dev.txt..."
    pip install -r requirements-dev.txt
else
    echo "⚠️ requirements-dev.txt not found, skipping."
fi

deactivate
echo "✅ Development environment setup complete!"
