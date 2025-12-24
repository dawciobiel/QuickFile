#!/usr/bin/env bash
#==============================================================================
# mount-slowfs.sh
#
# DESCRIPTION:
#   Mounts a slow FUSE-based filesystem using SSHFS to localhost. This creates
#   an intentionally slow I/O environment ideal for testing file managers,
#   progress bars, and deletion performance without modifying application code.
#
#   The mounted directory behaves like a normal folder, but all operations
#   (delete, copy, move) are significantly slower due to SSH encryption,
#   FUSE overhead, and user-space roundtrips.
#
# USAGE:
#   ./mount-slowfs.sh [mount_point]
#
#   Example:
#       ./mount-slowfs.sh slowfs
#
# REQUIREMENTS:
#   - sshfs installed
#   - SSH server running locally (usually enabled by default)
#
# AUTHOR:
#   dawciobiel (https://github.com/dawciobiel)
#
# CREATED:
#   2025-12-24
#==============================================================================

MOUNT_POINT="${1:-slowfs}"

mkdir -p "$MOUNT_POINT"
sshfs localhost:/tmp "$MOUNT_POINT"

echo "Mounted slow filesystem at: $MOUNT_POINT"

