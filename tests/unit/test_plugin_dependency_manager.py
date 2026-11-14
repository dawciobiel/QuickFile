# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Contract tests for plugin dependency handling.

The regression these tests exist for: loading a plugin used to run
``pip install`` into the plugin's ``libs`` directory. That required network
access at startup, silently changed the environment and made tests hang.
"""

import subprocess

import pytest

from app.plugin_dependency_manager import PluginDependencyManager


@pytest.fixture
def manager():
    return PluginDependencyManager()


def forbid_pip(monkeypatch):
    """Make any subprocess call fail loudly."""

    def _boom(*args, **kwargs):
        raise AssertionError("plugin dependency check must never run a subprocess")

    monkeypatch.setattr(subprocess, "run", _boom)


def test_plugin_without_dependencies_is_satisfied(manager, tmp_path):
    status = manager.check_dependencies(str(tmp_path), {})

    assert status.satisfied is True
    assert status.libs_dir is None
    assert status.missing == []


def test_host_provided_dependency_is_satisfied(manager, tmp_path):
    """PyQt6 is always available: the host is a Qt application."""
    status = manager.check_dependencies(
        str(tmp_path), {"python_dependencies": ["PyQt6"]}
    )

    assert status.satisfied is True
    assert status.libs_dir is None
    assert status.missing == []


def test_checking_dependencies_never_runs_pip(manager, tmp_path, monkeypatch):
    forbid_pip(monkeypatch)

    status = manager.check_dependencies(
        str(tmp_path), {"python_dependencies": ["quickfile-missing-testdep"]}
    )

    assert status.satisfied is False
    assert status.missing == ["quickfile-missing-testdep"]


def test_dependency_installed_in_libs_is_satisfied(manager, tmp_path):
    libs = tmp_path / "libs"
    (libs / "quickfile-testdep-1.0.dist-info").mkdir(parents=True)

    status = manager.check_dependencies(
        str(tmp_path), {"python_dependencies": ["quickfile-testdep"]}
    )

    assert status.satisfied is True
    assert status.libs_dir == str(libs)
    assert status.missing == []


def test_install_is_not_triggered_when_dependencies_are_satisfied(
    manager, tmp_path, monkeypatch
):
    forbid_pip(monkeypatch)

    assert manager.install_dependencies(str(tmp_path), {"python_dependencies": ["PyQt6"]})


def test_requirement_specifiers_are_understood(manager, tmp_path):
    libs = tmp_path / "libs"
    (libs / "quickfile-testdep-2.1.dist-info").mkdir(parents=True)

    status = manager.check_dependencies(
        str(tmp_path), {"python_dependencies": ["quickfile-testdep>=2.0"]}
    )

    assert status.satisfied is True
