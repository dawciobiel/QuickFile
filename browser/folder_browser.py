import logging
import os
import psutil
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QDir
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QLineEdit, QComboBox, QSizePolicy, QCompleter
from PyQt6.QtGui import QFileSystemModel
from browser.flat_view import FlatFileView
from browser.tree_view import TreeFileView
from app.settings_manager import SettingsManager
from app.theme_manager import ThemeManager # Import ThemeManager

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


class FolderBrowser(QWidget):
    file_selected = pyqtSignal(str)
    current_directory_changed = pyqtSignal(str)

    def __init__(self, view_mode="flat", settings_manager: SettingsManager = None, theme_manager: ThemeManager = None, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.theme_manager = theme_manager # Store theme_manager
        self.view_mode = view_mode
        self.active_panel_widget = None
        self.current_paths = {}

        # Pass self (FolderBrowser instance) as the event filter object and theme_manager
        self.left_panel_widget = PanelWidget(self.settings_manager, self.view_mode, self, self.theme_manager, self)
        self.right_panel_widget = PanelWidget(self.settings_manager, self.view_mode, self, self.theme_manager, self)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.left_panel_widget)
        splitter.addWidget(self.right_panel_widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)
        
        # The event filters are now installed by PanelWidget itself in its __init__
        # and managed by set_file_view_mode. So, these lines are removed from FolderBrowser.__init__
        # self.left_panel_widget.file_view.view.installEventFilter(self)
        # self.right_panel_widget.file_view.view.installEventFilter(self)

        self.set_active_panel(self.left_panel_widget)

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.FocusIn:
            # Check if the source is the *current* active view of either panel
            if source is self.left_panel_widget.file_view.view:
                self.set_active_panel(self.left_panel_widget)
            elif source is self.right_panel_widget.file_view.view:
                self.set_active_panel(self.right_panel_widget)
        return super().eventFilter(source, event)

    def set_active_panel(self, panel_widget):
        if self.active_panel_widget:
            self.active_panel_widget.set_active(False)
        
        self.active_panel_widget = panel_widget
        self.active_panel_widget.set_active(True)
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
        
        self.left_panel_widget.set_file_view_mode(mode)
        self.right_panel_widget.set_file_view_mode(mode)

        self.set_active_panel(self.left_panel_widget)

    def set_file_permissions_display_mode(self, mode):
        """
        Sets the file permissions display mode for both panels.
        """
        # Call update_view_settings on the currently active file_view within each panel
        self.left_panel_widget.file_view.update_view_settings()
        self.right_panel_widget.file_view.update_view_settings()
        self.refresh_all_views() # Refresh views to apply the new mode

    def set_show_dot_files(self, show):
        """
        Sets whether to show dot files for both panels.
        """
        self.left_panel_widget.file_view.update_view_settings()
        self.right_panel_widget.file_view.update_view_settings()
        self.refresh_all_views()

    def set_show_uid_column(self, show):
        """
        Sets whether to show the UID column for both panels.
        """
        self.left_panel_widget.file_view.update_view_settings()
        self.right_panel_widget.file_view.update_view_settings()
        self.refresh_all_views()

    def set_show_gid_column(self, show):
        """
        Sets whether to show the GID column for both panels.
        """
        self.left_panel_widget.file_view.update_view_settings()
        self.right_panel_widget.file_view.update_view_settings()
        self.refresh_all_views()

    def load_panel_settings(self):
        left_path = self.settings_manager.get_setting("leftPanelPath", os.path.expanduser("~"))
        right_path = self.settings_manager.get_setting("rightPanelPath", os.path.expanduser("~"))
        # Ensure set_path is called on the *current* file_view
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

    def navigate_to_path(self, path):
        """
        Navigates the active panel to the specified path.
        """
        if self.active_panel_widget:
            self.active_panel_widget.file_view.set_path(path)
