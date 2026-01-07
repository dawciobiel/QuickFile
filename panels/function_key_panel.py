# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os

from PyQt6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QStyle
from PyQt6.QtGui import QKeySequence, QAction
from app.translation_manager import translation_manager # Import our new manager


class FunctionKeyPanel(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)

        self._create_function_buttons()

    def _create_function_buttons(self):
        # F1 - Help (placeholder)
        btn_f1 = QPushButton(translation_manager.translate("FunctionKeyPanel", "F1 Help"))
        btn_f1.setToolTip(translation_manager.translate("FunctionKeyPanel", "Show help (not implemented)"))
        btn_f1.clicked.connect(lambda: self.main_window.status_bar.showMessage(translation_manager.translate("KeyboardEventManager", "F1: Help (not implemented)")))
        self.layout.addWidget(btn_f1)

        # F2 - Rename
        rename_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_LineEditClearButton), translation_manager.translate("FunctionKeyPanel", "F2 Rename"), self.main_window)
        rename_action.setShortcut(QKeySequence("F2"))
        rename_action.triggered.connect(self.main_window.application_logic_handler.rename_selected_item)
        btn_f2 = QPushButton(rename_action.icon(), rename_action.text())
        btn_f2.setToolTip(translation_manager.translate("FunctionKeyPanel", "Rename selected file or folder"))
        btn_f2.clicked.connect(rename_action.trigger)
        self.layout.addWidget(btn_f2)

        # F3 - View (Open Externally)
        view_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon), translation_manager.translate("FunctionKeyPanel", "F3 View"), self.main_window)
        view_action.setShortcut(QKeySequence("F3"))
        view_action.triggered.connect(lambda: self.main_window.application_logic_handler._handle_f3_key())
        btn_f3 = QPushButton(view_action.icon(), view_action.text())
        btn_f3.setToolTip(translation_manager.translate("FunctionKeyPanel", "View selected file using default application"))
        btn_f3.clicked.connect(view_action.trigger)
        self.layout.addWidget(btn_f3)

        # F4 - Edit (Open Externally)
        edit_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon), translation_manager.translate("FunctionKeyPanel", "F4 Edit"), self.main_window)
        edit_action.setShortcut(QKeySequence("F4"))
        edit_action.triggered.connect(lambda: self.main_window.application_logic_handler._handle_f4_key())
        btn_f4 = QPushButton(edit_action.icon(), edit_action.text())
        btn_f4.setToolTip(translation_manager.translate("FunctionKeyPanel", "Edit selected file using default application"))
        btn_f4.clicked.connect(edit_action.trigger)
        self.layout.addWidget(btn_f4)

        # F5 - Copy
        copy_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileLinkIcon), translation_manager.translate("FunctionKeyPanel", "F5 Copy"), self.main_window)
        copy_action.setShortcut(QKeySequence("F5"))
        copy_action.triggered.connect(self.main_window.application_logic_handler.copy_selected_item)
        btn_f5 = QPushButton(copy_action.icon(), copy_action.text())
        btn_f5.setToolTip(translation_manager.translate("FunctionKeyPanel", "Copy selected files/directories"))
        btn_f5.clicked.connect(copy_action.trigger)
        self.layout.addWidget(btn_f5)

        # F6 - Move
        move_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_DirLinkIcon), translation_manager.translate("FunctionKeyPanel", "F6 Move"), self.main_window)
        move_action.setShortcut(QKeySequence("F6"))
        move_action.triggered.connect(self.main_window.application_logic_handler.move_selected_item)
        btn_f6 = QPushButton(move_action.icon(), move_action.text())
        btn_f6.setToolTip(translation_manager.translate("FunctionKeyPanel", "Move selected files/directories"))
        btn_f6.clicked.connect(move_action.trigger)
        self.layout.addWidget(btn_f6)

        # F7 - New Folder
        new_folder_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon), translation_manager.translate("FunctionKeyPanel", "F7 New Folder"), self.main_window)
        new_folder_action.setShortcut(QKeySequence("F7"))
        new_folder_action.triggered.connect(self.main_window.application_logic_handler.create_new_directory)
        btn_f7 = QPushButton(new_folder_action.icon(), new_folder_action.text())
        btn_f7.setToolTip(translation_manager.translate("FunctionKeyPanel", "Create a new directory"))
        btn_f7.clicked.connect(new_folder_action.trigger)
        self.layout.addWidget(btn_f7)

        # F8 - Delete
        delete_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon), translation_manager.translate("FunctionKeyPanel", "F8 Delete"), self.main_window)
        delete_action.setShortcut(QKeySequence("F8"))
        delete_action.triggered.connect(self.main_window.application_logic_handler.delete_selected_item)
        btn_f8 = QPushButton(delete_action.icon(), delete_action.text())
        btn_f8.setToolTip(translation_manager.translate("FunctionKeyPanel", "Delete selected files/directories"))
        btn_f8.clicked.connect(delete_action.trigger)
        self.layout.addWidget(btn_f8)

        # F9 - Compare
        compare_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogToParent), translation_manager.translate("FunctionKeyPanel", "F9 Compare"), self.main_window)
        compare_action.setShortcut(QKeySequence("F9"))
        compare_action.triggered.connect(self.main_window.application_logic_handler.compare_selected_items)
        btn_f9 = QPushButton(compare_action.icon(), compare_action.text())
        btn_f9.setToolTip(translation_manager.translate("FunctionKeyPanel", "Compare items in both panels"))
        btn_f9.clicked.connect(compare_action.trigger)
        self.layout.addWidget(btn_f9)

        # F10 - Exit
        exit_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton), translation_manager.translate("FunctionKeyPanel", "F10 Exit"), self.main_window)
        exit_action.setShortcut(QKeySequence("F10"))
        exit_action.triggered.connect(self.main_window.close)
        btn_f10 = QPushButton(exit_action.icon(), exit_action.text())
        btn_f10.setToolTip(translation_manager.translate("FunctionKeyPanel", "Exit the application"))
        btn_f10.clicked.connect(exit_action.trigger)
        self.layout.addWidget(btn_f10)
