from abc import ABC, abstractmethod

from PyQt6.QtWidgets import QWidget


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
