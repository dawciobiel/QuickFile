# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import importlib.util
from importlib import metadata as importlib_metadata
import logging
import os
import subprocess
import sys
from typing import Dict, List, NamedTuple, Optional

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion


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
    is an explicit, offline action (``install_dependencies``) driven by a hashed
    lock file and local wheels.

    Requirements are checked against the host interpreter and the plugin's own
    ``libs`` directory. A version specifier (``>=2.0``, ``==1.2``) is enforced,
    not just the distribution name. Dependencies that the host application
    already provides (for example PyQt6, which a Qt application always has) are
    treated as satisfied and never installed.
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
        libs_dir = os.path.join(plugin_path, "libs")
        declared = metadata.get("python_dependencies", [])
        if not declared and not os.path.isfile(self._lock_path(plugin_path, metadata)):
            return DependencyStatus(True, None, [])

        requirements = self._requirements(plugin_path, metadata)
        libs_versions = self._libs_versions(libs_dir)
        import_names = {
            canonicalize_name(name): module
            for name, module in metadata.get("python_import_names", {}).items()
        }

        missing = []
        needs_libs = False

        for requirement in requirements:
            if self._version_satisfies(self._host_version(requirement.name), requirement):
                continue

            libs_version = libs_versions.get(canonicalize_name(requirement.name))
            if self._version_satisfies(libs_version, requirement):
                needs_libs = True
                continue

            # Single-file modules have no distribution metadata, so an explicit
            # distribution -> module map is the only way to see them. It cannot
            # prove a version, so it only satisfies unpinned requirements.
            if not requirement.specifier:
                module_name = import_names.get(
                    canonicalize_name(requirement.name), requirement.name
                )
                if self._module_available(module_name):
                    continue

            missing.append(str(requirement))

        satisfied = not missing
        return DependencyStatus(
            satisfied,
            libs_dir if needs_libs and os.path.isdir(libs_dir) else None,
            missing,
        )

    def install_dependencies(self, plugin_path: str, metadata: Dict) -> bool:
        """
        Install missing dependencies into ``<plugin>/libs``, offline.

        The plugin must ship a fully resolved, hashed lock file and the wheels
        it references. This is an explicit action and must not be called while
        loading plugins.
        """
        status = self.check_dependencies(plugin_path, metadata)
        if status.satisfied:
            return True

        if not metadata.get("sandboxed", False):
            self.logger.error(
                "Cannot install dependencies for plugin %s: it is not sandboxed. "
                "A plugin that needs libs must run in a separate process.",
                metadata.get("id", "<unknown>"),
            )
            return False

        lock_path = self._lock_path(plugin_path, metadata)
        wheels_dir = self._wheels_dir(plugin_path, metadata)

        if not os.path.isfile(lock_path):
            self.logger.error(
                "Cannot install plugin dependencies: %s does not exist. "
                "Ship a hashed lock file with the plugin.",
                lock_path,
            )
            return False

        if not self._has_wheels(wheels_dir):
            self.logger.error(
                "Cannot install plugin dependencies: no wheels in %s. "
                "Plugins must ship their wheels; installation never uses the network.",
                wheels_dir,
            )
            return False

        libs_dir = os.path.join(plugin_path, "libs")
        self.logger.info(
            "Installing dependencies for plugin at %s: %s",
            plugin_path,
            ", ".join(status.missing),
        )
        return self._pip_install(libs_dir, lock_path, wheels_dir)

    # ------------------------------------------------------------------
    # Isolation
    # ------------------------------------------------------------------
    @staticmethod
    def validate_isolation(status: DependencyStatus, metadata: Dict) -> None:
        """Reject a non-sandboxed plugin that needs libraries from ``libs``.

        A separate process gives the plugin its own ``sys.path``. A plugin
        loaded into the host would share the host's imports, so its pinned
        dependencies could not be isolated.
        """
        if status.libs_dir and not metadata.get("sandboxed", False):
            raise ValueError(
                f"Plugin {metadata.get('id', '<unknown>')} needs dependencies from "
                "its libs directory but is not sandboxed; isolated dependencies "
                "require a separate process."
            )

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
    # Requirements and metadata
    # ------------------------------------------------------------------
    def _requirements(self, plugin_path: str, metadata: Dict) -> List[Requirement]:
        """Return the requirements to verify, using lock pins when present."""
        declared = []
        for dependency in metadata.get("python_dependencies", []):
            try:
                declared.append(Requirement(dependency))
            except InvalidRequirement as error:
                raise ValueError(
                    f"Invalid python dependency {dependency!r} in metadata: {error}"
                ) from error

        locked = self._locked_requirements(plugin_path, metadata)
        if locked is None:
            return declared

        locked_names = {canonicalize_name(requirement.name) for requirement in locked}
        uncovered = [
            str(requirement)
            for requirement in declared
            if canonicalize_name(requirement.name) not in locked_names
        ]
        if uncovered:
            raise ValueError(
                "Dependency lock file does not cover every declared dependency: "
                + ", ".join(uncovered)
            )

        return locked

    def _locked_requirements(
        self, plugin_path: str, metadata: Dict
    ) -> Optional[List[Requirement]]:
        """Parse the plugin's hashed requirements lock, or return None."""
        lock_path = self._lock_path(plugin_path, metadata)
        if not os.path.isfile(lock_path):
            return None

        requirements = []
        with open(lock_path, encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.split("#", 1)[0].strip()
                if not line or line.startswith("-"):
                    continue

                requirement_text = line.split(" --hash=", 1)[0].strip()
                try:
                    requirement = Requirement(requirement_text)
                except InvalidRequirement as error:
                    raise ValueError(
                        f"{lock_path}:{line_number}: invalid requirement "
                        f"{requirement_text!r}: {error}"
                    ) from error

                if requirement.marker is not None and not requirement.marker.evaluate():
                    continue

                requirements.append(requirement)

        if not requirements:
            raise ValueError(f"{lock_path}: lock file contains no requirements")

        return requirements

    def _lock_path(self, plugin_path: str, metadata: Dict) -> str:
        return self._plugin_relative_path(
            plugin_path, metadata.get("dependency_lock", "requirements.lock")
        )

    def _wheels_dir(self, plugin_path: str, metadata: Dict) -> str:
        return self._plugin_relative_path(
            plugin_path, metadata.get("dependency_wheels", "wheels")
        )

    @staticmethod
    def _plugin_relative_path(plugin_path: str, relative_path: str) -> str:
        """Resolve a metadata path, refusing to escape the plugin directory."""
        root = os.path.abspath(plugin_path)
        resolved = os.path.abspath(os.path.join(root, relative_path))
        if os.path.commonpath([root, resolved]) != root:
            raise ValueError(
                f"Plugin dependency path {relative_path!r} leaves the plugin directory"
            )
        return resolved

    @staticmethod
    def _host_version(distribution: str) -> Optional[str]:
        try:
            return importlib_metadata.version(distribution)
        except (importlib_metadata.PackageNotFoundError, ValueError):
            return None

    @staticmethod
    def _libs_versions(libs_dir: str) -> Dict[str, str]:
        """Map canonical distribution names to versions installed in ``libs``."""
        if not os.path.isdir(libs_dir):
            return {}

        versions = {}
        try:
            distributions = importlib_metadata.distributions(path=[libs_dir])
            for distribution in distributions:
                metadata = distribution.metadata
                name = metadata.get("Name") if metadata is not None else None
                if name and distribution.version:
                    versions[canonicalize_name(name)] = distribution.version
        except (OSError, ValueError):
            logging.getLogger("PluginDependencyManager").warning(
                "Could not read installed distribution metadata from %s",
                libs_dir,
                exc_info=True,
            )
        return versions

    @staticmethod
    def _version_satisfies(version: Optional[str], requirement: Requirement) -> bool:
        if version is None:
            return False
        if not requirement.specifier:
            return True
        try:
            return requirement.specifier.contains(version, prereleases=True)
        except InvalidVersion:
            return False

    @staticmethod
    def _module_available(module_name: str) -> bool:
        try:
            return importlib.util.find_spec(module_name) is not None
        except (ImportError, ValueError, ModuleNotFoundError):
            return False

    @staticmethod
    def _has_wheels(wheels_dir: str) -> bool:
        if not os.path.isdir(wheels_dir):
            return False
        return any(name.endswith(".whl") for name in os.listdir(wheels_dir))

    # ------------------------------------------------------------------
    # Installation
    # ------------------------------------------------------------------
    def _pip_install(self, target_dir: str, lock_path: str, wheels_dir: str) -> bool:
        if importlib.util.find_spec("pip") is None:
            self.logger.error(
                "Cannot install plugin dependencies: pip is not available in this "
                "interpreter. Install the wheels from %s manually into %s.",
                wheels_dir,
                target_dir,
            )
            return False

        os.makedirs(target_dir, exist_ok=True)

        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-cache-dir",
            "--find-links",
            wheels_dir,
            "--require-hashes",
            "--target",
            target_dir,
            "-r",
            lock_path,
        ]

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
