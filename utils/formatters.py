# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

def format_size(bytes_val):
    """Formats size in bytes to a human-readable string (KB, MB, GB, TB)."""
    if bytes_val is None:
        return ""
    power = 1024
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while bytes_val >= power and n < len(power_labels) - 1:
        bytes_val /= power
        n += 1
    return f"{bytes_val:.1f} {power_labels[n]}"

def format_speed(bytes_per_sec):
    """Formats speed in bytes per second to a human-readable string."""
    if bytes_per_sec == 0:
        return ""
    return f"{format_size(bytes_per_sec)}/s"
