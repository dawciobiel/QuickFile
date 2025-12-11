#!/bin/bash
# -----------------------------------------------------------------------------
# compile_translations.sh
#
# GitHub-style documentation header
#
# This script compiles all translation source files (.ts) located in the
# 'translations' directory into binary Qt message files (.qm) using the
# `lrelease` tool from Qt.
#
# Usage:
#   ./compile_translations.sh
#
# Output:
#   - For each .ts file in the 'translations' directory, a corresponding
#     .qm file will be generated in the same directory.
#
# Notes:
#   - Ensure that Qt tools (`lrelease`) are installed and available in PATH.
#   - Run `update_translations.sh` first to refresh .ts files before compiling.
#   - Commit both .ts and .qm files to keep translations in sync.
# -----------------------------------------------------------------------------

echo "Compiling translation files..."

# Run lrelease for all .ts files in the translations directory
lrelease translations/*.ts

echo "Compilation finished."
