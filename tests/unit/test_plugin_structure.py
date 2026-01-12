# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import json
import pytest

def get_all_plugin_version_paths():
    """
    Scans the plugins directory and yields tuples of
    (plugin_name, version_dir_name, metadata_path).
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    plugins_dir = os.path.join(project_root, 'plugins', 'org.quickfile')

    if not os.path.isdir(plugins_dir):
        return

    for plugin_name in os.listdir(plugins_dir):
        plugin_path = os.path.join(plugins_dir, plugin_name)
        if not os.path.isdir(plugin_path):
            continue

        for version_dir_name in os.listdir(plugin_path):
            version_path = os.path.join(plugin_path, version_dir_name)
            if os.path.isdir(version_path) and version_dir_name[0].isdigit():
                metadata_file = os.path.join(version_path, 'metadata.json')
                if os.path.isfile(metadata_file):
                    yield (plugin_name, version_dir_name, metadata_file)

@pytest.mark.parametrize(
    "plugin_name, version_dir, metadata_path",
    get_all_plugin_version_paths(),
    ids=lambda param: f"{param[0]}-{param[1]}" if isinstance(param, tuple) else ""
)
def test_plugin_version_matches_directory_name(plugin_name, version_dir, metadata_path):
    """
    Verifies that the 'version' in metadata.json matches the directory name.
    """
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    except json.JSONDecodeError:
        pytest.fail(f"Could not parse JSON in '{metadata_path}'")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred while reading '{metadata_path}': {e}")

    metadata_version = metadata.get('version')
    assert metadata_version is not None, f"'version' key not found in '{metadata_path}'"
    
    assert metadata_version == version_dir, (
        f"Version mismatch for plugin '{plugin_name}'. "
        f"Directory name is '{version_dir}' but metadata.json version is '{metadata_version}'."
    )
