import importlib.util
import json
import logging
import os
import platform
import shutil
import sys

from plugins.base import StandardOperationsPlugin, ViewModePlugin, AttributeEditorPlugin, ViewerPlugin, SymlinkPlugin, ArchivePlugin, \
    ChecksumPlugin, SearchPlugin, UiExtensionPlugin


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
            "ui_extension": []
        }

        self._ensure_bundled_plugins()
        self.load_plugins()

    def _ensure_bundled_plugins(self):
        bundled_plugin_dir = os.path.join(os.path.dirname(__file__), "..", "plugins")
        user_plugin_dir = self.plugin_dirs[0]  # Assuming the first one is the main user plugin dir

        if not os.path.exists(user_plugin_dir):
            os.makedirs(user_plugin_dir)

        for org_name in os.listdir(bundled_plugin_dir):
            org_path = os.path.join(bundled_plugin_dir, org_name)
            if os.path.isdir(org_path):
                for plugin_name in os.listdir(org_path):
                    plugin_path = os.path.join(org_path, plugin_name)
                    if os.path.isdir(plugin_path):
                        dest_org_path = os.path.join(user_plugin_dir, org_name)
                        dest_plugin_path = os.path.join(dest_org_path, plugin_name)

                        if not os.path.exists(dest_plugin_path):
                            try:
                                shutil.copytree(plugin_path, dest_plugin_path)
                                logging.info(f"Installed bundled plugin: {org_name}.{plugin_name}")
                            except Exception as e:
                                logging.error(f"Failed to install bundled plugin {plugin_name}: {e}")

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

        latest_version = sorted(versions, reverse=True)[0]
        version_path = os.path.join(plugin_path, latest_version)
        metadata_path = os.path.join(version_path, "metadata.json")

        if os.path.exists(metadata_path):
            original_sys_path = sys.path[:]
            try:
                # Add plugin's directory to sys.path to allow direct imports
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
                # Restore sys.path
                sys.path[:] = original_sys_path


    def get_standard_operations_plugin(self) -> StandardOperationsPlugin | None:
        """
        Returns the appropriate standard operations plugin for the current OS.
        Prefers the Windows-specific plugin on Windows.
        """
        if platform.system() == "Windows":
            # Look for the Windows-specific plugin first
            for plugin in self.plugins["standard_operations"]:
                if "windows" in plugin.name.lower():
                    return plugin

        # Fallback to the first available standard operations plugin
        if self.plugins["standard_operations"]:
            return self.plugins["standard_operations"][0]
        return None

    def get_view_mode_plugin(self, view_id: str) -> ViewModePlugin | None:
        for plugin in self.plugins["view_mode"]:
            if plugin.view_mode_name == view_id:
                return plugin
        return None

    def get_attribute_editor_plugin(self, editor_id: str) -> AttributeEditorPlugin | None:
        for plugin in self.plugins["attribute_editor"]:
            # Assuming attribute editor plugins might have an ID or we just pick the first one for now
            # The interface doesn't enforce an ID property, but let's assume we might add it or check name
            # For now, let's just return the first one if it matches or if no ID is passed
            return plugin
        return None

    def get_viewer_for_file(self, file_path: str) -> ViewerPlugin | None:
        # Simple logic: return the first viewer that supports the file type
        ext = os.path.splitext(file_path)[1].lower()
        for plugin in self.plugins["viewer"]:
            if ext in plugin.supported_extensions():
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
