import importlib.util
import json
import logging
import os
import platform
import shutil
import sys
from functools import cmp_to_key

from plugins.base import StandardOperationsPlugin, ViewModePlugin, AttributeEditorPlugin, ViewerPlugin, SymlinkPlugin, ArchivePlugin, \
    ChecksumPlugin, SearchPlugin, UiExtensionPlugin, DiskUtilsPlugin


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
            "symlink": [],
            "archive": [],
            "checksum": [],
            "search": [],
            "ui_extension": [],
            "disk_utils": []
        }

        self._ensure_bundled_plugins()
        self.load_plugins()

    def _get_plugin_version(self, plugin_path):
        """Safely reads the version from a plugin's metadata.json."""
        try:
            versions = [d for d in os.listdir(plugin_path) if os.path.isdir(os.path.join(plugin_path, d))]
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

    def _compare_versions(self, v1, v2):
        """Compares two version strings (e.g., '1.0.1' > '1.0.0'). Returns True if v1 > v2."""
        try:
            p1 = tuple(map(int, v1.split('.')))
            p2 = tuple(map(int, v2.split('.')))
            return p1 > p2
        except (ValueError, TypeError):
            return False

    def _ensure_bundled_plugins(self):
        if getattr(sys, 'frozen', False):
            # If the application is run as a bundle, the PyInstaller bootloader
            # extends the sys module by a flag frozen=True and sets the app
            # path into variable _MEIPASS.
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        bundled_plugin_dir = os.path.join(base_dir, "plugins")
        user_plugin_dir = self.plugin_dirs[0]

        if not os.path.exists(user_plugin_dir):
            os.makedirs(user_plugin_dir)

        if not os.path.exists(bundled_plugin_dir):
            logging.warning(f"Bundled plugin directory not found at: {bundled_plugin_dir}")
            return

        for org_name in os.listdir(bundled_plugin_dir):
            org_path = os.path.join(bundled_plugin_dir, org_name)
            if os.path.isdir(org_path):
                for plugin_name in os.listdir(org_path):
                    bundled_path = os.path.join(org_path, plugin_name)
                    if os.path.isdir(bundled_path):
                        dest_org_path = os.path.join(user_plugin_dir, org_name)
                        dest_path = os.path.join(dest_org_path, plugin_name)

                        bundled_version = self._get_plugin_version(bundled_path)
                        if not bundled_version:
                            logging.warning(f"Skipping bundled plugin '{plugin_name}' due to missing version.")
                            continue

                        if not os.path.exists(dest_path):
                            try:
                                shutil.copytree(bundled_path, dest_path)
                                logging.info(f"Installed bundled plugin: {org_name}.{plugin_name} v{bundled_version}")
                            except Exception as e:
                                logging.error(f"Failed to install bundled plugin {plugin_name}: {e}")
                        else:
                            user_version = self._get_plugin_version(dest_path)
                            if not user_version:
                                logging.warning(f"Could not determine version of user-installed plugin '{plugin_name}'. Skipping update.")
                                continue

                            if self._compare_versions(bundled_version, user_version):
                                try:
                                    shutil.rmtree(dest_path)
                                    shutil.copytree(bundled_path, dest_path)
                                    logging.info(f"Updated bundled plugin: {org_name}.{plugin_name} from v{user_version} to v{bundled_version}")
                                except Exception as e:
                                    logging.error(f"Failed to update bundled plugin {plugin_name}: {e}")

    def load_plugins(self):
        logging.info(f"Scanning for plugins in: {', '.join(self.plugin_dirs)}")
        for plugin_dir in self.plugin_dirs:
            if not os.path.isdir(plugin_dir):
                continue
            for org_name in os.listdir(plugin_dir):
                org_path = os.path.join(plugin_dir, org_name)
                if os.path.isdir(org_path):
                    for plugin_name in os.listdir(org_path):
                        plugin_path = os.path.join(org_path, plugin_name)
                        if os.path.isdir(plugin_path):
                            self._load_plugin_versions(plugin_path)

    def _load_plugin_versions(self, plugin_path):
        versions = [d for d in os.listdir(plugin_path) if os.path.isdir(os.path.join(plugin_path, d))]
        if not versions:
            return

        versions.sort(key=lambda v: tuple(map(int, v.split('.'))), reverse=True)
        latest_version = versions[0]
        version_path = os.path.join(plugin_path, latest_version)
        metadata_path = os.path.join(version_path, "metadata.json")

        if os.path.exists(metadata_path):
            original_sys_path = sys.path[:]
            try:
                sys.path.insert(0, version_path)

                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)

                plugin_type = metadata.get("type")
                if plugin_type in self.plugins:
                    module_path = os.path.join(version_path, metadata["entry_point"])
                    spec = importlib.util.spec_from_file_location(metadata["id"], module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    plugin_class = getattr(module, metadata["class_name"])
                    plugin_instance = plugin_class()

                    self.plugins[plugin_type].append(plugin_instance)
                    logging.info(f"Successfully loaded plugin: {metadata['id']} v{metadata['version']} (type: {plugin_type})")
                else:
                    logging.warning(f"Unknown plugin type '{plugin_type}' for {metadata['id']}")

            except Exception as e:
                logging.error(f"Failed to load plugin from {version_path}: {e}", exc_info=True)
            finally:
                sys.path[:] = original_sys_path

    def get_standard_operations_plugin(self) -> StandardOperationsPlugin | None:
        if platform.system() == "Windows":
            for plugin in self.plugins["standard_operations"]:
                if "windows" in plugin.name.lower():
                    return plugin
        if self.plugins["standard_operations"]:
            return self.plugins["standard_operations"][0]
        return None

    def get_view_mode_plugin(self, view_id: str) -> ViewModePlugin | None:
        for plugin in self.plugins["view_mode"]:
            if plugin.view_mode_name == view_id:
                return plugin
        return None

    def get_attribute_editor_plugin(self, editor_id=None) -> AttributeEditorPlugin | None:
        if self.plugins["attribute_editor"]:
            return self.plugins["attribute_editor"][0]
        return None

    def get_viewer_for_file(self, file_path: str) -> ViewerPlugin | None:
        for plugin in self.plugins["viewer"]:
            if plugin.can_view(file_path):
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
