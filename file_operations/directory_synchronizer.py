import logging
import os
import shutil
import filecmp
from utils.dialogs import show_error_message


class DirectorySynchronizer:
    def __init__(self, main_window):
        self.main_window = main_window

    def synchronize(self, dir1, dir2, options):
        """
        Synchronizes two directories based on the given options.
        """
        try:
            if options.get("two_way"):
                self._synchronize_two_way(dir1, dir2, options)
            else:
                self._synchronize_one_way(dir1, dir2, options)
            self.main_window.status_bar.showMessage("Synchronization completed successfully.")
            self.main_window.folder_browser.refresh_view()
        except Exception as e:
            logging.exception(f"Error during synchronization between {dir1} and {dir2}: {e}")
            show_error_message(self.main_window, "Synchronization Error", f"Error during synchronization: {e}")

    def _synchronize_one_way(self, source, dest, options):
        """One-way synchronization (source -> dest)."""
        comparison = filecmp.dircmp(source, dest)
        
        # Copy files that are in source but not in dest
        for item in comparison.left_only:
            shutil.copy2(os.path.join(source, item), os.path.join(dest, item))

        # Copy files that are in both but differ
        for item in comparison.diff_files:
            shutil.copy2(os.path.join(source, item), os.path.join(dest, item))

        # Delete files from dest if the option is enabled
        if options.get("delete"):
            for item in comparison.right_only:
                path = os.path.join(dest, item)
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)

        # Recursively for subdirectories
        if options.get("include_subdirs"):
            for common_dir in comparison.common_dirs:
                self._synchronize_one_way(os.path.join(source, common_dir), os.path.join(dest, common_dir), options)

    def _synchronize_two_way(self, dir1, dir2, options):
        """Two-way synchronization (copy newer files)."""
        comparison = filecmp.dircmp(dir1, dir2)

        # Files only in dir1 -> copy to dir2
        for item in comparison.left_only:
            shutil.copy2(os.path.join(dir1, item), os.path.join(dir2, item))

        # Files only in dir2 -> copy to dir1
        for item in comparison.right_only:
            shutil.copy2(os.path.join(dir2, item), os.path.join(dir1, item))

        # Files that differ -> copy newer
        for item in comparison.diff_files:
            path1 = os.path.join(dir1, item)
            path2 = os.path.join(dir2, item)
            if os.path.getmtime(path1) > os.path.getmtime(path2):
                shutil.copy2(path1, path2)
            else:
                shutil.copy2(path2, path1)
        
        # Recursively for subdirectories
        if options.get("include_subdirs"):
            for common_dir in comparison.common_dirs:
                self._synchronize_two_way(os.path.join(dir1, common_dir), os.path.join(dir2, common_dir), options)
