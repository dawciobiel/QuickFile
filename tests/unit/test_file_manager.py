# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import pytest
from file_operations.file_manager import FileManager, FileManagerError
from app.task_queue_manager import TaskStatus
import os

# region Create Tests
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

def test_create_directory_successfully(tmp_path):
    """
    Test that a directory is created successfully.
    """
    fm = FileManager()
    parent_dir = tmp_path
    dir_name = "new_dir"
    
    fm.create_directory(parent_dir, dir_name)
    
    created_dir_path = parent_dir / dir_name
    assert created_dir_path.exists()
    assert created_dir_path.is_dir()

def test_create_directory_that_already_exists(tmp_path):
    """
    Test that creating a directory that already exists raises FileExistsError.
    """
    fm = FileManager()
    parent_dir = tmp_path
    dir_name = "existing_dir"
    
    (parent_dir / dir_name).mkdir()
    
    with pytest.raises(FileExistsError):
        fm.create_directory(parent_dir, dir_name)

def test_create_directory_with_empty_name(tmp_path):
    """
    Test that creating a directory with an empty name raises ValueError.
    """
    fm = FileManager()
    parent_dir = tmp_path
    
    with pytest.raises(ValueError):
        fm.create_directory(parent_dir, "")

def test_create_directory_in_non_existent_parent(tmp_path):
    """
    Test that creating a directory in a non-existent parent directory raises FileNotFoundError.
    """
    fm = FileManager()
    non_existent_parent = tmp_path / "non_existent"
    
    with pytest.raises(FileNotFoundError):
        fm.create_directory(non_existent_parent, "new_dir")
# endregion

# region Rename Tests
def test_rename_file_successfully(tmp_path):
    """
    Test that a file is renamed successfully.
    """
    fm = FileManager()
    file_path = tmp_path / "original_name.txt"
    file_path.touch()
    
    new_name = "new_name.txt"
    fm.rename_item(str(file_path), new_name)
    
    assert not file_path.exists()
    assert (tmp_path / new_name).exists()

def test_rename_directory_successfully(tmp_path):
    """
    Test that a directory is renamed successfully.
    """
    fm = FileManager()
    dir_path = tmp_path / "original_dir"
    dir_path.mkdir()
    
    new_name = "new_dir_name"
    fm.rename_item(str(dir_path), new_name)
    
    assert not dir_path.exists()
    assert (tmp_path / new_name).exists()

def test_rename_to_existing_name(tmp_path):
    """
    Test that renaming to an already existing name raises FileExistsError.
    """
    fm = FileManager()
    file_to_rename = tmp_path / "file1.txt"
    existing_file = tmp_path / "file2.txt"
    file_to_rename.touch()
    existing_file.touch()
    
    with pytest.raises(FileExistsError):
        fm.rename_item(str(file_to_rename), "file2.txt")

def test_rename_non_existent_file(tmp_path):
    """
    Test that renaming a non-existent file raises FileNotFoundError.
    """
    fm = FileManager()
    non_existent_path = tmp_path / "non_existent.txt"
    
    with pytest.raises(FileNotFoundError):
        fm.rename_item(str(non_existent_path), "new_name.txt")

def test_rename_to_empty_name(tmp_path):
    """
    Test that renaming to an empty name raises ValueError.
    """
    fm = FileManager()
    file_path = tmp_path / "some_file.txt"
    file_path.touch()
    
    with pytest.raises(ValueError):
        fm.rename_item(str(file_path), "")
# endregion
