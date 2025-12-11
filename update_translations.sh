#!/bin/bash

# This script updates the .ts translation source files
# by scanning the Python source code for new translatable strings.

echo "Updating translation source files (.ts)..."

# Create a temporary .pro file to list all Python sources.
# This is the most reliable way to feed files to lupdate.
PRO_FILE="translations.pro"
echo "Creating temporary project file: $PRO_FILE"

# Find all .py files, excluding .venv, and format them for the .pro file
# The 'SOURCES +=' format is what lupdate expects in a .pro file.
find . -path ./.venv -prune -o -name "*.py" -print | sed 's/^/SOURCES += /' > "$PRO_FILE"

# Run lupdate using the generated .pro file
echo "Running lupdate on the project file..."
lupdate "$PRO_FILE" -ts translations/app_pl.ts translations/app_en.ts

# Clean up the temporary file
echo "Cleaning up temporary project file."
rm "$PRO_FILE"

echo "Update finished. Please review the .ts files to add new translations."
