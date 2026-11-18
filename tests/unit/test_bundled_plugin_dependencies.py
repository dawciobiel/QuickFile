# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Contract for dependencies declared by shipped and external plugin sources.

Plugins delivered with the repository must get their third-party libraries from
the Nix development environment (``flake.nix``), not from a ``libs`` directory.
That keeps the application and the packages reproducible. A plugin that does
need its own ``libs`` must be sandboxed so its ``sys.path`` cannot leak into the
host.

Specification: ``docs/architecture/plugins/plugins.md`` ("Zależności wtyczek",
"Źródła w repozytorium").
"""

import os

from app.plugin_dependency_manager import PluginDependencyManager
from tests.plugin_helpers import iter_plugin_metadata


def _metadata_with_dependencies():
    return [
        (metadata_path, metadata)
        for metadata_path, metadata in iter_plugin_metadata()
        if metadata.get("python_dependencies")
    ]


CASES = _metadata_with_dependencies()


def test_the_contract_covers_the_plugins_that_need_third_party_libraries():
    assert {metadata["id"] for _, metadata in CASES} >= {
        "org.quickfile.delete_operation",
        "org.quickfile.rar_archiver",
    }


def test_bundled_plugin_dependencies_are_provided_by_the_development_environment():
    manager = PluginDependencyManager()

    for metadata_path, metadata in CASES:
        version_dir = os.path.dirname(metadata_path)
        status = manager.check_dependencies(version_dir, metadata)

        assert status.satisfied, (
            f"{metadata['id']} declares dependencies that the Nix environment "
            f"does not provide: {', '.join(status.missing)}. Add them to flake.nix."
        )
        assert status.libs_dir is None, (
            f"{metadata['id']} needs its own libs directory; bundled plugins must "
            "get dependencies from flake.nix instead."
        )


def test_bundled_plugins_with_dependencies_are_sandboxed():
    for metadata_path, metadata in CASES:
        assert metadata.get("sandboxed") is True, (
            f"{metadata['id']} declares python_dependencies but is not sandboxed; "
            "dependencies from libs require a separate process."
        )
