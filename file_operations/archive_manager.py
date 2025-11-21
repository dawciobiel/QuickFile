import os
import zipfile
import tarfile

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
            self.main_window.status_bar.showMessage(f"Błąd podczas tworzenia archiwum ZIP: {e}")

    def extract_zip_archive(self, archive_path, extract_path):
        """
        Wypakowuje archiwum ZIP do podanej lokalizacji.
        """
        try:
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                zipf.extractall(extract_path)
            self.main_window.status_bar.showMessage(f"Wypakowano archiwum do: {extract_path}")
        except Exception as e:
            self.main_window.status_bar.showMessage(f"Błąd podczas wypakowywania archiwum ZIP: {e}")

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
            self.main_window.status_bar.showMessage(f"Błąd podczas tworzenia archiwum TAR: {e}")

    def extract_tar_archive(self, archive_path, extract_path):
        """
        Wypakowuje archiwum TAR do podanej lokalizacji.
        """
        try:
            with tarfile.open(archive_path, "r:*") as tarf:
                tarf.extractall(extract_path)
            self.main_window.status_bar.showMessage(f"Wypakowano archiwum do: {extract_path}")
        except Exception as e:
            self.main_window.status_bar.showMessage(f"Błąd podczas wypakowywania archiwum TAR: {e}")
