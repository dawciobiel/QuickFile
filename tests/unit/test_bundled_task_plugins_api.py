# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""Contract for every bundled sandboxed plugin that provides tasks.

Specification: ``docs/architecture/plugins/plugins.md`` ("Kontrakt zadań").

The explicit API is not only about naming: ``TaskPlugin.create_task`` must
return a ``PluginTask`` whose ``run`` takes the context as an argument, and the
plugin's modules must not reach for the legacy hidden state (``self.context``,
``emit_progress`` and friends). ``LegacyPluginAdapter`` stays available for
third-party plugins, but every bundled task plugin is expected to be migrated.
"""

import ast
import glob
import importlib
import inspect
import json
import os
import sys
from contextlib import contextmanager

import pytest

from app.plugin_system.api import PluginTask, TaskPlugin
from tests.plugin_helpers import get_latest_plugin_path

PLUGIN_GROUP = "org.quickfile"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PLUGINS_DIR = os.path.join(PROJECT_ROOT, "plugins", PLUGIN_GROUP)

LEGACY_ATTRIBUTES = {"context", "emit_progress", "emit_event", "request_user_input"}

#: One representative action per bundled plugin. These are factories because
#: some kwargs need a temporary path. Task creation must not touch the paths.
TASK_CASES = {
    "org.quickfile.checksum_standard": (
        "calculate_checksum",
        lambda tmp: {
            "source_paths": [str(tmp / "source.bin")],
            "algorithms": ["md5"],
        },
    ),
    "org.quickfile.copy_operation": (
        "copy_items",
        lambda tmp: {
            "source_paths": [str(tmp / "source.txt")],
            "destination_path": str(tmp / "destination"),
            "options": {},
        },
    ),
    "org.quickfile.delete_operation": (
        "delete_items",
        lambda tmp: {
            "item_paths": [str(tmp / "doomed.txt")],
            "options": {"move_to_trash": False},
        },
    ),
    "org.quickfile.directory_size": (
        "calculate_directory_size",
        lambda tmp: {"source_paths": [str(tmp)]},
    ),
    "org.quickfile.file_splitter": (
        "split_file",
        lambda tmp: {
            "source_paths": [str(tmp / "big.bin")],
            "destination_path": str(tmp / "parts"),
            "options": {"chunk_size": 1024},
        },
    ),
    "org.quickfile.move_operation": (
        "move_items",
        lambda tmp: {
            "source_paths": [str(tmp / "source.txt")],
            "destination_path": str(tmp / "destination"),
            "options": {},
        },
    ),
    "org.quickfile.rar_archiver": (
        "extract_archive",
        lambda tmp: {
            "source_path": str(tmp / "archive.rar"),
            "dest_dir": str(tmp / "extracted"),
            "options": {},
        },
    ),
    "org.quickfile.search_standard": (
        "search",
        lambda tmp: {"start_path": str(tmp), "options": {}},
    ),
    "org.quickfile.zip_archiver": (
        "create_archive",
        lambda tmp: {
            "source_paths": [str(tmp / "file.txt")],
            "destination_path": str(tmp / "archive.zip"),
            "options": {},
        },
    ),
}


def _discover_sandboxed_plugins():
    found = {}
    for metadata_path in sorted(
        glob.glob(os.path.join(PLUGINS_DIR, "*", "*", "metadata.json"))
    ):
        with open(metadata_path, encoding="utf-8") as handle:
            metadata = json.load(handle)
        if metadata.get("sandboxed", False):
            found[metadata["id"]] = metadata
    return found


SANDBOXED_PLUGINS = _discover_sandboxed_plugins()


def _version_dir(plugin_id):
    return get_latest_plugin_path(PLUGIN_GROUP, plugin_id.split(".")[-1])


@contextmanager
def _load_plugin(version_dir):
    """Imports ``plugin`` and ``tasks`` the same way the sandbox runtime does."""
    saved = {name: sys.modules.pop(name, None) for name in ("plugin", "tasks")}
    sys.path.insert(0, version_dir)
    try:
        tasks = importlib.import_module("tasks")
        yield importlib.import_module("plugin"), tasks
    finally:
        sys.path.remove(version_dir)
        sys.modules.pop("plugin", None)
        sys.modules.pop("tasks", None)
        for name, module in saved.items():
            if module is not None:
                sys.modules[name] = module


def test_the_contract_covers_every_bundled_sandboxed_plugin():
    assert set(SANDBOXED_PLUGINS) == set(TASK_CASES)


@pytest.mark.parametrize("plugin_id", sorted(TASK_CASES))
def test_plugin_is_a_task_plugin_returning_plugin_tasks(plugin_id, tmp_path):
    action_id, kwargs_factory = TASK_CASES[plugin_id]
    metadata = SANDBOXED_PLUGINS[plugin_id]

    with _load_plugin(_version_dir(plugin_id)) as (plugin_module, _tasks):
        plugin_class = getattr(plugin_module, metadata["class_name"])
        plugin = plugin_class()

        assert isinstance(plugin, TaskPlugin), (
            f"{plugin_id} still uses the legacy PluginBase/AbstractTask API"
        )

        task = plugin.create_task(action_id, **kwargs_factory(tmp_path))

        assert isinstance(task, PluginTask), (
            f"{plugin_id}.create_task({action_id!r}) returned "
            f"{type(task).__name__}, expected a PluginTask"
        )
        assert list(inspect.signature(task.run).parameters), (
            f"{plugin_id} task must receive the context as run(self, ctx)"
        )


@pytest.mark.parametrize("plugin_id", sorted(TASK_CASES))
def test_plugin_modules_do_not_use_the_legacy_task_api(plugin_id):
    version_dir = _version_dir(plugin_id)
    offenders = []

    for filename in sorted(
        name for name in os.listdir(version_dir) if name.endswith(".py")
    ):
        path = os.path.join(version_dir, filename)
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), filename=path)

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "app.plugin_system.api":
                for alias in node.names:
                    if alias.name == "AbstractTask":
                        offenders.append(f"{filename}:{node.lineno}: imports AbstractTask")

            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "self"
                and node.attr in LEGACY_ATTRIBUTES
            ):
                offenders.append(f"{filename}:{node.lineno}: self.{node.attr}")

    assert not offenders, (
        f"{plugin_id} still reaches for the legacy task state:\n  "
        + "\n  ".join(offenders)
    )
