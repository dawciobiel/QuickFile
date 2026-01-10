# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import pytest
import importlib.util

# Helper to load the plugin class dynamically
def load_search_plugin_class():
    plugin_path = os.path.join(
        os.path.dirname(__file__), 
        "..", 
        "plugins", 
        "org.quickfile",
        "search_standard", 
        "1.0.0", 
        "plugin.py"
    )
    spec = importlib.util.spec_from_file_location("StandardSearchPlugin", plugin_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.StandardSearchPlugin

@pytest.fixture
def search_plugin():
    PluginClass = load_search_plugin_class()
    return PluginClass()

@pytest.fixture
def test_files(tmp_path):
    # Create a directory structure for testing
    # root/
    #   file1.txt
    #   file2.LOG
    #   Image.png
    #   TEST.TXT
    #   subdir1/
    #     subfile1.txt
    #   subdir2/
    #     subfile2.txt
    
    (tmp_path / "file1.txt").touch()
    (tmp_path / "file2.LOG").touch()
    (tmp_path / "Image.png").touch()
    (tmp_path / "TEST.TXT").touch()
    
    subdir1 = tmp_path / "subdir1"
    subdir1.mkdir()
    (subdir1 / "subfile1.txt").touch()
    
    subdir2 = tmp_path / "subdir2"
    subdir2.mkdir()
    (subdir2 / "subfile2.txt").touch()
    
    return tmp_path

def test_basic_search(search_plugin, test_files):
    options = {"file_name": "file*"}
    results = search_plugin.search(str(test_files), "", options)
    
    filenames = [os.path.basename(p) for p in results]
    assert "file1.txt" in filenames
    assert "file2.LOG" in filenames
    assert "Image.png" not in filenames
    assert len(results) == 2

def test_extension_search(search_plugin, test_files):
    options = {"file_name": "*", "extension": "txt"}
    results = search_plugin.search(str(test_files), "", options)
    
    filenames = [os.path.basename(p) for p in results]
    assert "file1.txt" in filenames
    assert "subfile1.txt" in filenames
    assert "subfile2.txt" in filenames
    assert "TEST.TXT" in filenames # Should match if case insensitive by default
    assert "file2.LOG" not in filenames

def test_case_sensitive_filename(search_plugin, test_files):
    # Case sensitive search for "file*" should match "file1.txt" but not "FILE..." if it existed
    # Let's test with "Image.png" vs "image.png"
    
    options = {"file_name": "Image*", "file_name_case_sensitive": True}
    results = search_plugin.search(str(test_files), "", options)
    assert len(results) == 1
    assert os.path.basename(results[0]) == "Image.png"
    
    options = {"file_name": "image*", "file_name_case_sensitive": True}
    results = search_plugin.search(str(test_files), "", options)
    assert len(results) == 0

    options = {"file_name": "image*", "file_name_case_sensitive": False}
    results = search_plugin.search(str(test_files), "", options)
    assert len(results) == 1
    assert os.path.basename(results[0]) == "Image.png"

def test_case_sensitive_extension(search_plugin, test_files):
    # "txt" vs "TXT"
    
    options = {"file_name": "*", "extension": "txt", "extension_case_sensitive": True}
    results = search_plugin.search(str(test_files), "", options)
    filenames = [os.path.basename(p) for p in results]
    assert "file1.txt" in filenames
    assert "TEST.TXT" not in filenames
    
    options = {"file_name": "*", "extension": "TXT", "extension_case_sensitive": True}
    results = search_plugin.search(str(test_files), "", options)
    filenames = [os.path.basename(p) for p in results]
    assert "file1.txt" not in filenames
    assert "TEST.TXT" in filenames

def test_exclude_paths(search_plugin, test_files):
    subdir2 = str(test_files / "subdir2")
    options = {"file_name": "subfile*", "exclude_paths": [subdir2]}
    
    results = search_plugin.search(str(test_files), "", options)
    filenames = [os.path.basename(p) for p in results]
    
    assert "subfile1.txt" in filenames
    assert "subfile2.txt" not in filenames

def test_wildcards(search_plugin, test_files):
    options = {"file_name": "file?.txt"} # Should match file1.txt but not file2.LOG
    results = search_plugin.search(str(test_files), "", options)
    
    filenames = [os.path.basename(p) for p in results]
    assert "file1.txt" in filenames
    assert "file2.LOG" not in filenames
