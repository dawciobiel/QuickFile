import os
import shutil
import filecmp

class DirectorySynchronizer:
    def __init__(self, main_window):
        self.main_window = main_window

    def synchronize(self, dir1, dir2, options):
        """
        Synchronizuje dwa katalogi na podstawie podanych opcji.
        """
        try:
            if options.get("two_way"):
                self._synchronize_two_way(dir1, dir2, options)
            else:
                self._synchronize_one_way(dir1, dir2, options)
            self.main_window.status_bar.showMessage("Synchronizacja zakończona pomyślnie.")
            self.main_window.folder_browser.refresh_view()
        except Exception as e:
            self.main_window.status_bar.showMessage(f"Błąd podczas synchronizacji: {e}")

    def _synchronize_one_way(self, source, dest, options):
        """Synchronizacja jednokierunkowa (source -> dest)."""
        comparison = filecmp.dircmp(source, dest)
        
        # Kopiuj pliki, które są w source, ale nie ma ich w dest
        for item in comparison.left_only:
            shutil.copy2(os.path.join(source, item), os.path.join(dest, item))

        # Kopiuj pliki, które są w obu, ale różnią się
        for item in comparison.diff_files:
            shutil.copy2(os.path.join(source, item), os.path.join(dest, item))

        # Usuń pliki z dest, jeśli opcja jest włączona
        if options.get("delete"):
            for item in comparison.right_only:
                path = os.path.join(dest, item)
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)

        # Rekurencyjnie dla podkatalogów
        if options.get("include_subdirs"):
            for common_dir in comparison.common_dirs:
                self._synchronize_one_way(os.path.join(source, common_dir), os.path.join(dest, common_dir), options)

    def _synchronize_two_way(self, dir1, dir2, options):
        """Synchronizacja dwukierunkowa (kopiowanie nowszych plików)."""
        comparison = filecmp.dircmp(dir1, dir2)

        # Pliki tylko w dir1 -> kopiuj do dir2
        for item in comparison.left_only:
            shutil.copy2(os.path.join(dir1, item), os.path.join(dir2, item))

        # Pliki tylko w dir2 -> kopiuj do dir1
        for item in comparison.right_only:
            shutil.copy2(os.path.join(dir2, item), os.path.join(dir1, item))

        # Pliki, które się różnią -> kopiuj nowszy
        for item in comparison.diff_files:
            path1 = os.path.join(dir1, item)
            path2 = os.path.join(dir2, item)
            if os.path.getmtime(path1) > os.path.getmtime(path2):
                shutil.copy2(path1, path2)
            else:
                shutil.copy2(path2, path1)
        
        # Rekurencyjnie dla podkatalogów
        if options.get("include_subdirs"):
            for common_dir in comparison.common_dirs:
                self._synchronize_two_way(os.path.join(dir1, common_dir), os.path.join(dir2, common_dir), options)
