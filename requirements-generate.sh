#!/bin/bash
# =====================================================================
# File: requirements-generate.sh
# Author: Dawid Bielecki
# Description: 
#   This script generates two requirements files for a Python project:
#     - requirements.txt: minimal dependencies based on actual imports 
#       in the source code (using pipreqs).
#     - requirements-dev.txt: full snapshot of the current virtual 
#       environment, including development tools (using pip freeze).
#
# Usage:
#   Run this script from the root directory of your Python project:
#     ./requirements-generate.sh
#
# Requirements:
#   - Python 3.x
#   - pipreqs installed in the active environment
#
# Notes:
#   - requirements.txt is intended for publishing the project 
#     (e.g., in GitHub).
#   - requirements-dev.txt is intended for developers to reproduce 
#     the exact environment 1:1.
# =====================================================================


# source .venv/bin/activate

# Generate minimal dependencies based on project imports
# This will automatically overwrite requirements.txt in the current directory
pipreqs . --force

# Generate full snapshot of the current environment
# This includes all installed packages, even development tools
pip freeze > requirements-dev.txt

# exit # .venv
