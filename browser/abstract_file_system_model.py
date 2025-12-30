from abc import ABC, abstractmethod, ABCMeta
from PyQt6.QtCore import QAbstractTableModel, QModelIndex

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
