import logging
import os
import shutil

import psutil
from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QDir, QTimer
from PyQt6.QtGui import QFileSystemModel, QMovie, QIcon, QFont
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QSizePolicy, QCompleter, QTabWidget, QLabel, \
    QToolButton

from app.plugin_manager import PluginManager
from app.settings_manager import SettingsManager
from app.task_queue_manager import TaskType
from app.theme_manager import ThemeManager
from app.translation_manager import translation_manager
from plugins.base import AbstractFileView
from utils.resource_path import get_resource_path


def _format_size(bytes_val):
    """Formats size in bytes to a human-readable string (KB, MB, GB, TB)."""
    if bytes_val is None:
        return ""
    power = 1024
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while bytes_val >= power and n < len(power_labels) -1 :
        bytes_val /= power
        n += 1
    return f"{bytes_val:.1f} {power_labels[n]}"


class DriveComboBox(QComboBox):
    popup_about_to_show = pyqtSignal()

    def showPopup(self):
        self.popup_about_to_show.emit()
        super().showPopup()


class PanelWidget(QWidget):
    def __init__(self, settings_manager, folder_browser_event_filter, theme_manager, plugin_manager: PluginManager, notification_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self._folder_browser_event_filter = folder_browser_event_filter
        self.theme_manager = theme_manager
        self.plugin_manager = plugin_manager
        self.notification_manager = notification_manager
        self.folder_browser = parent  # Reference to the main FolderBrowser instance
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)

        # Path Edit (Top Row)
        self.path_edit = QLineEdit()
        self.layout.addWidget(self.path_edit)

        self.completer = QCompleter(self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer_model = QFileSystemModel(self)
        self.completer.setModel(self.completer_model)
        self.path_edit.setCompleter(self.completer)

        # Navigation Bar Layout (Second Row)
        self.nav_layout = QHBoxLayout()
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(2)

        self.drive_combo = DriveComboBox()
        self.drive_combo.setMaximumWidth(100)
        self.drive_combo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.drive_combo.popup_about_to_show.connect(self._refresh_drive_combo)
        self.nav_layout.addWidget(self.drive_combo)

        # Font for buttons
        bold_font = QFont()
        bold_font.setBold(True)

        # Navigation Buttons
        self.btn_home = QToolButton()
        self.btn_home.setText("~")
        self.btn_home.setFont(bold_font)
        self.btn_home.setToolTip(translation_manager.translate("PanelWidget", "Go to Home"))
        self.btn_home.clicked.connect(self.go_home)
        self.nav_layout.addWidget(self.btn_home)

        self.btn_root = QToolButton()
        self.btn_root.setText("/")
        self.btn_root.setFont(bold_font)
        self.btn_root.setToolTip(translation_manager.translate("PanelWidget", "Go to Root"))
        self.btn_root.clicked.connect(self.go_root)
        self.nav_layout.addWidget(self.btn_root)

        self.btn_up = QToolButton()
        self.btn_up.setText("..")
        self.btn_up.setFont(bold_font)
        self.btn_up.setToolTip(translation_manager.translate("PanelWidget", "Go Up"))
        self.btn_up.clicked.connect(self.go_up)
        self.nav_layout.addWidget(self.btn_up)

        self.btn_equal = QToolButton()
        self.btn_equal.setText("=")
        self.btn_equal.setFont(bold_font)
        self.btn_equal.setToolTip(translation_manager.translate("PanelWidget", "Sync with other panel"))
        self.btn_equal.clicked.connect(self.sync_with_other_panel)
        self.nav_layout.addWidget(self.btn_equal)

        self.nav_layout.addStretch()  # Push buttons to the left

        # Free space label
        self.free_space_label = QLabel("")
        self.free_space_label.setObjectName("freeSpaceLabel")
        self.nav_layout.addWidget(self.free_space_label)

        self.layout.addLayout(self.nav_layout)

        # Dynamically create the view from a plugin
        view_plugin = self.plugin_manager.get_view_mode_plugin("flat") # Default to flat view
        if view_plugin:
            # Pass self to the plugin so it can access settings_manager etc.
            self.file_view = view_plugin.create_view_widget(self)
        else:
            # Fallback to a simple label if plugin is not found
            self.file_view = QLabel("Error: 'flat' view mode plugin not found.")
            logging.error("'flat' view mode plugin not found.")
        
        self.layout.addWidget(self.file_view)

        self.summary_label = QLabel("Summary")
        self.layout.addWidget(self.summary_label)

        if isinstance(self.file_view, AbstractFileView):
            self.file_view.path_changed.connect(self._on_path_changed)
            self.path_edit.returnPressed.connect(self.on_path_edited)
            self.drive_combo.currentIndexChanged.connect(self._on_drive_selected)

            self.file_view.view.selectionModel().currentChanged.connect(self.update_summary_panel)
            self.file_view.insert_selection_changed.connect(self.update_summary_panel)

            if self._folder_browser_event_filter:
                self.file_view.view.installEventFilter(self._folder_browser_event_filter)

        self._populate_drive_combo()


    def set_active(self, is_active):
        self.path_edit.setProperty("activePanel", is_active)
        if isinstance(self.file_view, AbstractFileView):
            self.file_view.view.setProperty("activePanel", is_active)
            # Force style update for the view and its header
            self.file_view.view.style().unpolish(self.file_view.view)
            self.file_view.view.style().polish(self.file_view.view)
            
            # Also update the header view specifically
            header = None
            if hasattr(self.file_view.view, 'header'):
                header = self.file_view.view.header()
            elif hasattr(self.file_view.view, 'horizontalHeader'):
                header = self.file_view.view.horizontalHeader()
            
            if header:
                header.setProperty("activePanel", is_active)
                header.style().unpolish(header)
                header.style().polish(header)
        
        self.path_edit.style().unpolish(self.path_edit)
        self.path_edit.style().polish(self.path_edit)

    def _get_available_drives(self):
        """
        Scans the system for available drives and mount points.
        Returns a sorted list of paths.
        """
        mount_points = set()
        for drive in QDir.drives():
            mount_points.add(drive.path())
        try:
            partitions = psutil.disk_partitions(all=False)
            for p in partitions:
                if p.mountpoint in ['/proc', '/sys', '/dev', '/run', '/snap'] or \
                   p.fstype in ['squashfs', 'tmpfs', 'devtmpfs', 'proc', 'sysfs', 'cgroup', 'fuse.portal', 'overlay']:
                    continue
                if p.mountpoint.startswith(('/media', '/mnt', '/run/media', os.path.expanduser('~/'))):
                    mount_points.add(p.mountpoint)
                elif p.mountpoint == '/':
                    mount_points.add(p.mountpoint)
                elif os.path.isdir(p.mountpoint) and os.path.ismount(p.mountpoint):
                    mount_points.add(p.mountpoint)
        except Exception as e:
            logging.warning(f"Failed to get disk partitions with psutil: {e}")
        return sorted(list(mount_points))

    def _populate_drive_combo(self):
        self.drive_combo.clear()
        drives = self._get_available_drives()
        self.drive_combo.addItems(drives)

    def _refresh_drive_combo(self):
        """Refreshes the drive list when the user opens the dropdown."""
        new_drives = self._get_available_drives()
        current_drives = [self.drive_combo.itemText(i) for i in range(self.drive_combo.count())]

        if new_drives != current_drives:
            logging.debug("Drive list changed, refreshing dropdown.")
            self.drive_combo.blockSignals(True)
            self.drive_combo.clear()
            self.drive_combo.addItems(new_drives)
            self.drive_combo.blockSignals(False)

            if isinstance(self.file_view, AbstractFileView):
                self._update_drive_selection(self.file_view.get_current_path())

    def _on_drive_selected(self, index):
        if index >= 0 and isinstance(self.file_view, AbstractFileView):
            selected_drive_path = self.drive_combo.itemText(index)
            self.file_view.set_path(selected_drive_path)
            self.file_view.view.setFocus()

    def _on_path_changed(self, new_path):
        self.path_edit.setText(new_path)
        self.completer_model.setRootPath(new_path)
        self.update_free_space_display(new_path)
        self._update_drive_selection(new_path)

    def _update_drive_selection(self, path):
        self.drive_combo.blockSignals(True)
        best_match_index = -1
        longest_match_len = -1
        for i in range(self.drive_combo.count()):
            drive_path = self.drive_combo.itemText(i)
            if drive_path != '/' and not drive_path.endswith(os.sep):
                drive_path += os.sep
            if path.startswith(drive_path):
                if len(drive_path) > longest_match_len:
                    longest_match_len = len(drive_path)
                    best_match_index = i
        if best_match_index != -1 and self.drive_combo.currentIndex() != best_match_index:
            self.drive_combo.setCurrentIndex(best_match_index)
        self.drive_combo.blockSignals(False)

    def on_path_edited(self):
        path = os.path.expanduser(self.path_edit.text().strip())
        if os.path.isdir(path) and isinstance(self.file_view, AbstractFileView):
            self.file_view.set_path(path)
            self.file_view.view.setFocus()
        elif isinstance(self.file_view, AbstractFileView):
            self.path_edit.setText(self.file_view.get_current_path())

    def update_free_space_display(self, path):
        if not path or not os.path.exists(path):
            self.free_space_label.setText("")
            return
        
        disk_utils_plugin = self.plugin_manager.get_disk_utils_plugin()
        if not disk_utils_plugin:
            self.free_space_label.setText("")
            return
            
        try:
            usage = disk_utils_plugin.get_disk_usage(path)
            if usage:
                total, used, free = usage
                free_str = _format_size(free)
                total_str = _format_size(total)
                free_text = translation_manager.translate("PanelWidget", "Free")
                self.free_space_label.setText(f"{free_text}: {free_str} / {total_str}  ")
            else:
                self.free_space_label.setText("")
        except Exception as e:
            logging.warning(f"Could not get disk usage for {path}: {e}")
            self.free_space_label.setText("")

    def toggle_insert_selection(self):
        if isinstance(self.file_view, AbstractFileView):
            self.file_view.toggle_selection()

    def update_summary_panel(self):
        if not isinstance(self.file_view, AbstractFileView):
            return

        insert_selected_paths = self.file_view.get_insert_selected_paths()
        if insert_selected_paths:
            num_files = 0
            num_dirs = 0
            total_size = 0
            for path in insert_selected_paths:
                if os.path.isdir(path):
                    num_dirs += 1
                    if hasattr(self.file_view.model, '_directory_sizes') and path in self.file_view.model._directory_sizes:
                        total_size += self.file_view.model._directory_sizes[path]
                else:
                    num_files += 1
                    try:
                        total_size += os.path.getsize(path)
                    except OSError:
                        pass
            size_str = f"{total_size / (1024 * 1024):.2f} MB" if total_size > 1024 * 1024 else f"{total_size / 1024:.2f} KB"
            selected_str = translation_manager.translate("SummaryPanel", "Selected")
            files_str = translation_manager.translate("SummaryPanel", "files")
            dirs_str = translation_manager.translate("SummaryPanel", "dirs")
            self.summary_label.setText(f"{selected_str}: {num_files} {files_str}, {num_dirs} {dirs_str} ({size_str})")
        else:
            current_index = self.file_view.view.currentIndex()
            if current_index.isValid():
                path = self.file_view.model.filePath(current_index)
                name = self.file_view.model.fileName(current_index)
                size = self.file_view.model.data(self.file_view.model.index(current_index.row(), 1), Qt.ItemDataRole.DisplayRole)
                date_modified = self.file_view.model.data(self.file_view.model.index(current_index.row(), 3), Qt.ItemDataRole.DisplayRole)
                self.summary_label.setText(f"{name} | {size} | {date_modified}")
            else:
                self.summary_label.setText("")

    def go_home(self):
        if isinstance(self.file_view, AbstractFileView):
            self.file_view.set_path(os.path.expanduser("~"))

    def go_root(self):
        if isinstance(self.file_view, AbstractFileView):
            self.file_view.set_path(os.path.abspath(os.sep))

    def go_up(self):
        if isinstance(self.file_view, AbstractFileView):
            self.file_view.go_up()

    def sync_with_other_panel(self):
        if not self.folder_browser:
            return

        other_panel = self.folder_browser.get_inactive_panel_widget()
        if other_panel and isinstance(other_panel, PanelWidget) and isinstance(other_panel.file_view, AbstractFileView) and isinstance(
                self.file_view, AbstractFileView):
            path = other_panel.file_view.get_current_path()
            self.file_view.set_path(path)


class FolderBrowser(QWidget):
    file_selected = pyqtSignal(str)
    current_directory_changed = pyqtSignal(str)
    status_message_requested = pyqtSignal(str)

    def __init__(self, settings_manager: SettingsManager, theme_manager: ThemeManager, plugin_manager: PluginManager, notification_manager, parent=None):
        super().__init__(parent)

        # --- Declare UI attributes for linter ---
        self.leftTabWidget: QTabWidget | None = None
        self.rightTabWidget: QTabWidget | None = None
        # -----------------------------------------

        try:
            uic.loadUi(get_resource_path("ui/folder_browser.ui"), self)
        except Exception as e:
            logging.critical(f"Failed to load UI: {e}", exc_info=True)
            raise
        
        self.settings_manager = settings_manager
        self.theme_manager = theme_manager
        self.plugin_manager = plugin_manager
        self.notification_manager = notification_manager
        self.active_panel_widget = None
        self.current_paths = {}
        self._init_tab_widget(self.leftTabWidget)
        self._init_tab_widget(self.rightTabWidget)
        
        self._paths_to_refresh = set()
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        
        refresh_interval = self.settings_manager.get_setting("dynamic_refresh_interval", 2000)
        self._refresh_timer.setInterval(refresh_interval)
        
        self._refresh_timer.timeout.connect(self._do_refresh)
        
        self.spinner_movie = QMovie(get_resource_path("resources/icons/spinner.gif"))
        self.busy_tabs = set()
        self.spinner_movie.frameChanged.connect(self._update_busy_icons)
        self.spinner_movie.start()
        
        self.load_panel_settings()

    def _init_tab_widget(self, tab_widget: QTabWidget):
        tab_widget.setTabsClosable(True)
        tab_widget.tabCloseRequested.connect(lambda index, tw=tab_widget: self._close_tab_at_index(tw, index))
        tab_widget.currentChanged.connect(lambda index, tw=tab_widget: self._on_tab_changed(tw, index))

    def _create_panel_widget(self, path):
        panel = PanelWidget(self.settings_manager, self, self.theme_manager, self.plugin_manager, self.notification_manager, self)
        if isinstance(panel.file_view, AbstractFileView):
            panel.file_view.set_path(path)
            panel.file_view.path_changed.connect(lambda new_path, p=panel: self._update_tab_title(p, new_path))
            panel.file_view.file_selected.connect(self.file_selected.emit)
            panel.file_view.path_changed.connect(self.current_directory_changed.emit)
        return panel

    def add_new_tab(self, target_tab_widget=None, path=None):
        if target_tab_widget is None:
            if self.active_panel_widget:
                target_tab_widget = self._get_parent_tab_widget(self.active_panel_widget)
            else:
                target_tab_widget = self.leftTabWidget
        if path is None:
            if self.active_panel_widget and isinstance(self.active_panel_widget.file_view, AbstractFileView):
                path = self.active_panel_widget.file_view.get_current_path()
            else:
                path = os.path.expanduser("~")
        panel = self._create_panel_widget(path)
        index = target_tab_widget.addTab(panel, os.path.basename(path) or path)
        target_tab_widget.setCurrentIndex(index)
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
        parent = panel.parent()
        while parent:
            if isinstance(parent, QTabWidget):
                return parent
            parent = parent.parent()
        return None

    def get_inactive_panel_widget(self):
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
            widget = source
            while widget:
                if isinstance(widget, PanelWidget):
                    self.set_active_panel(widget)
                    break
                widget = widget.parent()
            return False
        return super().eventFilter(source, event)

    def set_active_panel(self, panel_widget):
        if self.active_panel_widget and self.active_panel_widget != panel_widget:
            self.active_panel_widget.set_active(False)
        self.active_panel_widget = panel_widget
        if self.active_panel_widget:
            self.active_panel_widget.set_active(True)
            if isinstance(self.active_panel_widget.file_view, AbstractFileView):
                self.active_panel_widget.file_view.view.setFocus()

    def switch_active_panel(self):
        current_tab_widget = self._get_parent_tab_widget(self.active_panel_widget)
        if current_tab_widget == self.leftTabWidget:
            target_widget = self.rightTabWidget
        else:
            target_widget = self.leftTabWidget
        self.set_active_panel(target_widget.currentWidget())

    def go_up_directory(self):
        if self.active_panel_widget and isinstance(self.active_panel_widget.file_view, AbstractFileView):
            self.active_panel_widget.file_view.go_up()

    def refresh_all_views(self):
        for i in range(self.leftTabWidget.count()):
            widget = self.leftTabWidget.widget(i)
            if isinstance(widget.file_view, AbstractFileView):
                widget.file_view.refresh()
        for i in range(self.rightTabWidget.count()):
            widget = self.rightTabWidget.widget(i)
            if isinstance(widget.file_view, AbstractFileView):
                widget.file_view.refresh()

    def refresh_path(self, path):
        self._paths_to_refresh.add(path)
        self._refresh_timer.start()

    def _do_refresh(self):
        paths_to_process = self._paths_to_refresh.copy()
        self._paths_to_refresh.clear()

        all_panels = [self.leftTabWidget.widget(i) for i in range(self.leftTabWidget.count())] + \
                     [self.rightTabWidget.widget(i) for i in range(self.rightTabWidget.count())]

        for path in paths_to_process:
            for panel in all_panels:
                if panel and isinstance(panel.file_view, AbstractFileView) and os.path.normpath(
                        panel.file_view.get_current_path()) == os.path.normpath(path):
                    logging.debug(f"Refreshing panel at: {path}")
                    panel.file_view.refresh()

    def set_panel_paths(self, left_path, right_path):
        if self.leftTabWidget.count() > 0:
            widget = self.leftTabWidget.widget(0)
            if isinstance(widget.file_view, AbstractFileView):
                widget.file_view.set_path(left_path)
        if self.rightTabWidget.count() > 0:
            widget = self.rightTabWidget.widget(0)
            if isinstance(widget.file_view, AbstractFileView):
                widget.file_view.set_path(right_path)

    def load_panel_settings(self):
        while self.leftTabWidget.count() > 0:
            self.leftTabWidget.removeTab(0)
        while self.rightTabWidget.count() > 0:
            self.rightTabWidget.removeTab(0)

        home_path = os.path.expanduser("~")
        left_tabs = self.settings_manager.get_setting("leftPanelTabs", [home_path])
        if not left_tabs:
            left_tabs = [home_path]
            
        right_tabs = self.settings_manager.get_setting("rightPanelTabs", [home_path])
        if not right_tabs:
            right_tabs = [home_path]
            
        left_active_tab = self.settings_manager.get_setting("leftPanelActiveTab", 0)
        right_active_tab = self.settings_manager.get_setting("rightPanelActiveTab", 0)

        for path in left_tabs:
            self.add_new_tab(self.leftTabWidget, path)
        self.leftTabWidget.setCurrentIndex(left_active_tab)

        for path in right_tabs:
            self.add_new_tab(self.rightTabWidget, path)
        self.rightTabWidget.setCurrentIndex(right_active_tab)

        last_active_panel = self.settings_manager.get_setting("lastActivePanel", "left")
        if last_active_panel == "right":
            self.set_active_panel(self.rightTabWidget.currentWidget())
        else:
            self.set_active_panel(self.leftTabWidget.currentWidget())

    def save_panel_settings(self):
        left_tabs = []
        for i in range(self.leftTabWidget.count()):
            widget = self.leftTabWidget.widget(i)
            if isinstance(widget.file_view, AbstractFileView):
                left_tabs.append(widget.file_view.get_current_path())

        right_tabs = []
        for i in range(self.rightTabWidget.count()):
            widget = self.rightTabWidget.widget(i)
            if isinstance(widget.file_view, AbstractFileView):
                right_tabs.append(widget.file_view.get_current_path())
        
        self.settings_manager.set_setting("leftPanelTabs", left_tabs)
        self.settings_manager.set_setting("rightPanelTabs", right_tabs)
        self.settings_manager.set_setting("leftPanelActiveTab", self.leftTabWidget.currentIndex())
        self.settings_manager.set_setting("rightPanelActiveTab", self.rightTabWidget.currentIndex())

        active_widget = self.active_panel_widget
        if active_widget:
            parent_tab_widget = self._get_parent_tab_widget(active_widget)
            if parent_tab_widget == self.rightTabWidget:
                self.settings_manager.set_setting("lastActivePanel", "right")
            else:
                self.settings_manager.set_setting("lastActivePanel", "left")
        
    def get_selected_paths(self):
        if not self.active_panel_widget or not isinstance(self.active_panel_widget.file_view, AbstractFileView):
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
        if self.active_panel_widget and isinstance(self.active_panel_widget.file_view, AbstractFileView):
            return self.active_panel_widget.file_view.get_current_selected_path()
        return None

    def navigate_to_path(self, path):
        if self.active_panel_widget and isinstance(self.active_panel_widget.file_view, AbstractFileView):
            self.active_panel_widget.file_view.set_path(path)

    def calculate_selected_directory_size(self):
        pass

    def update_directory_size(self, path, size):
        for i in range(self.leftTabWidget.count()):
            panel = self.leftTabWidget.widget(i)
            if isinstance(panel.file_view, AbstractFileView) and panel.file_view.get_current_path() == os.path.dirname(path):
                 panel.file_view.model.update_directory_size(path, size)
        
        for i in range(self.rightTabWidget.count()):
            panel = self.rightTabWidget.widget(i)
            if isinstance(panel.file_view, AbstractFileView) and panel.file_view.get_current_path() == os.path.dirname(path):
                 panel.file_view.model.update_directory_size(path, size)

    def handle_task_completion(self, task):
        if task.type != TaskType.DELETE:
            return

        logging.debug(f"FolderBrowser handling completed DELETE task: {task.id}")

        all_panels = [self.leftTabWidget.widget(i) for i in range(self.leftTabWidget.count())] + \
                     [self.rightTabWidget.widget(i) for i in range(self.rightTabWidget.count())]

        for panel in all_panels:
            if not isinstance(panel.file_view, AbstractFileView):
                continue
            current_path = panel.file_view.get_current_path()
            if not os.path.exists(current_path):
                logging.info(f"Path no longer exists: {current_path}. Navigating up.")
                
                parent_path = current_path
                while not os.path.exists(parent_path) and parent_path != os.path.dirname(parent_path):
                    parent_path = os.path.dirname(parent_path)
                
                panel.file_view.set_path(parent_path)
                
                message = translation_manager.translate("FolderBrowser", "Directory no longer exists. Navigated up.")
                self.status_message_requested.emit(message)

    def set_tab_busy_indicator(self, panel, is_busy):
        tab_widget = self._get_parent_tab_widget(panel)
        if not tab_widget:
            return
        
        index = tab_widget.indexOf(panel)
        if index == -1:
            return
            
        tab_tuple = (tab_widget, index)

        if is_busy:
            self.busy_tabs.add(tab_tuple)
            self._update_busy_icons()
        else:
            if tab_tuple in self.busy_tabs:
                self.busy_tabs.remove(tab_tuple)
            tab_widget.setTabIcon(index, QIcon())

    def _update_busy_icons(self):
        if not self.busy_tabs:
            return
            
        current_frame_icon = QIcon(self.spinner_movie.currentPixmap())
        
        for tab_widget, index in self.busy_tabs:
            if tab_widget.widget(index):
                tab_widget.setTabIcon(index, current_frame_icon)

    def _paths_are_related(self, path1, path2):
        norm_path1 = os.path.normpath(path1)
        norm_path2 = os.path.normpath(path2)

        path1_sep = os.path.join(norm_path1, '')
        path2_sep = os.path.join(norm_path2, '')

        return path1_sep.startswith(path2_sep) or path2_sep.startswith(path1_sep)

    def find_panels_by_path(self, path):
        affected_panels = []
        all_panels = [self.leftTabWidget.widget(i) for i in range(self.leftTabWidget.count())] + \
                     [self.rightTabWidget.widget(i) for i in range(self.rightTabWidget.count())]
        
        for panel in all_panels:
            if not isinstance(panel.file_view, AbstractFileView):
                continue
            panel_path = panel.file_view.get_current_path()
            if self._paths_are_related(path, panel_path):
                affected_panels.append(panel)
                
        return affected_panels

    def clear_selection(self):
        if self.active_panel_widget:
            if hasattr(self.active_panel_widget.file_view, 'clear_selection'):
                self.active_panel_widget.file_view.clear_selection()
