import logging
import os
from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QLineEdit, QComboBox, QSizePolicy
from browser.flat_view import FlatFileView
from browser.tree_view import TreeFileView
from app.settings_manager import SettingsManager

class PanelWidget(QWidget):
    def __init__(self, settings_manager, view_mode, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.view_mode = view_mode
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)

        self.drive_combo = QComboBox()
        self.drive_combo.setMaximumWidth(140)
        self.drive_combo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.layout.addWidget(self.drive_combo)

        self.path_edit = QLineEdit()
        self.layout.addWidget(self.path_edit)

        if self.view_mode == "flat":
            self.file_view = FlatFileView(self.settings_manager, self)
        else: # "tree"
            self.file_view = TreeFileView(self.settings_manager, self)
        
        self.layout.addWidget(self.file_view)

class FolderBrowser(QWidget):
    file_selected = pyqtSignal(str)
    current_directory_changed = pyqtSignal(str)

    def __init__(self, view_mode="flat", settings_manager: SettingsManager = None, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.view_mode = view_mode
        self.active_panel_widget = None
        self.current_paths = {}

        self.left_panel_widget = PanelWidget(self.settings_manager, self.view_mode, self)
        self.right_panel_widget = PanelWidget(self.settings_manager, self.view_mode, self)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.left_panel_widget)
        splitter.addWidget(self.right_panel_widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)
        
        self.set_active_panel(self.left_panel_widget)

    def set_active_panel(self, panel_widget):
        self.active_panel_widget = panel_widget
        # Logic to indicate active panel (e.g., style sheets) can be added here

    def go_up_directory(self):
        if self.active_panel_widget:
            self.active_panel_widget.file_view.go_up()

    def refresh_all_views(self):
        self.left_panel_widget.file_view.refresh()
        self.right_panel_widget.file_view.refresh()

    def set_view_mode(self, mode):
        if self.view_mode == mode:
            return
        self.view_mode = mode
        
        left_path = self.left_panel_widget.file_view.get_current_path()
        right_path = self.right_panel_widget.file_view.get_current_path()

        splitter = self.findChild(QSplitter)
        
        self.left_panel_widget.deleteLater()
        self.right_panel_widget.deleteLater()

        self.left_panel_widget = PanelWidget(self.settings_manager, self.view_mode, self)
        self.right_panel_widget = PanelWidget(self.settings_manager, self.view_mode, self)
        
        self.left_panel_widget.file_view.set_path(left_path)
        self.right_panel_widget.file_view.set_path(right_path)

        splitter.insertWidget(0, self.left_panel_widget)
        splitter.insertWidget(1, self.right_panel_widget)
        
        self.set_active_panel(self.left_panel_widget)

    def load_panel_settings(self):
        left_path = self.settings_manager.get_setting("leftPanelPath", os.path.expanduser("~"))
        right_path = self.settings_manager.get_setting("rightPanelPath", os.path.expanduser("~"))
        self.left_panel_widget.file_view.set_path(left_path)
        self.right_panel_widget.file_view.set_path(right_path)

    def save_panel_settings(self):
        self.settings_manager.set_setting("leftPanelPath", self.left_panel_widget.file_view.get_current_path())
        self.settings_manager.set_setting("rightPanelPath", self.right_panel_widget.file_view.get_current_path())
        
    def get_selected_paths(self):
        if self.active_panel_widget:
            return self.active_panel_widget.file_view.get_selected_paths()
        return []
        
    def get_current_selected_path(self):
        if self.active_panel_widget:
            return self.active_panel_widget.file_view.get_current_selected_path()
        return None
