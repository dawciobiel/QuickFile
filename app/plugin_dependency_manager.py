# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import importlib.util
import logging
import os
import re
import subprocess
import sys
from typing import Dict, List, NamedTuple, Optional


class DependencyStatus(NamedTuple):
    """Result of a plugin dependency check."""

    satisfied: bool
    libs_dir: Optional[str]  # directory that must be added to sys.path, if any
    missing: List[str]  # dependencies that could not be found anywhere


class PluginDependencyManager:
    """
    Verifies plugin dependencies declared in ``metadata.json``.

    Loading a plugin never installs anything. Installing dependencies on the
    fly means the application silently rewrites its own environment, requires
    network access at startup and makes bug reports unreproducible. Installation
    is an explicit action (``install_dependencies``), triggered by the user or
    by the plugin installer.

    Dependencies that the host application already provides (for example PyQt6,
    which a Qt application always has) are treated as satisfied and never
    installed.
    """

    def __init__(self):
        self.logger = logging.getLogger("PluginDependencyManager")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def check_dependencies(self, plugin_path: str, metadata: Dict) -> DependencyStatus:
        """
        Check whether the dependencies declared in metadata are available.

        Never touches the network and never runs pip.
        """
        dependencies = metadata.get("python_dependencies", [])
        if not dependencies:
            return DependencyStatus(True, None, [])

        libs_dir = os.path.join(plugin_path, "libs")

        missing_from_host = [dep for dep in dependencies if not self._is_available(dep)]
        if not missing_from_host:
            # Everything is provided by the host interpreter.
            return DependencyStatus(True, None, [])

        installed_in_libs = self._installed_in_libs(libs_dir)
        missing = [dep for dep in missing_from_host if not self._matches(dep, installed_in_libs)]

        if not missing:
            return DependencyStatus(True, libs_dir, [])

        return DependencyStatus(False, libs_dir if os.path.isdir(libs_dir) else None, missing)

    def install_dependencies(self, plugin_path: str, metadata: Dict) -> bool:
        """
        Install missing dependencies into ``<plugin>/libs`` using pip.

        This is an explicit action and must not be called while loading plugins.
        """
        status = self.check_dependencies(plugin_path, metadata)
        if status.satisfied:
            return True

        libs_dir = os.path.join(plugin_path, "libs")
        self.logger.info(
            "Installing dependencies for plugin at %s: %s", plugin_path, ", ".join(status.missing)
        )
        return self._pip_install(libs_dir, status.missing)

    # ------------------------------------------------------------------
    # Backwards compatibility
    # ------------------------------------------------------------------
    def ensure_dependencies(self, plugin_path: str, metadata: Dict) -> Optional[str]:
        """
        Deprecated: kept for callers that only need the libs path.

        Unlike the old implementation this never installs anything; use
        ``install_dependencies`` for that.
        """
        status = self.check_dependencies(plugin_path, metadata)
        if not status.satisfied:
            self.logger.warning(
                "Plugin at %s is missing dependencies: %s",
                plugin_path,
                ", ".join(status.missing),
            )
        return status.libs_dir

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    @staticmethod
    def _dependency_name(dependency: str) -> str:
        """Extract the bare distribution name from a requirement string."""
        return re.split(r"[<>=!~\[; ]", dependency, maxsplit=1)[0].strip()

    @staticmethod
    def _is_available(dependency: str) -> bool:
        """True if the current interpreter can import the dependency."""
        name = PluginDependencyManager._dependency_name(dependency)
        try:
            return importlib.util.find_spec(name) is not None
        except (ImportError, ValueError, ModuleNotFoundError):
            return False

    @staticmethod
    def _installed_in_libs(libs_dir: str) -> List[str]:
        """Return distribution names found in a ``libs`` directory."""
        if not os.path.isdir(libs_dir):
            return []
        names = []
        for entry in os.listdir(libs_dir):
            if entry.endswith(".dist-info"):
                # "requests-2.32.5.dist-info" -> "requests"
                names.append(entry[: -len(".dist-info")].rsplit("-", 1)[0])
        return names

    @staticmethod
    def _matches(dependency: str, installed: List[str]) -> bool:
        wanted = PluginDependencyManager._normalize(dependency)
        return any(
            PluginDependencyManager._normalize(name) == wanted for name in installed
        )

    @staticmethod
    def _normalize(name: str) -> str:
        """Normalize a distribution name the way PEP 503 does."""
        return (
            PluginDependencyManager._dependency_name(name)
            .lower()
            .replace("_", "-")
            .replace(".", "-")
        )

    def _pip_install(self, target_dir: str, dependencies: List[str]) -> bool:
        os.makedirs(target_dir, exist_ok=True)

        try:
            import pip  # noqa: F401
        except ImportError:
            self.logger.error(
                "Cannot install plugin dependencies: pip is not available in this "
                "interpreter. Install them manually: %s",
                " ".join(dependencies),
            )
            return False

        cmd = [sys.executable, "-m", "pip", "install", "--target", target_dir] + dependencies

        try:
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.logger.debug("Pip output: %s", result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error("Pip installation failed: %s", e.stderr)
            return False
        except OSError as e:
            self.logger.error("Unexpected error during dependency installation: %s", e)
            return False
