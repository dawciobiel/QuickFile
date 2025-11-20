import unittest
import os
import shutil
from file_operations.file_comparator import FileComparator

class TestFileComparator(unittest.TestCase):

    def setUp(self):
        """Set up temporary directories and files for testing."""
        self.test_dir = "temp_test_dir"
        os.makedirs(self.test_dir, exist_ok=True)

        self.dir1 = os.path.join(self.test_dir, "dir1")
        self.dir2 = os.path.join(self.test_dir, "dir2")
        self.dir3 = os.path.join(self.test_dir, "dir3") # For different structure

        os.makedirs(self.dir1, exist_ok=True)
        os.makedirs(self.dir2, exist_ok=True)
        os.makedirs(self.dir3, exist_ok=True)

        # Files for comparison
        self.file1_1 = os.path.join(self.dir1, "file1.txt")
        self.file1_2 = os.path.join(self.dir1, "file2.txt")
        self.file2_1 = os.path.join(self.dir2, "file1.txt")
        self.file2_2 = os.path.join(self.dir2, "file2.txt")
        self.file3_1 = os.path.join(self.dir3, "file3.txt")

        with open(self.file1_1, "w") as f:
            f.write("content of file1_1")
        with open(self.file1_2, "w") as f:
            f.write("content of file1_2")
        with open(self.file2_1, "w") as f:
            f.write("content of file1_1") # Same content as file1_1
        with open(self.file2_2, "w") as f:
            f.write("different content for file2_2")
        with open(self.file3_1, "w") as f:
            f.write("content of file3_1")

        # Subdirectories for directory comparison
        self.subdir1_1 = os.path.join(self.dir1, "subdir1")
        self.subdir2_1 = os.path.join(self.dir2, "subdir1")
        os.makedirs(self.subdir1_1, exist_ok=True)
        os.makedirs(self.subdir2_1, exist_ok=True)

        self.subdir_file1 = os.path.join(self.subdir1_1, "subfile.txt")
        self.subdir_file2 = os.path.join(self.subdir2_1, "subfile.txt")
        with open(self.subdir_file1, "w") as f:
            f.write("content in subdir file")
        with open(self.subdir_file2, "w") as f:
            f.write("content in subdir file")

        self.comparator = FileComparator()

    def tearDown(self):
        """Clean up temporary directories and files after testing."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_compare_files_identical(self):
        """Test comparison of two identical files."""
        self.assertTrue(self.comparator.compare_files(self.file1_1, self.file2_1))

    def test_compare_files_different(self):
        """Test comparison of two different files."""
        self.assertFalse(self.comparator.compare_files(self.file1_1, self.file1_2))

    def test_compare_files_non_existent(self):
        """Test comparison with non-existent files."""
        self.assertFalse(self.comparator.compare_files(self.file1_1, "non_existent_file.txt"))
        self.assertFalse(self.comparator.compare_files("non_existent_file.txt", self.file1_1))

    def test_compare_directories_identical(self):
        """Test comparison of two identical directories."""
        # Make dir1 and dir2 identical for this test
        shutil.rmtree(self.dir2)
        shutil.copytree(self.dir1, self.dir2)

        dircmp_obj = self.comparator.compare_directories(self.dir1, self.dir2)
        self.assertIsNotNone(dircmp_obj)
        self.assertEqual(len(dircmp_obj.diff_files), 0)
        self.assertEqual(len(dircmp_obj.left_only), 0)
        self.assertEqual(len(dircmp_obj.right_only), 0)
        self.assertEqual(len(dircmp_obj.common_funny), 0)

    def test_compare_directories_different_files(self):
        """Test comparison of directories with differing files."""
        dircmp_obj = self.comparator.compare_directories(self.dir1, self.dir2)
        self.assertIsNotNone(dircmp_obj)
        self.assertIn("file2.txt", dircmp_obj.diff_files) # file1_2 vs file2_2

    def test_compare_directories_left_only(self):
        """Test comparison of directories with files only in the left directory."""
        # Create a file only in dir1
        with open(os.path.join(self.dir1, "left_only.txt"), "w") as f:
            f.write("only in left")

        dircmp_obj = self.comparator.compare_directories(self.dir1, self.dir2)
        self.assertIsNotNone(dircmp_obj)
        self.assertIn("left_only.txt", dircmp_obj.left_only)

    def test_compare_directories_right_only(self):
        """Test comparison of directories with files only in the right directory."""
        # Create a file only in dir2
        with open(os.path.join(self.dir2, "right_only.txt"), "w") as f:
            f.write("only in right")

        dircmp_obj = self.comparator.compare_directories(self.dir1, self.dir2)
        self.assertIsNotNone(dircmp_obj)
        self.assertIn("right_only.txt", dircmp_obj.right_only)

    def test_compare_directories_subdirs(self):
        """Test comparison of directories with subdirectories."""
        dircmp_obj = self.comparator.compare_directories(self.dir1, self.dir2)
        self.assertIsNotNone(dircmp_obj)
        self.assertIn("subdir1", dircmp_obj.common_dirs)
        
        subdir_dircmp = dircmp_obj.subdirs["subdir1"]
        self.assertIsNotNone(subdir_dircmp)
        self.assertEqual(len(subdir_dircmp.diff_files), 0)
        self.assertEqual(len(subdir_dircmp.left_only), 0)
        self.assertEqual(len(subdir_dircmp.right_only), 0)

    def test_get_directory_comparison_report(self):
        """Test the detailed report generation for directory comparison."""
        dircmp_obj = self.comparator.compare_directories(self.dir1, self.dir2)
        report = self.comparator.get_directory_comparison_report(dircmp_obj)

        self.assertIsInstance(report, dict)
        self.assertIn("diff_files", report)
        self.assertIn("left_only", report)
        self.assertIn("right_only", report)
        self.assertIn("subdirs", report)
        
        self.assertIn("file2.txt", report["diff_files"])
        self.assertIn("subdir1", report["subdirs"])
        self.assertIsInstance(report["subdirs"]["subdir1"], dict)

if __name__ == '__main__':
    unittest.main()
