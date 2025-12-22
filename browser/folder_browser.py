import logging
import os

import psutil
from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QDir
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QComboBox, QSizePolicy, QCompleter, QTabWidget

from app.settings_manager import SettingsManager
from app.theme_manager import ThemeManager
from browser.flat_view import FlatFileView
from browser.tree_view import TreeFileView


class PanelWidget(QWidget):
    def __init__(self, settings_manager, initial_view_mode, folder_browser_event_filter, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self._current_view_mode = initial_view_mode
        self._folder_browser_event_filter = folder_browser_event_filter
        self.theme_manager = theme_manager # Store theme_manager
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)

        self.drive_combo = QComboBox()
        self.drive_combo.setMaximumWidth(140)
        self.drive_combo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.layout.addWidget(self.drive_combo)

        self.path_edit = QLineEdit()
        self.layout.addWidget(self.path_edit)

        # Setup completer for the path edit - each panel has its own
        self.completer = QCompleter(self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer_model = QFileSystemModel(self)
        self.completer.setModel(self.completer_model)
        self.path_edit.setCompleter(self.completer)

        # Create both views, passing theme_manager
        self.flat_file_view = FlatFileView(self.settings_manager, self.theme_manager, self)
        self.tree_file_view = TreeFileView(self.settings_manager, self.theme_manager, self)
        
        self.layout.addWidget(self.flat_file_view)
        self.layout.addWidget(self.tree_file_view)

        # Set initial visibility
        self.flat_file_view.setVisible(self._current_view_mode == "flat")
        self.tree_file_view.setVisible(self._current_view_mode == "tree")

        # Set the initially active file_view
        self.file_view = self.flat_file_view if self._current_view_mode == "flat" else self.tree_file_view

        # Connect signals from both views to path synchronization
        self.flat_file_view.path_changed.connect(self._on_path_changed)
        self.tree_file_view.path_changed.connect(self._on_path_changed)
        
        self.path_edit.returnPressed.connect(self.on_path_edited)
        self.drive_combo.currentIndexChanged.connect(self._on_drive_selected) # Connect drive combo

        self._populate_drive_combo() # Populate drives on init

        # Install event filter for the initially active view
        if self._folder_browser_event_filter:
            self.file_view.view.installEventFilter(self._folder_browser_event_filter)

    def set_active(self, is_active):
        self.path_edit.setProperty("activePanel", is_active)
        # Use the currently active file_view
        self.file_view.view.setProperty("activePanel", is_active)
        
        # Re-polish widgets to apply new styles
        self.path_edit.style().unpolish(self.path_edit)
        self.path_edit.style().polish(self.path_edit)
        self.file_view.view.style().unpolish(self.file_view.view)
        self.file_view.view.style().polish(self.file_view.view)

    def _populate_drive_combo(self):
        """
        Populates the drive combo box with available mounted drives and partitions.
        """
        self.drive_combo.clear()
        
        mount_points = set()

        # Add QDir.drives() for Windows compatibility and common roots
        for drive in QDir.drives():
            mount_points.add(drive.path())

        # Add psutil partitions for more comprehensive Linux/macOS mount points
        try:
            partitions = psutil.disk_partitions(all=False)
            for p in partitions:
                # Filter out common system/virtual filesystems
                if p.mountpoint in ['/proc', '/sys', '/dev', '/run', '/snap'] or \
                   p.fstype in ['squashfs', 'tmpfs', 'devtmpfs', 'proc', 'sysfs', 'cgroup', 'fuse.portal', 'overlay']:
                    continue
                
                # Add typical user-mounted locations
                if p.mountpoint.startswith(('/media', '/mnt', '/run/media', os.path.expanduser('~/'))):
                    mount_points.add(p.mountpoint)
                elif p.mountpoint == '/': # Always include root
                    mount_points.add(p.mountpoint)
                elif os.path.isdir(p.mountpoint) and os.path.ismount(p.mountpoint): # Check if it's a real mount point
                    mount_points.add(p.mountpoint)

        except Exception as e:
            logging.warning(f"Failed to get disk partitions with psutil: {e}")

        sorted_mount_points = sorted(list(mount_points))
        for mp in sorted_mount_points:
            self.drive_combo.addItem(mp)

    def _on_drive_selected(self, index):
        """
        Handles selection change in the drive combo box.
        """
        if index >= 0:
            selected_drive_path = self.drive_combo.itemText(index)
            self.file_view.set_path(selected_drive_path)
            self.file_view.view.setFocus() # Set focus to the file view

    def _on_path_changed(self, new_path):
        """
        Updates the path in the line edit and sets the root for the completer.
        """
        self.path_edit.setText(new_path)
        self.completer_model.setRootPath(new_path)

        # Update drive combo to reflect current drive if it's one of the listed drives
        # Block signals to prevent recursive calls to _on_drive_selected
        self.drive_combo.blockSignals(True)
        
        best_match_index = -1
        longest_match_len = -1
        for i in range(self.drive_combo.count()):
            drive_path = self.drive_combo.itemText(i)
            # Ensure drive_path ends with a separator for accurate matching, unless it's root
            if drive_path != '/' and not drive_path.endswith(os.sep):
                drive_path += os.sep
            
            if new_path.startswith(drive_path):
                if len(drive_path) > longest_match_len:
                    longest_match_len = len(drive_path)
                    best_match_index = i
        
        if best_match_index != -1 and self.drive_combo.currentIndex() != best_match_index:
            self.drive_combo.setCurrentIndex(best_match_index)
        
        self.drive_combo.blockSignals(False)


    def on_path_edited(self):
        """
        Called when the user presses Enter in the path edit field.
        Normalizes and validates the entered path.
        """
        # Normalize the path: expand '~' and remove leading/trailing whitespace
        path = os.path.expanduser(self.path_edit.text().strip())
        
        if os.path.isdir(path):
            self.file_view.set_path(path)
            # Set focus back to the file view for keyboard navigation
            self.file_view.view.setFocus()
        else:
            # If path is invalid, revert the line edit to the current path
            self.path_edit.setText(self.file_view.get_current_path())

    def set_file_view_mode(self, mode):
        if self._current_view_mode == mode:
            return

        current_path = self.file_view.get_current_path()
        
        # Remove event filter from the old view
        if self._folder_browser_event_filter:
            self.file_view.view.removeEventFilter(self._folder_browser_event_filter)

        # Hide current view
        self.file_view.setVisible(False)
        
        # Update current view mode and set new active view
        self._current_view_mode = mode
        if mode == "flat":
            self.file_view = self.flat_file_view
        else: # "tree"
            self.file_view = self.tree_file_view
        
        # Show new view
        self.file_view.setVisible(True)
        self.file_view.set_path(current_path) # Set path for the new view
        self.file_view.view.setFocus() # Ensure focus is on the new view
        self.file_view.update_view_settings() # Apply settings to the new view

        # Install event filter for the new view
        if self._folder_browser_event_filter:
            self.file_view.view.installEventFilter(self._folder_browser_event_filter)

    def toggle_insert_selection(self):
        """
        Toggles the 'Insert' selection state for the currently selected item in the active file view.
        """
        if self.file_view:
            self.file_view.toggle_insert_selection_for_current_item()


class FolderBrowser(QWidget):
    file_selected = pyqtSignal(str)
    current_directory_changed = pyqtSignal(str)

    def __init__(self, view_mode="flat", settings_manager: SettingsManager = None, theme_manager: ThemeManager = None, parent=None):
        super().__init__(parent)

        # Load the UI from the .ui file
        uic.loadUi("ui/folder_browser.ui", self)

        self.settings_manager = settings_manager
        self.theme_manager = theme_manager
        self.view_mode = view_mode
        self.active_panel_widget = None
        self.current_paths = {}

        # Initialize tabs
        self._init_tab_widget(self.leftTabWidget)
        self._init_tab_widget(self.rightTabWidget)

        # Create initial panels
        self.add_new_tab(self.leftTabWidget, os.path.expanduser("~"))
        self.add_new_tab(self.rightTabWidget, os.path.expanduser("~"))

        # Set initial active panel
        self.set_active_panel(self.leftTabWidget.currentWidget())

    def _init_tab_widget(self, tab_widget: QTabWidget):
        tab_widget.setTabsClosable(True)
        tab_widget.tabCloseRequested.connect(lambda index: self._close_tab_at_index(tab_widget, index))
        tab_widget.currentChanged.connect(lambda index: self._on_tab_changed(tab_widget, index))

    def _create_panel_widget(self, path):
        panel = PanelWidget(self.settings_manager, self.view_mode, self, self.theme_manager, self)
        panel.file_view.set_path(path)

        # Connect signals
        panel.file_view.path_changed.connect(lambda new_path: self._update_tab_title(panel, new_path))
        panel.file_view.file_selected.connect(self.file_selected.emit)
        panel.file_view.path_changed.connect(self.current_directory_changed.emit)

        return panel

    def add_new_tab(self, target_tab_widget=None, path=None):
        """
        Adds a new tab to the specified tab widget (or the active one).
        """
        if target_tab_widget is None:
            # Determine active tab widget based on active panel
            if self.active_panel_widget:
                target_tab_widget = self._get_parent_tab_widget(self.active_panel_widget)
            else:
                target_tab_widget = self.leftTabWidget  # Default

        if path is None:
            # Use current path of active panel if available
            if self.active_panel_widget:
                path = self.active_panel_widget.file_view.get_current_path()
            else:
                path = os.path.expanduser("~")

        panel = self._create_panel_widget(path)
        index = target_tab_widget.addTab(panel, os.path.basename(path) or path)
        target_tab_widget.setCurrentIndex(index)

        # Ensure the new panel becomes active
        self.set_active_panel(panel)

    def close_current_tab(self):
        if self.active_panel_widget:
            tab_widget = self._get_parent_tab_widget(self.active_panel_widget)
            if tab_widget and tab_widget.count() > 1:
                index = tab_widget.indexOf(self.active_panel_widget)
                self._close_tab_at_index(tab_widget, index)

    def _close_tab_at_index(self, tab_widget, index):
        if tab_widget.count() > 1:
            widget = tab_widget.widget(index)
            tab_widget.removeTab(index)
            widget.deleteLater()

            # If we closed the active panel, set the new current one as active
            if widget == self.active_panel_widget:
                self.set_active_panel(tab_widget.currentWidget())

    def _on_tab_changed(self, tab_widget, index):
        if index >= 0:
            panel = tab_widget.widget(index)
            self.set_active_panel(panel)

    def _update_tab_title(self, panel, path):
        tab_widget = self._get_parent_tab_widget(panel)
        if tab_widget:
            index = tab_widget.indexOf(panel)
            if index >= 0:
                tab_widget.setTabText(index, os.path.basename(path) or path)

    def _get_parent_tab_widget(self, panel):
        # Helper to find which QTabWidget a panel belongs to
        parent = panel.parent()
        while parent:
            if isinstance(parent, QTabWidget):
                return parent
            parent = parent.parent()
        return None

    def get_inactive_panel_widget(self):
        """Returns the active widget of the opposite tab widget."""
        if not self.active_panel_widget:
            return None

        current_tab_widget = self._get_parent_tab_widget(self.active_panel_widget)
        if current_tab_widget == self.leftTabWidget:
            return self.rightTabWidget.currentWidget()
        elif current_tab_widget == self.rightTabWidget:
            return self.leftTabWidget.currentWidget()
        return None

    def get_left_panel_widget(self):
        return self.leftTabWidget.currentWidget()

    def get_right_panel_widget(self):
        return self.rightTabWidget.currentWidget()

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.FocusIn:
            # Find which panel this source belongs to
            widget = source
            while widget:
                if isinstance(widget, PanelWidget):
                    self.set_active_panel(widget)
                    break
                widget = widget.parent()
            return False
        elif event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Insert:
                if self.active_panel_widget:
                    self.active_panel_widget.toggle_insert_selection()
                return True
        return super().eventFilter(source, event)

    def set_active_panel(self, panel_widget):
        if self.active_panel_widget and self.active_panel_widget != panel_widget:
            self.active_panel_widget.set_active(False)
        
        self.active_panel_widget = panel_widget
        if self.active_panel_widget:
            self.active_panel_widget.set_active(True)
            self.active_panel_widget.file_view.view.setFocus()

    def switch_active_panel(self):
        current_tab_widget = self._get_parent_tab_widget(self.active_panel_widget)
        if current_tab_widget == self.leftTabWidget:
            target_widget = self.rightTabWidget
        else:
            target_widget = self.leftTabWidget

        self.set_active_panel(target_widget.currentWidget())

    def go_up_directory(self):
        if self.active_panel_widget:
            self.active_panel_widget.file_view.go_up()

    def refresh_all_views(self):
        for i in range(self.leftTabWidget.count()):
            self.leftTabWidget.widget(i).file_view.refresh()
        for i in range(self.rightTabWidget.count()):
            self.rightTabWidget.widget(i).file_view.refresh()

    def set_view_mode(self, mode):
        if self.view_mode == mode:
            return
        self.view_mode = mode
        self.settings_manager.set_setting("view_mode", mode)

        for i in range(self.leftTabWidget.count()):
            self.leftTabWidget.widget(i).set_file_view_mode(mode)
        for i in range(self.rightTabWidget.count()):
            self.rightTabWidget.widget(i).set_file_view_mode(mode)

        if self.active_panel_widget:
            self.set_active_panel(self.active_panel_widget)

    def set_file_permissions_display_mode(self, mode):
        for i in range(self.leftTabWidget.count()):
            self.leftTabWidget.widget(i).file_view.update_view_settings()
        for i in range(self.rightTabWidget.count()):
            self.rightTabWidget.widget(i).file_view.update_view_settings()
        self.refresh_all_views()

    def set_show_dot_files(self, show):
        for i in range(self.leftTabWidget.count()):
            self.leftTabWidget.widget(i).file_view.update_view_settings()
        for i in range(self.rightTabWidget.count()):
            self.rightTabWidget.widget(i).file_view.update_view_settings()
        self.refresh_all_views()

    def set_show_uid_column(self, show):
        for i in range(self.leftTabWidget.count()):
            self.leftTabWidget.widget(i).file_view.update_view_settings()
        for i in range(self.rightTabWidget.count()):
            self.rightTabWidget.widget(i).file_view.update_view_settings()
        self.refresh_all_views()

    def set_show_gid_column(self, show):
        for i in range(self.leftTabWidget.count()):
            self.leftTabWidget.widget(i).file_view.update_view_settings()
        for i in range(self.rightTabWidget.count()):
            self.rightTabWidget.widget(i).file_view.update_view_settings()
        self.refresh_all_views()

    def load_panel_settings(self):
        left_path = self.settings_manager.get_setting("leftPanelPath", os.path.expanduser("~"))
        right_path = self.settings_manager.get_setting("rightPanelPath", os.path.expanduser("~"))

        if self.leftTabWidget.count() > 0:
            self.leftTabWidget.widget(0).file_view.set_path(left_path)
        if self.rightTabWidget.count() > 0:
            self.rightTabWidget.widget(0).file_view.set_path(right_path)

    def save_panel_settings(self):
        if self.leftTabWidget.currentWidget():
            self.settings_manager.set_setting("leftPanelPath", self.leftTabWidget.currentWidget().file_view.get_current_path())
        if self.rightTabWidget.currentWidget():
            self.settings_manager.set_setting("rightPanelPath", self.rightTabWidget.currentWidget().file_view.get_current_path())
        
    def get_selected_paths(self):
        if not self.active_panel_widget:
            return []

        insert_selected = self.active_panel_widget.file_view.get_insert_selected_paths()
        if insert_selected:
            return insert_selected

        selected = self.active_panel_widget.file_view.get_selected_paths()
        if selected:
            return selected

        current = self.active_panel_widget.file_view.get_current_selected_path()
        if current:
            return [current]

        return []
        
    def get_current_selected_path(self):
        if self.active_panel_widget:
            return self.active_panel_widget.file_view.get_current_selected_path()
        return None

    def navigate_to_path(self, path):
        if self.active_panel_widget:
            self.active_panel_widget.file_view.set_path(path)
