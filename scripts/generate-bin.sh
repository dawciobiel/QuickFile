#!/usr/bin/env bash
# ==============================================================================
# Project: QuickFile
# Script: generate-bin.sh
# Description: Generates a standalone binary executable using PyInstaller.
#
# Author: Dawid Bielecki "dawciobiel"
# GitHub: https://github.com/dawciobiel/QuickFile
# License: GPL 3.0
# Date: 2025-12-25
# ==============================================================================

# TODO
# Need to be added do binary file:
# `themes/`,
# `translations`,
# `README.md`
# `docs/about/*`,
# `docs/BUGS.md`
# `docs/TODO.md` or `docs/TODO.PL.md`

cd ..

# python -m venv .venv
echo "🧪 Activating the virtual environment..."
source .venv/bin/activate
# source .venv/bin/activate.fish
# pip install pyinstaller

pyinstaller --onefile --name Quickfile main.py
