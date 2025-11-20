import filecmp
import os

class FileComparator:
    def __init__(self):
        pass

    def compare_files(self, file1_path, file2_path):
        """
        Compares two files.
        :param file1_path: Absolute path to the first file.
        :param file2_path: Absolute path to the second file.
        :return: True if files are identical, False otherwise.
        """
        if not os.path.exists(file1_path) or not os.path.exists(file2_path):
            return False # Or raise an error, depending on desired behavior
        return filecmp.cmp(file1_path, file2_path, shallow=False)

    def compare_directories(self, dir1_path, dir2_path):
        """
        Compares two directories and returns a dircmp object.
        :param dir1_path: Absolute path to the first directory.
        :param dir2_path: Absolute path to the second directory.
        :return: A filecmp.dircmp object.
        """
        if not os.path.isdir(dir1_path) or not os.path.isdir(dir2_path):
            return None # Or raise an error
        return filecmp.dircmp(dir1_path, dir2_path)

    def get_directory_comparison_report(self, dircmp_obj):
        """
        Generates a detailed report from a dircmp object.
        :param dircmp_obj: A filecmp.dircmp object.
        :return: A dictionary containing detailed comparison results.
        """
        report = {
            "left_only": dircmp_obj.left_only,
            "right_only": dircmp_obj.right_only,
            "diff_files": dircmp_obj.diff_files,
            "same_files": dircmp_obj.same_files,
            "common_dirs": dircmp_obj.common_dirs,
            "common_files": dircmp_obj.common_files,
            "common_funny": dircmp_obj.common_funny,
            "subdirs": {}
        }

        for common_dir in dircmp_obj.common_dirs:
            subdir_dircmp = dircmp_obj.subdirs[common_dir]
            report["subdirs"][common_dir] = self.get_directory_comparison_report(subdir_dircmp)
        
        return report
