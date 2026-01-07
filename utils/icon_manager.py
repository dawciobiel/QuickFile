# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import logging
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QByteArray

def get_colorized_icon(icon_path: str, new_color_hex: str) -> QIcon:
    """
    Loads an SVG icon, replaces its color, and returns a QIcon.

    This function assumes the original SVG file name contains the color
    to be replaced, e.g., 'icon_name_1F1F1F_... .svg'.

    Args:
        icon_path: The file path to the SVG icon.
        new_color_hex: The new color as a hex string (e.g., "#FFFFFF").

    Returns:
        A QIcon with the colorized SVG.
    """
    try:
        # Extract the old color from the filename
        parts = icon_path.split('_')
        old_color_str = next((part for part in parts if len(part) == 6), None)
        if not old_color_str:
            logging.warning(f"Could not determine original color from filename: {icon_path}")
            return QIcon(icon_path) # Return original icon

        with open(icon_path, 'r') as f:
            svg_data = f.read()

        # Replace the color string. The color in the file might be lowercase.
        new_color_str = new_color_hex.lstrip('#')
        modified_svg_data = svg_data.replace(old_color_str.lower(), new_color_str.lower())
        modified_svg_data = modified_svg_data.replace(old_color_str.upper(), new_color_str.upper())

        # Create QIcon from the modified SVG data
        icon_byte_array = QByteArray(modified_svg_data.encode('utf-8'))
        return QIcon(icon_byte_array)

    except Exception as e:
        logging.error(f"Failed to colorize icon {icon_path}: {e}")
        return QIcon(icon_path) # Fallback to the original icon
