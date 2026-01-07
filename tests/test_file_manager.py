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

# region Clipboard and Paste Tests
def test_copy_and_paste_file(tmp_path):
    fm = FileManager()
    source_file = tmp_path / "source.txt"
    source_file.touch()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    fm.copy_to_clipboard(str(source_file))
    fm.paste_item(str(dest_dir))

    assert (dest_dir / "source.txt").exists()
    assert source_file.exists() # Original should still exist

def test_cut_and_paste_file(tmp_path):
    fm = FileManager()
    source_file = tmp_path / "source.txt"
    source_file.touch()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    fm.cut_to_clipboard(str(source_file))
    fm.paste_item(str(dest_dir))

    assert (dest_dir / "source.txt").exists()
    assert not source_file.exists() # Original should be gone

def test_copy_and_paste_directory(tmp_path):
    fm = FileManager()
    source_dir = tmp_path / "source_dir"
    source_dir.mkdir()
    (source_dir / "child.txt").touch()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    fm.copy_to_clipboard(str(source_dir))
    fm.paste_item(str(dest_dir))

    assert (dest_dir / "source_dir").is_dir()
    assert (dest_dir / "source_dir" / "child.txt").exists()
    assert source_dir.exists()

def test_cut_and_paste_directory(tmp_path):
    fm = FileManager()
    source_dir = tmp_path / "source_dir"
    source_dir.mkdir()
    (source_dir / "child.txt").touch()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    fm.cut_to_clipboard(str(source_dir))
    fm.paste_item(str(dest_dir))

    assert (dest_dir / "source_dir").is_dir()
    assert (dest_dir / "source_dir" / "child.txt").exists()
    assert not source_dir.exists()

def test_paste_with_empty_clipboard(tmp_path):
    fm = FileManager()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    with pytest.raises(ValueError, match="Clipboard is empty"):
        fm.paste_item(str(dest_dir))

def test_paste_to_non_existent_directory(tmp_path):
    fm = FileManager()
    source_file = tmp_path / "source.txt"
    source_file.touch()
    non_existent_dest = tmp_path / "non_existent"

    fm.copy_to_clipboard(str(source_file))

    with pytest.raises(FileNotFoundError):
        fm.paste_item(str(non_existent_dest))

def test_copy_paste_over_existing_file(tmp_path):
    fm = FileManager()
    source_file = tmp_path / "source.txt"
    source_file.touch()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    (dest_dir / "source.txt").touch()

    fm.copy_to_clipboard(str(source_file))

    with pytest.raises(FileExistsError):
        fm.paste_item(str(dest_dir))
# endregion

# region Calculate Size Tests
def test_calculate_directory_size_successfully(tmp_path, mocker):
    """
    Test that directory size is calculated correctly, including subdirectories.
    """
    fm = FileManager()
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    
    # Create files and subdirectories
    (test_dir / "file1.txt").write_text("12345")  # 5 bytes
    sub_dir = test_dir / "sub"
    sub_dir.mkdir()
    (sub_dir / "file2.txt").write_text("1234567890")  # 10 bytes
    
    expected_size = 15
    
    # Mock the task object
    mock_task = mocker.Mock()
    mock_task.status = TaskStatus.IN_PROGRESS
    
    # Action
    calculated_size = fm.calculate_directory_size(str(test_dir), task=mock_task)
    
    # Assert
    assert calculated_size == expected_size
    mock_task.set_progress.assert_called_with(100)
    mock_task.set_details.assert_called_with("Found 2 files.")

def test_calculate_directory_size_cancelled(tmp_path, mocker):
    """
    Test that the calculation stops when the task is cancelled.
    """
    fm = FileManager()
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    
    # We don't need to create real files, as we're mocking os.walk
    
    mock_task = mocker.Mock()
    mock_task.status = TaskStatus.IN_PROGRESS

    # Mock os.walk to return a controlled list of files
    mock_walk = mocker.patch('file_operations.file_manager.os.walk')
    mock_walk.return_value = [
        (str(test_dir), [], ['file1.txt', 'file2.txt']),
    ]

    # Mock getsize to cancel the task on the first call
    mock_getsize = mocker.patch('file_operations.file_manager.os.path.getsize')
    def getsize_side_effect(path):
        mock_task.status = TaskStatus.CANCELLED
        return 10 # Return some size

    mock_getsize.side_effect = getsize_side_effect
    
    # Action
    size = fm.calculate_directory_size(str(test_dir), task=mock_task)
    
    # Assert
    assert size == 0
    # The loop should break after the first file, so getsize is called only once
    mock_getsize.assert_called_once()
# endregion
