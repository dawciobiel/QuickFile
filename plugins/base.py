from abc import ABC, abstractmethod

from PyQt6.QtWidgets import QWidget, QDialog


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
    def view_file(self, file_path: str, parent: QWidget):
        """
        Opens a non-modal dialog or a new window to view the file.
        The parent widget is provided to ensure proper window management.
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
