# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Bundled plugins must declare the host binaries they cannot live without.

A declaration the host cannot parse refuses the plugin at load time, and a
plugin that forgets its backend fails only in the middle of a task. Both are
shippable mistakes, so the bundled metadata is checked here.

Specification: ``docs/architecture/plugins/plugins.md`` ("Narzędzia zewnętrzne").
"""

import pytest

from app.external_tools import requirements_for
from tests.plugin_helpers import iter_plugin_metadata


def _metadata_cases():
    return list(iter_plugin_metadata())


CASES = _metadata_cases()
RAR_ID = "org.quickfile.rar_archiver"


def _metadata(plugin_id):
    return next(metadata for _, metadata in CASES if metadata["id"] == plugin_id)


def test_the_contract_covers_the_rar_plugin():
    assert RAR_ID in {metadata["id"] for _, metadata in CASES}


@pytest.mark.parametrize(
    "metadata_path,metadata", CASES, ids=[meta["id"] for _, meta in CASES]
)
def test_bundled_tool_declarations_are_valid(metadata_path, metadata):
    requirements_for(metadata)


def test_rar_accepts_every_backend_rarfile_can_use():
    (requirement,) = requirements_for(_metadata(RAR_ID))

    assert requirement.id == "rar_backend"
    assert set(requirement.executables) >= {"unrar", "unar", "bsdtar", "7z"}


def test_rar_declares_the_wrapper_package_and_the_binary_it_needs():
    metadata = _metadata(RAR_ID)

    dependencies = metadata.get("python_dependencies", [])
    assert any(dependency.split("=")[0].split(">")[0].split("<")[0] == "rarfile" for dependency in dependencies)
    assert metadata["external_tools"], (
        "rarfile is only a wrapper; the plugin must also declare the backend "
        "binary, otherwise a missing tool surfaces as a task failure"
    )
