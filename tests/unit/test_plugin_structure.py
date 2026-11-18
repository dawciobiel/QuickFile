# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import os
import json
import pytest

from tests.plugin_helpers import iter_plugin_version_paths

PLUGIN_CASES = list(iter_plugin_version_paths())
PLUGIN_IDS = [f"{name}-{version}" for name, version, _ in PLUGIN_CASES]


@pytest.mark.order(1)
@pytest.mark.parametrize(
    "plugin_name, version_dir, metadata_path",
    PLUGIN_CASES,
    ids=PLUGIN_IDS,
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


@pytest.mark.order(1)
@pytest.mark.parametrize(
    "plugin_name, version_dir, metadata_path",
    PLUGIN_CASES,
    ids=PLUGIN_IDS,
)
def test_plugin_root_modules_use_flat_imports(plugin_name, version_dir, metadata_path):
    """
    Modules at the root of a plugin version directory are loaded by file path
    (``spec_from_file_location``), so they have no parent package and must not
    use relative imports.

    Subpackages are different: a directory with ``__init__.py`` (for example
    ``widgets/``) is put on ``sys.path`` as a package, so relative imports
    inside it are fine.

    This test exists because a refactor once rewrote ``from tasks import X``
    into ``from .tasks import X`` in plugin entry modules. The plugins then
    failed at load time with "attempted relative import with no known parent
    package".
    """
    version_path = os.path.dirname(metadata_path)
    offenders = []

    for filename in sorted(os.listdir(version_path)):
        if not filename.endswith(".py"):
            continue

        file_path = os.path.join(version_path, filename)
        if not os.path.isfile(file_path):
            continue

        with open(file_path, "r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                stripped = line.lstrip()
                if stripped.startswith("from .") or stripped.startswith("import ."):
                    offenders.append(f"{filename}:{line_number}: {stripped.rstrip()}")

    assert not offenders, (
        f"Relative imports are not allowed in plugin root modules "
        f"('{plugin_name}' {version_dir}), because they are loaded by file path "
        f"and have no parent package. Move the code into a subpackage or use a "
        f"flat import instead:\n  " + "\n  ".join(offenders)
    )
