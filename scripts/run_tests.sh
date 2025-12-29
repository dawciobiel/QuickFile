#!/bin/bash
# ==============================================================================
# Project: QuickFile
# Script: run_tests.sh
# Description: Runs all tests using pytest and captures output to a log file.
#
# Author: Dawid Bielecki "dawciobiel"
# GitHub: https://github.com/dawciobiel/QuickFile
# License: GPL 3.0
# Date: 2025-12-25
# ==============================================================================

# Go to the project root directory
cd "$(dirname "$0")/.."

# Ensure the logs directory exists
mkdir -p logs

# Log file name
LOG_FILE="logs/test_results.log"

# --- Clean up old log ---
# Use '>' to overwrite the file and start fresh
echo "Starting test session on $(date)" > "$LOG_FILE"
echo "================================================================================" >> "$LOG_FILE"

echo "Running all tests and capturing complete output to $LOG_FILE..."

# --- Run Pytest ---
# Use 'script' to trick pytest/tee into thinking they are running in an interactive terminal,
# which forces them to preserve colors and full formatting.
# The output is appended to LOG_FILE.
script -q -c "pytest -v --tb=long tests/" /dev/null | tee -a "$LOG_FILE"

# --- Check result ---
# We need to get the exit status from pytest, which is trickier with 'script'.
# We can do this by checking the log content for the word "failed".
# This is not ideal, but it is a simple and effective workaround.
if grep -q "failed" "$LOG_FILE"; then
    echo "================================================================================" >> "$LOG_FILE"
    echo "🔴 Some tests failed. Check $LOG_FILE for details." | tee -a "$LOG_FILE"
    echo "================================================================================" >> "$LOG_FILE"
else
    echo "================================================================================" >> "$LOG_FILE"
    echo "✅ All tests passed!" | tee -a "$LOG_FILE"
    echo "================================================================================" >> "$LOG_FILE"
fi

echo "Test run finished. Full output is in $LOG_FILE"
