#!/usr/bin/env bash
# ==============================================================================
# Project: QuickFile
# Script: unmount-slowfs.sh
# Description: Unmounts the slow SSHFS-based filesystem created by mount-slowfs.sh.
#
# Author: Dawid Bielecki "dawciobiel"
# GitHub: https://github.com/dawciobiel/QuickFile
# License: GPL 3.0
# Date: 2025-12-24
# ==============================================================================

# DESCRIPTION:
#   Unmounts the slow SSHFS-based filesystem created by mount-slowfs.sh.
#
# USAGE:
#   ./unmount-slowfs.sh [mount_point]
#
#   Example:
#       ./unmount-slowfs.sh slowfs
#
# REQUIREMENTS:
#   - fusermount (Linux)

MOUNT_POINT="${1:-slowfs}"

fusermount -u "$MOUNT_POINT"

echo "Unmounted slow filesystem: $MOUNT_POINT"
