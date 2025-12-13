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

    ACTIVE_PANEL_STYLE = "border: 2px solid blue;"
    INACTIVE_PANEL_STYLE = "border: 2px solid lightgray;"

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
        
        # Install event filters on the file views for focus detection
        self.left_panel_widget.file_view.view.installEventFilter(self)
        self.right_panel_widget.file_view.view.installEventFilter(self)

        self.set_active_panel(self.left_panel_widget)

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.FocusIn:
            if source is self.left_panel_widget.file_view.view:
                self.set_active_panel(self.left_panel_widget)
            elif source is self.right_panel_widget.file_view.view:
                self.set_active_panel(self.right_panel_widget)
        return super().eventFilter(source, event)

    def set_active_panel(self, panel_widget):
        if self.active_panel_widget:
            self.active_panel_widget.setStyleSheet(self.INACTIVE_PANEL_STYLE)
        
        self.active_panel_widget = panel_widget
        self.active_panel_widget.setStyleSheet(self.ACTIVE_PANEL_STYLE)
        self.active_panel_widget.file_view.view.setFocus() # Ensure the view inside the panel has focus

    def switch_active_panel(self):
        if self.active_panel_widget == self.left_panel_widget:
            self.set_active_panel(self.right_panel_widget)
        else:
            self.set_active_panel(self.left_panel_widget)

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
        self.settings_manager.set_setting("view_mode", mode) # Save the new view mode
        
        left_path = self.left_panel_widget.file_view.get_current_path()
        right_path = self.right_panel_widget.file_view.get_current_path()

        splitter = self.findChild(QSplitter)
        
        # Uninstall event filters from old views before deleting
        self.left_panel_widget.file_view.view.removeEventFilter(self)
        self.right_panel_widget.file_view.view.removeEventFilter(self)

        self.left_panel_widget.deleteLater()
        self.right_panel_widget.deleteLater()

        self.left_panel_widget = PanelWidget(self.settings_manager, self.view_mode, self)
        self.right_panel_widget = PanelWidget(self.settings_manager, self.view_mode, self)
        
        self.left_panel_widget.file_view.set_path(left_path)
        self.right_panel_widget.file_view.set_path(right_path)

        splitter.insertWidget(0, self.left_panel_widget)
        splitter.insertWidget(1, self.right_panel_widget)
        
        # Re-install event filters on the new views
        self.left_panel_widget.file_view.view.installEventFilter(self)
        self.right_panel_widget.file_view.view.installEventFilter(self)

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
        if not self.active_panel_widget:
            return []
            
        selected = self.active_panel_widget.file_view.get_selected_paths()
        if not selected:
            current = self.active_panel_widget.file_view.get_current_selected_path()
            if current:
                return [current]
        return selected
        
    def get_current_selected_path(self):
        if self.active_panel_widget:
            return self.active_panel_widget.file_view.get_current_selected_path()
        return None
