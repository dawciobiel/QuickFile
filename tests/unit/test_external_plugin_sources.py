# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
External plugins have sources in the repository, but are not part of the release.

``rar_archiver`` needs a system backend and cannot ship with the application.
Its source moves to ``plugins-external/``; CI packages it and the installer puts
it in the user's external directory. The runtime must keep reading only
``plugins/``, otherwise the "external" plugin would silently become bundled
again.

Specification: ``docs/architecture/plugins/plugins.md`` ("Źródła w repozytorium").
"""

import glob
import json
import os

import pytest

import scripts.build_plugin_package as builder
from app.plugin_installer import install
from tests.plugin_helpers import get_latest_plugin_path

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SHIPPED_ROOT = os.path.join(PROJECT_ROOT, "plugins")
EXTERNAL_ROOT = os.path.join(PROJECT_ROOT, "plugins-external")
RAR_ID = "org.quickfile.rar_archiver"


def _external_sources():
    metadata_files = glob.glob(
        os.path.join(EXTERNAL_ROOT, "*", "*", "*", "metadata.json")
    )
    cases = []
    for metadata_path in sorted(metadata_files):
        with open(metadata_path, encoding="utf-8") as handle:
            cases.append((os.path.dirname(metadata_path), json.load(handle)))
    return cases


EXTERNAL_SOURCES = _external_sources()


def test_the_rar_source_lives_only_in_the_external_tree():
    external = os.path.join(
        EXTERNAL_ROOT, "org.quickfile", "rar_archiver", "1.0.4", "metadata.json"
    )
    shipped = os.path.join(SHIPPED_ROOT, "org.quickfile", "rar_archiver")

    assert os.path.isfile(external)
    assert not os.path.exists(shipped), (
        "rar_archiver must not be shipped: it needs a backend the application "
        "cannot provide"
    )


def test_the_helper_finds_external_sources():
    path = get_latest_plugin_path("org.quickfile", "rar_archiver")

    assert path.startswith(EXTERNAL_ROOT + os.sep)
    assert os.path.basename(path) == "1.0.4"


def test_every_external_source_installs_through_the_installer(tmp_path):
    install_dir = tmp_path / "plugins"
    install_dir.mkdir()
    dest = tmp_path / "plugins-external"

    assert EXTERNAL_SOURCES, "expected at least one external plugin source"

    for version_dir, metadata in EXTERNAL_SOURCES:
        result = install(version_dir, dest=dest, install_dir=install_dir)

        assert result.plugin_id == metadata["id"]
        assert result.version == metadata["version"]
        assert os.path.isfile(os.path.join(result.path, "metadata.json"))


def test_every_external_source_can_be_packaged(tmp_path):
    assert EXTERNAL_SOURCES, "expected at least one external plugin source"
    output = tmp_path / "dist"

    for version_dir, metadata in EXTERNAL_SOURCES:
        package = builder.build_package(version_dir, output)

        assert package.is_file()
        artifact_id = metadata["id"].rsplit(".", 1)[-1]
        assert package.name == f"{artifact_id}-{metadata['version']}.zip"


def test_ci_builds_packages_from_both_source_roots():
    workflow_path = os.path.join(
        PROJECT_ROOT, ".github", "workflows", "ci.yml"
    )
    with open(workflow_path, encoding="utf-8") as handle:
        workflow = handle.read()

    assert "--source-root plugins-external" in workflow
    assert "dist/plugins-external/*.zip" in workflow


def test_the_test_environment_loads_external_plugins(async_plugin_test_env):
    plugin_manager, _background_task_manager, _factory = async_plugin_test_env

    plugin = plugin_manager.get_plugin_by_id(RAR_ID)

    assert plugin is not None, (
        "the async plugin fixture must install plugins-external/ sources into "
        "an isolated external directory before creating PluginManager"
    )


@pytest.mark.parametrize(
    "version_dir,metadata",
    EXTERNAL_SOURCES,
    ids=[metadata["id"] for _path, metadata in EXTERNAL_SOURCES],
)
def test_external_metadata_is_valid(version_dir, metadata):
    assert metadata["id"] == ".".join(
        os.path.relpath(version_dir, EXTERNAL_ROOT).split(os.sep)[:2]
    )
    assert metadata["version"] == os.path.basename(version_dir)
