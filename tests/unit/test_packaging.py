# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Packaging guards.

``app/plugin_system`` used to be an implicit namespace package (no
``__init__.py``). That works when running from a checkout, but setuptools'
``find_packages`` skips such directories, so the wheel shipped ``app`` without
``app.plugin_system`` and every plugin failed to import
``app.plugin_system.api``. The directory now has an ``__init__.py``; this test
keeps it from disappearing again.
"""

from setuptools import find_packages


def test_plugin_system_is_discovered_as_a_package():
    packages = set(find_packages(include=["app*"]))

    assert "app.plugin_system" in packages


def test_every_application_subpackage_is_discoverable():
    """Folders under app/ that contain modules must be real packages."""
    import os

    import app

    app_dir = os.path.dirname(app.__file__)
    expected = {
        f"app.{name}"
        for name in os.listdir(app_dir)
        if os.path.isdir(os.path.join(app_dir, name))
        and not name.startswith("__")
        and any(
            entry.endswith(".py")
            for entry in os.listdir(os.path.join(app_dir, name))
        )
    }

    assert expected <= set(find_packages(include=["app*"]))
