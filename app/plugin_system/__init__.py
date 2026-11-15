# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Plugin system: contracts, wire protocol, plugin-side runtime and host.

This directory needs an ``__init__.py`` even though implicit namespace
packages work at runtime: setuptools' ``find_packages`` skips directories
without one, so the wheel used to ship ``app`` without ``app.plugin_system``
(plugins could not import ``app.plugin_system.api``).
"""
