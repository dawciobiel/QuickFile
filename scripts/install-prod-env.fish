#!/usr/bin/env fish
# ==============================================================================
# QuickFile - Production Environment Setup Script (Fish)
#
# Description:
#   Sets up the Python virtual environment (.venv) for production use.
#   Installs only production dependencies from requirements.txt.
#
# Usage:
#   ./scripts/install-prod-env.fish
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

echo "🔧 Setting up production virtual environment (.venv)..."

# Function to find the correct python command
function find_python_command
    if type -q python3
        echo "python3"
    else if type -q python
        echo "python"
    else
        echo "❌ Python is not installed or not in PATH." >&2
        exit 1
    end
end

set PYTHON_CMD (find_python_command)

# Create the virtual environment if it doesn't exist
if not test -d ".venv"
    echo "📦 Creating a new virtual environment..."
    $PYTHON_CMD -m venv .venv
else
    echo "✅ Virtual environment already exists."
end

# Activate the environment
source .venv/bin/activate.fish

# Upgrade pip
echo " upgrading pip..."
pip install --upgrade pip

# Install production dependencies
if test -f "requirements.txt"
    echo "📥 Installing production dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "⚠️ requirements.txt not found, skipping."
end

# Deactivate the environment
deactivate

echo "✅ Production environment setup complete!"
