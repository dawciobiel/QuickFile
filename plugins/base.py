# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

from abc import ABC, abstractmethod, ABCMeta

from PyQt6.QtCore import pyqtSignal, Qt, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QWidget, QDialog, QAbstractItemView, QVBoxLayout, QStyledItemDelegate, QStyle


class FileOperationPlugin(ABC):
    """
    Base interface for all file operation plugins.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """User-friendly name of the plugin, e.g., 'Standard ZIP Archiver'."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A brief description of what the plugin does."""
        pass

class MenuActionPlugin(FileOperationPlugin):
    """
    Interface for plugins that add custom actions to the main menu.
    """
    @abstractmethod
    def get_menu_actions(self) -> list[dict]:
        """
        Returns a list of actions to be added to the menu.
        Each action is a dictionary, e.g.:
        {
            'menu': 'tools',  # Target menu (e.g., 'file', 'tools', 'help')
            'text': 'My Custom Action',
            'callback': self.my_callback_function,
            'icon_path': 'path/to/icon.svg' # Optional
        }
        """
        pass

class UiExtensionPlugin(FileOperationPlugin):
    """
    Interface for plugins that extend the main application's UI.
    """
    @abstractmethod
    def initialize(self, main_window):
        """
        Called by the application to allow the plugin to add its UI elements.
        :param main_window: A reference to the main application window.
        """
        pass

class DiskUtilsPlugin(FileOperationPlugin):
    """
    Interface for plugins that provide disk utility functions (e.g., free space).
    """
    @abstractmethod
    def get_disk_usage(self, path: str) -> tuple[int, int, int] | None:
        """
        Returns a tuple of (total, used, free) bytes for the given path.
        Returns None if usage cannot be determined.
        """
        pass


class ArchivePlugin(FileOperationPlugin):
    """
    Interface for plugins that handle creating and extracting archives.
    """
    @abstractmethod
    def get_supported_extensions(self) -> list[str]:
        """
        Returns a list of file extensions supported by this plugin.
        Example: ['.zip', '.jar']
        """
        pass

    @abstractmethod
    def create_archive(self, source_paths: list[str], destination_path: str, options: dict, progress_callback=None, task_context=None, task=None):
        """
        Creates an archive from a list of source paths.
        This method must be thread-safe and support progress reporting and cancellation.
        """
        pass

    @abstractmethod
    def extract_archive(self, archive_path: str, destination_path: str, options: dict, progress_callback=None, task_context=None, task=None):
        """
        Extracts an archive to a destination path.
        This method must be thread-safe and support progress reporting and cancellation.
        """
        pass

    def get_configuration_dialog(self, parent: QWidget, current_options: dict) -> QDialog | None:
        """
        Returns a configuration dialog for creating an archive.
        The dialog should allow the user to modify 'current_options'.
        Returns None if the plugin has no configurable options.
        """
        return None

class ChecksumPlugin(FileOperationPlugin):
    """
    Interface for plugins that calculate file checksums.
    """
    @abstractmethod
    def get_supported_algorithms(self) -> list[str]:
        """
        Returns a list of supported algorithm names (e.g., ['md5', 'sha256']).
        """
        pass

    @abstractmethod
    def calculate_checksum(self, file_path: str, algorithm: str, progress_callback=None, task_context=None) -> str:
        """
        Calculates the checksum for a single file.
        """
        pass

class SearchPlugin(FileOperationPlugin):
    """
    Interface for plugins that search for files.
    """
    @abstractmethod
    def search(self, root_path: str, query: str, options: dict, progress_callback=None, task_context=None, task=None) -> list[str]:
        """
        Searches for files matching the query starting from root_path.
        Returns a list of matching file paths.
        """
        pass

class ViewerPlugin(FileOperationPlugin):
    """
    Interface for plugins that provide a file viewing capability.
    """
    @abstractmethod
    def can_view(self, file_path: str) -> bool:
        """
        Returns True if the plugin can handle viewing this file type.
        This can be based on extension, mime type, or file content.
        """
        pass

    @abstractmethod
    def view_file(self, file_path: str, theme_manager=None, parent: QWidget = None):
        """
        Opens a non-modal dialog or a new window to view the file.
        The parent widget is provided to ensure proper window management.
        """
        pass

class EditorPlugin(FileOperationPlugin):
    """
    Interface for plugins that provide a file editing capability.
    """
    @abstractmethod
    def can_handle(self, file_path: str) -> bool:
        """
        Returns True if the plugin can handle editing this file type.
        """
        pass

    @abstractmethod
    def open_editor(self, file_path: str, theme_manager, parent: QWidget):
        """
        Opens a dialog or window to edit the file.
        """
        pass

class AttributeEditorPlugin(FileOperationPlugin):
    """
    Interface for plugins that provide a file attribute editing capability.
    """
    @abstractmethod
    def is_supported(self) -> bool:
        """
        Returns True if the plugin can run on the current operating system.
        """
        pass

    @abstractmethod
    def open_editor(self, path: str, parent: QWidget):
        """
        Opens a dialog to edit attributes for the given file or directory path.
        """
        pass

class ViewModePlugin(FileOperationPlugin):
    """
    Interface for plugins that provide a file system view mode (e.g., Flat, Tree).
    """
    @property
    @abstractmethod
    def view_mode_name(self) -> str:
        """The name of the view mode, e.g., 'flat' or 'tree'."""
        pass

    @abstractmethod
    def create_view_widget(self, parent: QWidget) -> QWidget:
        """
        Creates and returns the main widget for this view mode.
        This widget should contain the model and the view (e.g., QTableView).
        """
        pass

class SymlinkPlugin(FileOperationPlugin):
    """
    Interface for plugins that handle symbolic and hard links.
    """
    @abstractmethod
    def is_supported(self) -> bool:
        """
        Returns True if the plugin can run on the current operating system.
        """
        pass

    @abstractmethod
    def create_link(self, source_path: str, default_link_dir: str, parent: QWidget):
        """
        Opens a dialog to create a link (symbolic or hard) to the source path.
        """
        pass

    @abstractmethod
    def modify_link(self, link_path: str, parent: QWidget):
        """
        Opens a dialog to modify an existing symbolic link.
        """
        pass


class StandardOperationsPlugin(FileOperationPlugin):
    """
    Interface for plugins that handle standard file operations: copy, move, delete.
    """

    @abstractmethod
    def copy_items(self, source_paths: list[str], destination_path: str, options: dict, progress_callback=None, task_context=None,
                   task=None):
        """
        Copies items from source_paths to destination_path.
        """
        pass

    @abstractmethod
    def move_items(self, source_paths: list[str], destination_path: str, options: dict, progress_callback=None, task_context=None,
                   task=None):
        """
        Moves items from source_paths to destination_path.
        """
        pass

    @abstractmethod
    def delete_items(self, item_paths: list[str], options: dict, progress_callback=None, task_context=None, task=None):
        """
        Deletes items specified in item_paths.
        """
        pass

# --- Base classes for View Plugins ---

class AbstractFileView(QWidget):
    path_changed = pyqtSignal(str)
    file_selected = pyqtSignal(str)
    insert_selection_changed = pyqtSignal()

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # These attributes should be initialized by subclasses
        self.view: QAbstractItemView | None = None
        self.model = None 

    def set_path(self, path):
        raise NotImplementedError

    def get_current_path(self):
        raise NotImplementedError

    def get_selected_paths(self):
        raise NotImplementedError

    def get_current_selected_path(self):
        raise NotImplementedError

    def refresh(self):
        raise NotImplementedError

    def go_up(self):
        import os
        current_path = self.get_current_path()
        parent_path = os.path.dirname(current_path)
        if os.path.exists(parent_path):
            self.set_path(parent_path)

    def toggle_selection(self):
        raise NotImplementedError

    def get_insert_selected_paths(self):
        return []

    def clear_selection(self):
        pass

    def _handle_common_key_events(self, event, current_index):
        if not self.view or not self.model:
            return False

        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if current_index.isValid():
                # Emit doubleClicked signal to handle navigation or file opening
                self.view.doubleClicked.emit(current_index)
                return True

        return False

# Custom metaclass to resolve the conflict between QObject's metaclass and ABCMeta
class QTableModelABCMeta(type(QAbstractTableModel), ABCMeta):
    pass

class AbstractFileSystemModel(QAbstractTableModel, ABC, metaclass=QTableModelABCMeta):
    """
    Abstract base class for custom file system models.
    It provides a common interface for different view modes,
    but leaves the data storage and retrieval to subclasses.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

    @abstractmethod
    def filePath(self, index: QModelIndex) -> str:
        """
        Should return the full path for the given index.
        """
        pass

    @abstractmethod
    def isDir(self, index: QModelIndex) -> bool:
        """
        Should return True if the item at the index is a directory.
        """
        pass

    @abstractmethod
    def fileName(self, index: QModelIndex) -> str:
        """
        Should return the file name for the given index.
        """
        pass

    @abstractmethod
    def refresh(self):
        """
        Should refresh the model's data from the file system.
        """
        pass

    @abstractmethod
    def set_current_path(self, path: str):
        """
        Sets the current path for the model to display.
        """
        pass

FileStyleRole = Qt.ItemDataRole.UserRole + 1

class FileStyleDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        # Create a copy of the option to modify it without affecting other delegates
        opt = option
        self.initStyleOption(opt, index)

        # Retrieve style data from the model
        style_data = index.data(FileStyleRole)

        if style_data:
            # Apply foreground color
            if "foreground_color" in style_data:
                color = QColor(style_data["foreground_color"])
                if color.isValid():
                    # Only apply custom color if the item is NOT selected
                    # Otherwise, use the system's selection text color for better contrast
                    if not (opt.state & QStyle.StateFlag.State_Selected):
                        opt.palette.setColor(QPalette.ColorRole.Text, color)

            # Apply font styles
            if "font_weight" in style_data and style_data["font_weight"] == "bold":
                opt.font.setBold(True)
            if "font_italic" in style_data and style_data["font_italic"]:
                opt.font.setItalic(True)
            if "font_strikethrough" in style_data and style_data["font_strikethrough"]:
                opt.font.setStrikeOut(True)

        # Let the base class handle the painting with our modified options
        super().paint(painter, opt, index)

        # Custom styling for insert-selected items (overlay)
        # We need to access the model directly here as this is specific logic
        # Ideally, this should also be exposed via data() role, but for now:
        if hasattr(index.model(), '_insert_selected_items'):
            file_path = index.model().filePath(index)
            if file_path and file_path in index.model()._insert_selected_items:
                if not (opt.state & QStyle.StateFlag.State_Selected):
                    painter.save()
                    rect = opt.rect
                    overlay_color = QColor(255, 255, 0, 40)  # Semi-transparent yellow
                    painter.fillRect(rect, overlay_color)
                    painter.restore()
