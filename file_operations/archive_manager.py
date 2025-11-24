import logging
import os
import zipfile
import tarfile
import rarfile
import shutil

from utils.dialogs import show_error_message


class UnrarNotInstalledError(Exception):
    """Custom exception raised when the unrar command is not found."""
    pass

class ArchiveManager:
    def __init__(self, main_window):
        self.main_window = main_window

    def create_zip_archive(self, source_path, archive_path):
        """
        Tworzy archiwum ZIP z podanego pliku lub folderu.
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
            self.main_window.status_bar.showMessage(f"Utworzono archiwum: {archive_path}")
        except Exception as e:
            logging.exception(f"Error creating ZIP archive {archive_path}: {e}")
            show_error_message(self.main_window, "Błąd tworzenia archiwum ZIP", str(e))

    def extract_zip_archive(self, archive_path, extract_path):
        """
        Wypakowuje archiwum ZIP do podanej lokalizacji.
        """
        try:
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                zipf.extractall(extract_path)
            self.main_window.status_bar.showMessage(f"Wypakowano archiwum do: {extract_path}")
        except Exception as e:
            logging.exception(f"Error extracting ZIP archive {archive_path}: {e}")
            show_error_message(self.main_window, "Błąd wypakowywania archiwum ZIP", str(e))

    def create_tar_archive(self, source_path, archive_path, compression=""):
        """
        Tworzy archiwum TAR z podanego pliku lub folderu.
        compression: "gz", "bz2", "xz" lub "" (bez kompresji).
        """
        mode = "w:" + compression
        try:
            with tarfile.open(archive_path, mode) as tarf:
                tarf.add(source_path, arcname=os.path.basename(source_path))
            self.main_window.status_bar.showMessage(f"Utworzono archiwum TAR: {archive_path}")
        except Exception as e:
            logging.exception(f"Error creating TAR archive {archive_path}: {e}")
            show_error_message(self.main_window, "Błąd tworzenia archiwum TAR", str(e))

    def extract_tar_archive(self, archive_path, extract_path):
        """
        Wypakowuje archiwum TAR do podanej lokalizacji.
        """
        try:
            with tarfile.open(archive_path, "r:*") as tarf:
                tarf.extractall(extract_path)
            self.main_window.status_bar.showMessage(f"Wypakowano archiwum do: {extract_path}")
        except Exception as e:
            logging.exception(f"Error extracting TAR archive {archive_path}: {e}")
            show_error_message(self.main_window, "Błąd wypakowywania archiwum TAR", str(e))

    def extract_rar_archive(self, archive_path, extract_path):
        """
        Wypakowuje archiwum RAR do podanej lokalizacji.
        Sprawdza, czy narzędzie 'unrar' jest dostępne w systemie.
        """
        if not shutil.which('unrar'):
            raise UnrarNotInstalledError("Narzędzie 'unrar' nie jest zainstalowane lub nie ma go w ścieżce systemowej (PATH).")

        try:
            with rarfile.RarFile(archive_path, 'r') as rf:
                rf.extractall(extract_path)
            self.main_window.status_bar.showMessage(f"Wypakowano archiwum RAR do: {extract_path}")
        except Exception as e:
            logging.exception(f"Error extracting RAR archive {archive_path}: {e}")
            show_error_message(self.main_window, "Błąd wypakowywania archiwum RAR", str(e))
            # Rzuć wyjątek dalej, aby można go było obsłużyć w UI
            raise e
