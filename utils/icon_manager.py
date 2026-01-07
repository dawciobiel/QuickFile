# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import logging
import re
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QByteArray

def get_colorized_icon(icon_path: str, new_color_hex: str) -> QIcon:
    """
    Loads an SVG icon, replaces its color using regex, and returns a QIcon.

    Args:
        icon_path: The file path to the SVG icon.
        new_color_hex: The new color as a hex string (e.g., "#FFFFFF").

    Returns:
        A QIcon with the colorized SVG.
    """
    try:
        with open(icon_path, 'r') as f:
            svg_data = f.read()

        # This regex looks for fill="some_color" or stroke="some_color" and replaces the color.
        # It avoids replacing colors like "none".
        fill_pattern = re.compile(r'(fill=")(?!none")[^"]*(")')
        stroke_pattern = re.compile(r'(stroke=")(?!none")[^"]*(")')
        
        # Replace fill color
        modified_svg_data = fill_pattern.sub(r'\g<1>{}\g<2>'.format(new_color_hex), svg_data)
        # Replace stroke color on the result of the fill replacement
        modified_svg_data = stroke_pattern.sub(r'\g<1>{}\g<2>'.format(new_color_hex), modified_svg_data)

        # Create QIcon from the modified SVG data
        icon_byte_array = QByteArray(modified_svg_data.encode('utf-8'))
        
        icon = QIcon()
        # The QIcon constructor from QByteArray is not directly available in PyQt6.
        # We need to load it into a QPixmap first.
        # However, for SVG, we can load data directly.
        # Let's ensure the byte array is correctly handled.
        # A more robust way is to use a temporary QBuffer if direct loading fails.
        # For now, let's assume the byte array works as intended with SVG data.
        # The error in logs suggests QIcon(QByteArray) might be the issue.
        # Let's try to be more explicit.
        # The issue is that QIcon() does not have a constructor that takes a QByteArray directly for SVG.
        # We need to use a different approach.
        # A simple way is to write to a temporary file, but that's inefficient.
        # A better way is to use QXmlStreamReader and QXmlStreamWriter, but that's complex.
        
        # The error QIcon(): likely means the byte array was empty or invalid.
        # Let's re-check the logic. The regex should be fine now.
        # The problem might be that QIcon(QByteArray) is not a valid constructor.
        # Let's check PyQt6 docs.
        # It seems there is no direct QIcon(QByteArray) constructor.
        # We can use addPixmap.
        from PyQt6.QtGui import QPixmap
        pixmap = QPixmap()
        pixmap.loadFromData(icon_byte_array, "svg")
        icon.addPixmap(pixmap)
        
        return icon

    except Exception as e:
        logging.error(f"Failed to colorize icon {icon_path}: {e}", exc_info=True)
        return QIcon(icon_path) # Fallback to the original icon
