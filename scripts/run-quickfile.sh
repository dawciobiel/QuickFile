#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Activates the environment defined in .envrc and runs the application
exec direnv exec . python main.py
