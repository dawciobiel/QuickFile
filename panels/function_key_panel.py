# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from PyQt6.QtWidgets import QWidget, QPushButton, QHBoxLayout
from app.translation_manager import translation_manager

class FunctionKeyPanel(QWidget):
    def __init__(self, main_window, menu_actions):
        super().__init__()
        self.main_window = main_window
        self.menu_actions = menu_actions
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)

        self._create_function_buttons()

    def _create_function_buttons(self):
        # Helper to create a button from a menu action
        def create_button(action_id, default_text, tooltip):
            action = self.menu_actions.get(action_id)
            if action:
                btn = QPushButton(action.icon(), default_text)
                btn.setToolTip(tooltip)
                btn.clicked.connect(action.trigger)
                return btn
            else:
                # Fallback for actions not in menu (like F1 Help)
                btn = QPushButton(default_text)
                btn.setToolTip(tooltip)
                return btn

        # F1 - Help (placeholder, no central action)
        btn_f1 = QPushButton(translation_manager.translate("FunctionKeyPanel", "F1 Help"))
        btn_f1.setToolTip(translation_manager.translate("FunctionKeyPanel", "Show help (not implemented)"))
        btn_f1.clicked.connect(lambda: self.main_window.statusBar().showMessage(translation_manager.translate("KeyboardEventManager", "F1: Help (not implemented)")))
        self.layout.addWidget(btn_f1)

        # F2 - Rename
        btn_f2 = create_button("operations.rename", translation_manager.translate("FunctionKeyPanel", "F2 Rename"), translation_manager.translate("FunctionKeyPanel", "Rename selected file or folder"))
        self.layout.addWidget(btn_f2)

        # F3 - View
        btn_f3 = create_button("operations.view", translation_manager.translate("FunctionKeyPanel", "F3 View"), translation_manager.translate("FunctionKeyPanel", "View selected file"))
        self.layout.addWidget(btn_f3)

        # F4 - Edit
        btn_f4 = create_button("operations.edit", translation_manager.translate("FunctionKeyPanel", "F4 Edit"), translation_manager.translate("FunctionKeyPanel", "Edit selected file"))
        self.layout.addWidget(btn_f4)

        # F5 - Copy
        btn_f5 = create_button("operations.copy", translation_manager.translate("FunctionKeyPanel", "F5 Copy"), translation_manager.translate("FunctionKeyPanel", "Copy selected files/directories"))
        self.layout.addWidget(btn_f5)

        # F6 - Move
        btn_f6 = create_button("operations.move", translation_manager.translate("FunctionKeyPanel", "F6 Move"), translation_manager.translate("FunctionKeyPanel", "Move selected files/directories"))
        self.layout.addWidget(btn_f6)

        # F7 - New Folder
        btn_f7 = create_button("operations.new_folder", translation_manager.translate("FunctionKeyPanel", "F7 New Folder"), translation_manager.translate("FunctionKeyPanel", "Create a new directory"))
        self.layout.addWidget(btn_f7)

        # F8 - Delete
        btn_f8 = create_button("operations.delete", translation_manager.translate("FunctionKeyPanel", "F8 Delete"), translation_manager.translate("FunctionKeyPanel", "Delete selected files/directories"))
        self.layout.addWidget(btn_f8)

        # F9 - Compare
        btn_f9 = create_button("file.compare", translation_manager.translate("FunctionKeyPanel", "F9 Compare"), translation_manager.translate("FunctionKeyPanel", "Compare items"))
        self.layout.addWidget(btn_f9)

        # F10 - Exit
        btn_f10 = create_button("file.exit", translation_manager.translate("FunctionKeyPanel", "F10 Exit"), translation_manager.translate("FunctionKeyPanel", "Exit the application"))
        self.layout.addWidget(btn_f10)
