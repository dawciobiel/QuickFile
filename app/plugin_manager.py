# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import importlib
import importlib.util
import hashlib
import json
import logging
import os
import platform
import re
import shutil
import sys
import tempfile

from app.plugin_dependency_manager import PluginDependencyManager
from app.plugin_sandbox import SandboxedPluginWrapper  # Import the new wrapper
from plugins.base import StandardOperationsPlugin, ViewModePlugin, AttributeEditorPlugin, ViewerPlugin, SymlinkPlugin, \
    ArchivePlugin, \
    ChecksumPlugin, SearchPlugin, UiExtensionPlugin, DiskUtilsPlugin, EditorPlugin, MenuActionPlugin


class PluginManager:
    def __init__(self, plugin_dirs=None):
        if plugin_dirs is None:
            user_config_dir = os.path.expanduser("~/.config/QuickFile")
            plugin_dirs = [os.path.join(user_config_dir, "plugins")]

        self.plugin_dirs = plugin_dirs
        self.plugins = {
            "standard_operations": [],
            "view_mode": [],
            "attribute_editor": [],
            "viewer": [],
            "editor": [],
            "symlink": [],
            "archive": [],
            "checksum": [],
            "search": [],
            "ui_extension": [],
            "disk_utils": [],
            "menu_action": [],
            "directory_size": [],
        }
        self.version_regex = re.compile(r"^\d+(\.\d+)*$")
        self.dependency_manager = PluginDependencyManager()

        self._ensure_bundled_plugins()
        self.load_plugins()

    def _is_version_dir(self, dir_name: str) -> bool:
        """Checks if a directory name matches the version format."""
        return self.version_regex.match(dir_name) is not None

    def _get_plugin_version(self, plugin_path):
        """Safely reads the version from a plugin's metadata.json."""
        try:
            versions = [d for d in os.listdir(plugin_path) if os.path.isdir(os.path.join(plugin_path, d)) and self._is_version_dir(d)]
            if not versions:
                return None
            latest_version_dir = sorted(versions, key=lambda v: tuple(map(int, v.split('.'))), reverse=True)[0]
            metadata_path = os.path.join(plugin_path, latest_version_dir, "metadata.json")
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            return metadata.get("version")
        except (IOError, json.JSONDecodeError, IndexError, ValueError) as e:
            logging.warning(f"Could not read version from plugin at {plugin_path}: {e}")
            return None

    _TREE_IGNORED_DIRS = {"__pycache__", "libs"}

    def _tree_fingerprint(self, root):
        """Map every bundled file to a content hash, ignoring build/venv leftovers."""
        fingerprint = {}
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in self._TREE_IGNORED_DIRS]
            for filename in filenames:
                if filename.endswith(".pyc"):
                    continue
                absolute = os.path.join(dirpath, filename)
                relative = os.path.relpath(absolute, root)
                with open(absolute, "rb") as handle:
                    fingerprint[relative] = hashlib.sha256(handle.read()).hexdigest()
        return fingerprint

    def _tree_matches(self, source, target):
        if not os.path.isdir(target):
            return False
        return self._tree_fingerprint(source) == self._tree_fingerprint(target)

    @staticmethod
    def _copy_preserving_libs(source, target):
        """Replace ``target`` with ``source`` but keep installed ``libs/``.

        ``libs/`` lives inside a version directory, so every occurrence in the
        tree has to be preserved, not just one at the plugin root. Libraries of
        a version that the new copy no longer ships are dropped: keeping them
        would leave dead code and stale dependencies behind after an upgrade.
        """
        with tempfile.TemporaryDirectory() as staging:
            preserved = []
            if os.path.isdir(target):
                for dirpath, dirnames, _ in os.walk(target):
                    if os.path.basename(dirpath) == "libs":
                        relative = os.path.relpath(dirpath, target)
                        owner = os.path.dirname(relative)
                        dirnames[:] = []  # do not descend into installed dependencies
                        if owner and not os.path.isdir(os.path.join(source, owner)):
                            continue
                        staged = os.path.join(staging, relative)
                        os.makedirs(os.path.dirname(staged), exist_ok=True)
                        shutil.copytree(dirpath, staged)
                        preserved.append(relative)

            if os.path.exists(target):
                shutil.rmtree(target)
            shutil.copytree(source, target)

            for relative in preserved:
                destination = os.path.join(target, relative)
                if os.path.exists(destination):
                    shutil.rmtree(destination)
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                shutil.copytree(os.path.join(staging, relative), destination)

    def _ensure_bundled_plugins(self):
        if getattr(sys, 'frozen', False):
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        bundled_plugin_dir = os.path.join(base_dir, "plugins")
        user_plugin_dir = self.plugin_dirs[0]

        if not os.path.exists(user_plugin_dir):
            os.makedirs(user_plugin_dir)

        if not os.path.exists(bundled_plugin_dir):
            logging.warning(f"Bundled plugin directory not found at: {bundled_plugin_dir}")
            return

        self._sync_bundled_plugin_dirs(bundled_plugin_dir, user_plugin_dir)

    def _sync_bundled_plugin_dirs(self, bundled_plugin_dir, user_plugin_dir):
        """Make every bundled plugin in the user directory match the shipped one."""
        for org_name in os.listdir(bundled_plugin_dir):
            org_path = os.path.join(bundled_plugin_dir, org_name)
            if not os.path.isdir(org_path) or org_name == "__pycache__":
                continue
            for plugin_name in os.listdir(org_path):
                bundled_path = os.path.join(org_path, plugin_name)
                if not os.path.isdir(bundled_path):
                    continue

                dest_org_path = os.path.join(user_plugin_dir, org_name)
                os.makedirs(dest_org_path, exist_ok=True)
                dest_path = os.path.join(dest_org_path, plugin_name)

                bundled_version = self._get_plugin_version(bundled_path)
                if not bundled_version:
                    logging.warning(f"Skipping bundled plugin '{plugin_name}' due to missing version.")
                    continue

                # Content, not version numbers, decides whether the installed copy
                # is up to date. Two releases can share a version number but
                # differ in content (the architecture-v3 refactor did exactly
                # that), and a "newer" user copy may be broken.
                if self._tree_matches(bundled_path, dest_path):
                    continue

                try:
                    was_installed = os.path.exists(dest_path)
                    self._copy_preserving_libs(bundled_path, dest_path)
                    if was_installed:
                        logging.info(
                            "Refreshed bundled plugin: %s.%s v%s",
                            org_name, plugin_name, bundled_version,
                        )
                    else:
                        logging.info(
                            "Installed bundled plugin: %s.%s v%s",
                            org_name, plugin_name, bundled_version,
                        )
                except OSError as e:
                    logging.error(f"Failed to install bundled plugin {plugin_name}: {e}")

    def load_plugins(self):
        logging.info(f"Scanning for plugins in: {', '.join(self.plugin_dirs)}")
        for plugin_dir in self.plugin_dirs:
            if not os.path.isdir(plugin_dir):
                continue
            for org_name in os.listdir(plugin_dir):
                org_path = os.path.join(plugin_dir, org_name)
                if os.path.isdir(org_path) and org_name != "__pycache__":
                    for plugin_name in os.listdir(org_path):
                        plugin_path = os.path.join(org_path, plugin_name)
                        if os.path.isdir(plugin_path):
                            self._load_plugin_versions(plugin_path)

    def _load_plugin_versions(self, plugin_path):
        versions = [d for d in os.listdir(plugin_path) if os.path.isdir(os.path.join(plugin_path, d)) and self._is_version_dir(d)]
        if not versions:
            return

        versions.sort(key=lambda v: tuple(map(int, v.split('.'))), reverse=True)
        latest_version = versions[0]
        logging.debug(f"For plugin {os.path.basename(plugin_path)}, latest version found: {latest_version}")
        version_path = os.path.join(plugin_path, latest_version)
        metadata_path = os.path.join(version_path, "metadata.json")

        if os.path.exists(metadata_path):
            self._load_plugin_from_path(version_path, metadata_path)

    def _load_plugin_from_path(self, base_path, metadata_path):
        original_sys_path = sys.path[:]
        plugin_instance = None  # Initialize plugin_instance
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            # Verify dependencies without installing anything. A missing
            # dependency is reported, but the plugin is still loaded: PyQt6 and
            # other host-provided packages are always available anyway.
            dependency_status = self.dependency_manager.check_dependencies(base_path, metadata)
            self.dependency_manager.validate_isolation(dependency_status, metadata)
            if dependency_status.libs_dir:
                sys.path.insert(0, dependency_status.libs_dir)
            if not dependency_status.satisfied:
                logging.warning(
                    "Plugin %s is missing dependencies: %s. Install them explicitly, "
                    "QuickFile will not run pip during startup.",
                    metadata.get("id"),
                    ", ".join(dependency_status.missing),
                )

            sys.path.insert(0, base_path)

            # Check platform compatibility
            if "platforms" in metadata:
                current_platform = platform.system().lower()
                supported_platforms = [p.lower() for p in metadata["platforms"]]
                
                # Handle macOS alias
                if current_platform == "darwin" and "macos" in supported_platforms:
                    current_platform = "macos"
                
                if current_platform not in supported_platforms:
                    logging.debug(f"Skipping plugin {metadata.get('id')} as it is not supported on {platform.system()}. Supported: {supported_platforms}")
                    return

            plugin_type = metadata.get("type")
            if plugin_type in self.plugins:
                entry_point = metadata["entry_point"]
                module_name, class_name = entry_point.split(":")

                if metadata.get("sandboxed", False):
                    logging.info(f"Loading plugin {metadata['id']} in sandbox mode.")
                    plugin_instance = SandboxedPluginWrapper(base_path, metadata)
                    plugin_instance.start()
                    if not plugin_instance.is_ready():
                        # Do not register a dead plugin: every later call on the
                        # wrapper would raise AttributeError and crash the UI.
                        logging.error(
                            "Plugin %s could not be started and will not be registered.",
                            metadata["id"],
                        )
                        plugin_instance.stop()
                        return
                else:
                    module_file_path = os.path.join(base_path, module_name.replace('.', os.sep) + '.py')

                    spec = importlib.util.spec_from_file_location(metadata["id"], module_file_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    plugin_class = getattr(module, class_name)
                    plugin_instance = plugin_class()

                    # Store metadata and module name for direct plugins
                    plugin_instance.__module_name__ = module.__name__
                    plugin_instance.metadata = metadata

                self.plugins[plugin_type].append(plugin_instance)
                logging.info(f"Successfully loaded plugin: {metadata['id']} v{metadata.get('version', 'N/A')} (type: {plugin_type})")
            else:
                logging.warning(f"Unknown plugin type '{plugin_type}' for {metadata['id']}")

        except Exception as e:
            logging.error(f"Failed to load plugin from {base_path}: {e}", exc_info=True)
            if isinstance(plugin_instance, SandboxedPluginWrapper):
                plugin_instance.stop()  # Ensure sandbox process is stopped on error
        finally:
            sys.path[:] = original_sys_path

    def shutdown(self):
        """
        Shuts down all sandboxed plugin processes.
        """
        logging.info("Shutting down plugin processes...")
        for plugin_type_list in self.plugins.values():
            for plugin_instance in plugin_type_list:
                if isinstance(plugin_instance, SandboxedPluginWrapper):
                    plugin_instance.stop()
                    logging.info(f"Stopped sandboxed plugin: {plugin_instance.metadata.get('id')}")

    def get_plugin_by_id(self, plugin_id: str):
        """
        Finds a loaded plugin instance by its ID.
        """
        for plugin_type_list in self.plugins.values():
            for plugin_instance in plugin_type_list:
                if hasattr(plugin_instance, 'metadata') and plugin_instance.metadata.get('id') == plugin_id:
                    return plugin_instance
        return None

    def get_standard_operations_plugin(self) -> StandardOperationsPlugin | None:
        if platform.system() == "Windows":
            for plugin in self.plugins["standard_operations"]:
                if "windows" in plugin.get_name().lower(): # Użyj get_name()
                    return plugin
        
        # On non-Windows systems, prefer plugins that don't have "windows" in the name
        for plugin in self.plugins["standard_operations"]:
            if "windows" not in plugin.get_name().lower(): # Użyj get_name()
                return plugin

        if self.plugins["standard_operations"]:
            return self.plugins["standard_operations"][0]
        return None

    def get_view_mode_plugin(self, view_id: str) -> ViewModePlugin | None:
        logging.debug(f"Searching for view mode plugin with id: {view_id}")
        logging.debug(f"Available view_mode plugins: {self.plugins['view_mode']}")
        for plugin in self.plugins["view_mode"]:
            try:
                plugin_view_id = plugin.get_view_mode_name()
                logging.debug(f"Checking plugin: {plugin.get_name()}, view_id: {plugin_view_id}")
                if plugin_view_id == view_id:
                    logging.debug(f"Found matching plugin: {plugin.get_name()}")
                    return plugin
            except Exception as e:
                logging.error(f"Error getting view_mode_name from plugin {plugin}: {e}")
        logging.warning(f"View mode plugin with id '{view_id}' not found.")
        return None

    def get_attribute_editor_plugin(self, editor_id=None) -> AttributeEditorPlugin | None:
        if self.plugins["attribute_editor"]:
            return self.plugins["attribute_editor"][0]
        return None

    def get_viewer_for_file(self, file_path: str) -> ViewerPlugin | None:
        for plugin in self.plugins["viewer"]:
            if plugin.can_view(file_path):
                # Force reload the plugin's module to ensure we have the latest code
                if hasattr(plugin, '__module_name__') and plugin.__module_name__ in sys.modules:
                    try:
                        importlib.reload(sys.modules[plugin.__module_name__])
                        # We need to find the class again in the reloaded module
                        # and create a new instance. This is tricky because we don't know the class name here.
                        # For now, we'll just reload and hope the existing instance picks up changes if possible.
                        # A better implementation would re-instantiate the plugin.
                        logging.debug(f"Reloaded module: {plugin.__module_name__}")
                    except Exception as e:
                        logging.error(f"Failed to reload plugin module {plugin.__module_name__}: {e}")
                return plugin
        return None
        
    def get_editor_for_file(self, file_path: str) -> EditorPlugin | None:
        for plugin in self.plugins["editor"]:
            if plugin.can_handle(file_path):
                return plugin
        return None

    def get_symlink_plugin(self) -> SymlinkPlugin | None:
        if self.plugins["symlink"]:
            return self.plugins["symlink"][0]
        return None

    def get_archiver_for_extension(self, extension: str) -> ArchivePlugin | None:
        for plugin in self.plugins["archive"]:
            if extension in plugin.get_supported_extensions():
                return plugin
        return None

    def get_all_archivers(self) -> list[ArchivePlugin]:
        return self.plugins["archive"]

    def get_checksum_plugins(self) -> list[ChecksumPlugin]:
        return self.plugins["checksum"]

    def get_search_plugins(self) -> list[SearchPlugin]:
        return self.plugins["search"]

    def get_ui_extension_plugins(self) -> list[UiExtensionPlugin]:
        return self.plugins["ui_extension"]

    def get_disk_utils_plugin(self) -> DiskUtilsPlugin | None:
        if self.plugins["disk_utils"]:
            return self.plugins["disk_utils"][0]
        return None

    def get_menu_action_plugins(self) -> list[MenuActionPlugin]:
        return self.plugins["menu_action"]
