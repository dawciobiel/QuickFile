import logging
import os
import zipfile
import tarfile
import rarfile
import shutil

class UnrarNotInstalledError(Exception):
    """Custom exception raised when the unrar command is not found."""
    pass

class ArchiveManagerError(Exception):
    """Custom exception for ArchiveManager errors."""
    pass

class ArchiveManager:
    def __init__(self):
        pass

    def create_zip_archive(self, source_path, archive_path):
        """
        Creates a ZIP archive from the given file or folder.
        """
        try:
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if os.path.isdir(source_path):
                    for root, dirs, files in os.walk(source_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, os.path.dirname(source_path))
                            zipf.write(file_path, arcname)
                else:
                    zipf.write(source_path, os.path.basename(source_path))
            return f"Archive created: {archive_path}"
        except Exception as e:
            logging.exception(f"Error creating ZIP archive {archive_path}: {e}")
            raise ArchiveManagerError(f"Error creating ZIP archive: {e}")

    def extract_zip_archive(self, archive_path, extract_path):
        """
        Extracts a ZIP archive to the specified location.
        """
        try:
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                zipf.extractall(extract_path)
            return f"Archive extracted to: {extract_path}"
        except Exception as e:
            logging.exception(f"Error extracting ZIP archive {archive_path}: {e}")
            raise ArchiveManagerError(f"Error extracting ZIP archive: {e}")

    def create_tar_archive(self, source_path, archive_path, compression=""):
        """
        Creates a TAR archive from the given file or folder.
        compression: "gz", "bz2", "xz" or "" (no compression).
        """
        mode = "w:" + compression
        try:
            with tarfile.open(archive_path, mode) as tarf:
                tarf.add(source_path, arcname=os.path.basename(source_path))
            return f"TAR Archive created: {archive_path}"
        except Exception as e:
            logging.exception(f"Error creating TAR archive {archive_path}: {e}")
            raise ArchiveManagerError(f"Error creating TAR archive: {e}")

    def extract_tar_archive(self, archive_path, extract_path):
        """
        Extracts a TAR archive to the specified location.
        """
        try:
            with tarfile.open(archive_path, "r:*") as tarf:
                tarf.extractall(extract_path)
            return f"Archive extracted to: {extract_path}"
        except Exception as e:
            logging.exception(f"Error extracting TAR archive {archive_path}: {e}")
            raise ArchiveManagerError(f"Error extracting TAR archive: {e}")

    def extract_rar_archive(self, archive_path, extract_path):
        """
        Extracts a RAR archive to the specified location.
        Checks if the 'unrar' tool is available on the system.
        """
        if not shutil.which('unrar'):
            raise UnrarNotInstalledError("The 'unrar' tool is not installed or not in the system's PATH.")

        try:
            with rarfile.RarFile(archive_path, 'r') as rf:
                rf.extractall(extract_path)
            return f"Wypakowano archiwum RAR do: {extract_path}"
        except Exception as e:
            logging.exception(f"Error extracting RAR archive {archive_path}: {e}")
            raise ArchiveManagerError(f"Error extracting RAR archive: {e}")
