# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Contract tests for plugin dependency handling.

The regression these tests exist for: loading a plugin used to run
``pip install`` into the plugin's ``libs`` directory. That required network
access at startup, silently changed the environment and made tests hang.

Installation is now an explicit, offline action driven by a hashed lock file
and a local wheel directory. Version specifiers are checked against the host
and the plugin's own ``libs`` directory, not just the distribution name.
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


def write_dist_info(libs, name, version):
    """Create the metadata pip would leave after installing into ``libs``."""
    info = libs / f"{name.replace('-', '_')}-{version}.dist-info"
    info.mkdir(parents=True, exist_ok=True)
    (info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n",
        encoding="utf-8",
    )
    return info


def write_lock(plugin_path, lines):
    (plugin_path / "requirements.lock").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


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
    write_dist_info(libs, "quickfile-testdep", "1.0")

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
    write_dist_info(libs, "quickfile-testdep", "2.1")

    status = manager.check_dependencies(
        str(tmp_path), {"python_dependencies": ["quickfile-testdep>=2.0"]}
    )

    assert status.satisfied is True


def test_a_libs_version_that_does_not_match_the_specifier_is_missing(manager, tmp_path):
    libs = tmp_path / "libs"
    write_dist_info(libs, "quickfile-testdep", "1.0")

    status = manager.check_dependencies(
        str(tmp_path), {"python_dependencies": ["quickfile-testdep>=2.0"]}
    )

    assert status.satisfied is False
    assert status.missing == ["quickfile-testdep>=2.0"]


def test_the_host_version_must_match_the_specifier(manager, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.plugin_dependency_manager.importlib_metadata.version",
        lambda name: "1.0",
    )

    status = manager.check_dependencies(
        str(tmp_path), {"python_dependencies": ["quickfile-hostdep>=2.0"]}
    )

    assert status.satisfied is False
    assert status.missing == ["quickfile-hostdep>=2.0"]


def test_python_import_names_can_identify_a_module_without_distribution_metadata(
    manager, tmp_path, monkeypatch
):
    (tmp_path / "quickfile_import_only.py").write_text("", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    status = manager.check_dependencies(
        str(tmp_path),
        {
            "python_dependencies": ["quickfile-import-only"],
            "python_import_names": {"quickfile-import-only": "quickfile_import_only"},
        },
    )

    assert status.satisfied is True
    assert status.libs_dir is None


def test_an_import_name_does_not_satisfy_a_version_specifier(manager, tmp_path, monkeypatch):
    (tmp_path / "quickfile_import_only.py").write_text("", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    status = manager.check_dependencies(
        str(tmp_path),
        {
            "python_dependencies": ["quickfile-import-only>=2.0"],
            "python_import_names": {"quickfile-import-only": "quickfile_import_only"},
        },
    )

    assert status.satisfied is False
    assert status.missing == ["quickfile-import-only>=2.0"]


def test_lockfile_pins_override_broad_metadata_requirements(manager, tmp_path):
    libs = tmp_path / "libs"
    write_dist_info(libs, "quickfile-testdep", "2.5")
    write_lock(tmp_path, ["quickfile-testdep==1.0 --hash=sha256:" + "a" * 64])

    status = manager.check_dependencies(
        str(tmp_path), {"python_dependencies": ["quickfile-testdep>=2.0"]}
    )

    assert status.satisfied is False
    assert status.missing == ["quickfile-testdep==1.0"]


def test_lockfile_must_cover_every_declared_dependency(manager, tmp_path):
    write_lock(tmp_path, ["quickfile-testdep==1.0 --hash=sha256:" + "a" * 64])

    with pytest.raises(ValueError, match="does not cover"):
        manager.check_dependencies(
            str(tmp_path),
            {"python_dependencies": ["quickfile-testdep", "quickfile-other"]},
        )


def test_install_requires_a_lockfile_and_local_wheels(manager, tmp_path, monkeypatch):
    forbid_pip(monkeypatch)

    installed = manager.install_dependencies(
        str(tmp_path), {"python_dependencies": ["quickfile-testdep"]}
    )

    assert installed is False


def test_install_uses_only_local_wheels_and_hashes(manager, tmp_path, monkeypatch):
    write_lock(tmp_path, ["quickfile-testdep==1.0 --hash=sha256:" + "a" * 64])
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    (wheels / "quickfile_testdep-1.0-py3-none-any.whl").write_bytes(b"")

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(
        "app.plugin_dependency_manager.importlib.util.find_spec",
        lambda name: object() if name == "pip" else None,
    )

    installed = manager.install_dependencies(
        str(tmp_path), {"python_dependencies": ["quickfile-testdep"]}
    )

    assert installed is True
    cmd = calls[0][0]
    assert cmd[1:4] == ["-m", "pip", "install"]
    assert "--no-index" in cmd
    assert "--require-hashes" in cmd
    assert "--find-links" in cmd
    assert str(wheels) in cmd
    assert str(tmp_path / "requirements.lock") in cmd
    assert str(tmp_path / "libs") in cmd
