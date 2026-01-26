import os
import sys
import pytest
import importlib.util

# Dodajemy główny katalog projektu do ścieżki
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Importujemy nowe fixtury i klasy
from app.task_queue_manager import Task, TaskType
from tests.conftest import async_plugin_test_env # Importujemy fixturę z conftest

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

def test_basic_search(test_files, async_plugin_test_env):
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.search_standard")

    options = {"file_name": "file*", "plugin_id": "org.quickfile.search_standard"}
    task = Task(TaskType.SEARCH, source_paths=[str(test_files)], options=options)
    
    results = async_helper.run_plugin_method_async(
        task,
        "search",
        root_path=str(test_files), # Zmieniono source_path na root_path
        query="", # query is usually passed in options for search
        options=options
    )
    
    filenames = [os.path.basename(p) for p in results]
    assert "file1.txt" in filenames
    assert "file2.LOG" in filenames
    assert "Image.png" not in filenames
    assert len(results) == 2

def test_extension_search(test_files, async_plugin_test_env):
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.search_standard")

    options = {"file_name": "*", "extension": "txt", "plugin_id": "org.quickfile.search_standard"}
    task = Task(TaskType.SEARCH, source_paths=[str(test_files)], options=options)
    
    results = async_helper.run_plugin_method_async(
        task,
        "search",
        root_path=str(test_files), # Zmieniono source_path na root_path
        query="",
        options=options
    )
    
    filenames = [os.path.basename(p) for p in results]
    assert "file1.txt" in filenames
    assert "subfile1.txt" in filenames
    assert "subfile2.txt" in filenames
    assert "TEST.TXT" in filenames # Should match if case insensitive by default
    assert "file2.LOG" not in filenames

def test_case_sensitive_filename(test_files, async_plugin_test_env):
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.search_standard")

    # Case sensitive search for "file*" should match "file1.txt" but not "FILE..." if it existed
    # Let's test with "Image.png" vs "image.png"
    
    options_cs = {"file_name": "Image*", "file_name_case_sensitive": True, "plugin_id": "org.quickfile.search_standard"}
    task_cs = Task(TaskType.SEARCH, source_paths=[str(test_files)], options=options_cs)
    results_cs = async_helper.run_plugin_method_async(
        task_cs,
        "search",
        root_path=str(test_files), # Zmieniono source_path na root_path
        query="",
        options=options_cs
    )
    assert len(results_cs) == 1
    assert os.path.basename(results_cs[0]) == "Image.png"
    
    options_ci = {"file_name": "image*", "file_name_case_sensitive": True, "plugin_id": "org.quickfile.search_standard"}
    task_ci = Task(TaskType.SEARCH, source_paths=[str(test_files)], options=options_ci)
    results_ci = async_helper.run_plugin_method_async(
        task_ci,
        "search",
        root_path=str(test_files), # Zmieniono source_path na root_path
        query="",
        options=options_ci
    )
    assert len(results_ci) == 0

    options_ci_insensitive = {"file_name": "image*", "file_name_case_sensitive": False, "plugin_id": "org.quickfile.search_standard"}
    task_ci_insensitive = Task(TaskType.SEARCH, source_paths=[str(test_files)], options=options_ci_insensitive)
    results_ci_insensitive = async_helper.run_plugin_method_async(
        task_ci_insensitive,
        "search",
        root_path=str(test_files), # Zmieniono source_path na root_path
        query="",
        options=options_ci_insensitive
    )
    assert len(results_ci_insensitive) == 1
    assert os.path.basename(results_ci_insensitive[0]) == "Image.png"

def test_case_sensitive_extension(test_files, async_plugin_test_env):
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.search_standard")

    # "txt" vs "TXT"
    
    options_ext_cs_lower = {"file_name": "*", "extension": "txt", "extension_case_sensitive": True, "plugin_id": "org.quickfile.search_standard"}
    task_ext_cs_lower = Task(TaskType.SEARCH, source_paths=[str(test_files)], options=options_ext_cs_lower)
    results_ext_cs_lower = async_helper.run_plugin_method_async(
        task_ext_cs_lower,
        "search",
        root_path=str(test_files), # Zmieniono source_path na root_path
        query="",
        options=options_ext_cs_lower
    )
    filenames_lower = [os.path.basename(p) for p in results_ext_cs_lower]
    assert "file1.txt" in filenames_lower
    assert "TEST.TXT" not in filenames_lower
    
    options_ext_cs_upper = {"file_name": "*", "extension": "TXT", "extension_case_sensitive": True, "plugin_id": "org.quickfile.search_standard"}
    task_ext_cs_upper = Task(TaskType.SEARCH, source_paths=[str(test_files)], options=options_ext_cs_upper)
    results_ext_cs_upper = async_helper.run_plugin_method_async(
        task_ext_cs_upper,
        "search",
        root_path=str(test_files), # Zmieniono source_path na root_path
        query="",
        options=options_ext_cs_upper
    )
    filenames_upper = [os.path.basename(p) for p in results_ext_cs_upper]
    assert "file1.txt" not in filenames_upper
    assert "TEST.TXT" in filenames_upper

def test_exclude_paths(test_files, async_plugin_test_env):
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.search_standard")

    subdir2 = str(test_files / "subdir2")
    options = {"file_name": "subfile*", "exclude_paths": [subdir2], "plugin_id": "org.quickfile.search_standard"}
    task = Task(TaskType.SEARCH, source_paths=[str(test_files)], options=options)
    
    results = async_helper.run_plugin_method_async(
        task,
        "search",
        root_path=str(test_files), # Zmieniono source_path na root_path
        query="",
        options=options
    )
    
    filenames = [os.path.basename(p) for p in results]
    
    assert "subfile1.txt" in filenames
    assert "subfile2.txt" not in filenames

def test_wildcards(test_files, async_plugin_test_env):
    plugin_manager, background_task_manager, async_test_helper_factory = async_plugin_test_env
    async_helper = async_test_helper_factory("org.quickfile.search_standard")

    options = {"file_name": "file?.txt", "plugin_id": "org.quickfile.search_standard"} # Should match file1.txt but not file2.LOG
    task = Task(TaskType.SEARCH, source_paths=[str(test_files)], options=options)
    
    results = async_helper.run_plugin_method_async(
        task,
        "search",
        root_path=str(test_files), # Zmieniono source_path na root_path
        query="",
        options=options
    )
    
    filenames = [os.path.basename(p) for p in results]
    assert "file1.txt" in filenames
    assert "file2.LOG" not in filenames
