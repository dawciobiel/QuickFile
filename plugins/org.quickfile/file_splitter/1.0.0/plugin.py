# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from plugins.base import MenuActionPlugin

class FileSplitterPlugin(MenuActionPlugin):
    @property
    def name(self):
        return "File Splitter"

    @property
    def description(self):
        return "Splits large files into smaller chunks."

    def get_menu_actions(self):
        return [
            {
                'menu': 'file',
                'text': 'Split File...',
                'callback': self.on_split_file_triggered
            }
        ]

    def on_split_file_triggered(self):
        # This will be implemented later
        print("Split File action triggered!")
        pass
