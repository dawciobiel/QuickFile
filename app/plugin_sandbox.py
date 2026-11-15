# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Compatibility module for the sandboxed plugin runtime.

The implementation now lives in :mod:`app.plugin_system.host` (host side) and
:mod:`app.plugin_system.runtime` (plugin side). This module only re-exports the
names that the rest of the application has imported historically, so existing
imports keep working while the code has a single home.

New code should import ``SandboxedPluginWrapper`` from ``app.plugin_system.host``.
"""

from app.plugin_system.host import (  # noqa: F401
    CALL_TIMEOUT,
    SHUTDOWN_GRACE,
    STARTUP_TIMEOUT,
    SandboxedPluginWrapper,
    run_plugin_process,
)

__all__ = [
    "CALL_TIMEOUT",
    "SHUTDOWN_GRACE",
    "STARTUP_TIMEOUT",
    "SandboxedPluginWrapper",
    "run_plugin_process",
]
