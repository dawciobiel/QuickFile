# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from PyQt6.QtWidgets import QWidget

from flat_view import FlatFileView
from plugins.base import ViewModePlugin


class FlatViewPlugin(ViewModePlugin):
    
    @property
    def name(self) -> str:
        return "Flat View"

    @property
    def description(self) -> str:
        return "A classic flat, two-column file system view."

    @property
    def view_mode_name(self) -> str:
        return "flat"

    def create_view_widget(self, parent: QWidget) -> QWidget:
        # The parent (PanelWidget) is expected to have settings_manager and theme_manager.
        if hasattr(parent, 'settings_manager') and hasattr(parent, 'theme_manager'):
            return FlatFileView(parent.settings_manager, parent.theme_manager, parent)
        else:
            # Fallback or error
            raise ValueError("Parent widget for FlatFileView must have settings_manager and theme_manager attributes.")
