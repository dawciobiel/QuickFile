#!/usr/bin/env bash
# ==============================================================================
# Project: QuickFile
# Script: create-test-tree.sh
# Description: Generates a test directory structure for validating file deletion logic.
#
# Author: Dawid Bielecki "dawciobiel"
# GitHub: https://github.com/dawciobiel/QuickFile
# License: GPL 3.0
# Date: 2025-12-24
# ==============================================================================

# DESCRIPTION:
#   Generates a test directory structure for validating file deletion logic,
#   progress bars, and performance behavior in applications such as QuickFile.
#
#   Creates a base directory containing a configurable number of subdirectories.
#   Each subdirectory is populated with a specified number of test files.
#
#   The script is SAFE: it only creates files and directories. It does NOT
#   delete or modify any existing user data outside the target directory.
#
# USAGE:
#   ./create-test-tree.sh [target_path]
#
#   Example:
#       ./create-test-tree.sh slowfs/test_dir
#
# CONFIGURATION:
#   SUBDIR_COUNT=10
#   FILES_PER_SUBDIR=100
#
# REQUIREMENTS:
#   - Bash shell
#   - Standard GNU utilities: seq, mkdir, echo

TARGET_DIR="${1:-test_dir}"
SUBDIR_COUNT=10
FILES_PER_SUBDIR=100

mkdir -p "$TARGET_DIR"

for i in $(seq -w 1 "$SUBDIR_COUNT"); do
    SUBDIR="$TARGET_DIR/dir_$i"
    mkdir -p "$SUBDIR"

    for j in $(seq -w 1 "$FILES_PER_SUBDIR"); do
        echo "Test file $j in $SUBDIR" > "$SUBDIR/file_$j.txt"
    done
done

echo "Test directory structure created at: $TARGET_DIR"
