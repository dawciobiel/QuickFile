#!/usr/bin/env bash
#==============================================================================
# unmount-slowfs.sh
#
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
#
# AUTHOR:
#   dawciobiel (https://github.com/dawciobiel)
#
# CREATED:
#   2025-12-24
#==============================================================================

MOUNT_POINT="${1:-slowfs}"

fusermount -u "$MOUNT_POINT"

echo "Unmounted slow filesystem: $MOUNT_POINT"

