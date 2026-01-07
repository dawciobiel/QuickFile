# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import pytest
from file_operations.file_manager import FileManager, FileManagerError

def test_create_file_successfully(tmp_path):
    """
    Test that a file is created successfully in a given directory.
    """
    fm = FileManager()
    test_dir = tmp_path
    file_name = "test_file.txt"
    
    # Action
    fm.create_file(test_dir, file_name)
    
    # Assert
    created_file_path = test_dir / file_name
    assert created_file_path.exists()
    assert created_file_path.is_file()

def test_create_file_that_already_exists(tmp_path):
    """
    Test that creating a file that already exists raises FileExistsError.
    """
    fm = FileManager()
    test_dir = tmp_path
    file_name = "existing_file.txt"
    
    # Create a file first
    (test_dir / file_name).touch()
    
    # Action and Assert
    with pytest.raises(FileExistsError):
        fm.create_file(test_dir, file_name)

def test_create_file_with_empty_name(tmp_path):
    """
    Test that creating a file with an empty name raises ValueError.
    """
    fm = FileManager()
    test_dir = tmp_path
    
    with pytest.raises(ValueError):
        fm.create_file(test_dir, "")

def test_create_file_in_non_existent_directory(tmp_path):
    """
    Test that creating a file in a non-existent directory raises FileNotFoundError.
    """
    fm = FileManager()
    non_existent_dir = tmp_path / "non_existent"
    
    with pytest.raises(FileNotFoundError):
        fm.create_file(non_existent_dir, "test.txt")
