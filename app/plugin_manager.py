import importlib
import json
import logging
import os
import shutil
import sys

from packaging.version import Version

from plugins.base import ArchivePlugin, ChecksumPlugin, SearchPlugin, ViewerPlugin, AttributeEditorPlugin, ViewModePlugin, SymlinkPlugin, \
    StandardOperationsPlugin


class PluginInfo:
    """Holds metadata and the loaded class for a specific plugin version."""
    def __init__(self, group_id, artifact_id, version, path, metadata, plugin_class):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.version = Version(version)
        self.path = path
        self.metadata = metadata
        self.plugin_class = plugin_class
        self.instance = None

    def get_instance(self):
        if not self.instance:
            self.instance = self.plugin_class()
        return self.instance

class PluginManager:
    def __init__(self):
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.user_plugins_dir = os.path.join(os.path.expanduser("~"), ".config", "QuickFile", "plugins")
        self.bundled_plugins_dir = os.path.join(self.project_root, "plugins")
        os.makedirs(self.user_plugins_dir, exist_ok=True)
        
        self.registry = {
            "archive": {},
            "checksum": {},
            "search": {},
            "viewer": {},
            "attribute_editor": {},
            "view_mode": {},
            "symlink": {},
            "standard_operations": {}
        }
        
        self._install_bundled_plugins()
        self.scan_and_load_plugins()

    def _install_bundled_plugins(self):
        if not os.path.isdir(self.bundled_plugins_dir):
            return
        
        for group_id in os.listdir(self.bundled_plugins_dir):
            group_src = os.path.join(self.bundled_plugins_dir, group_id)
            if not os.path.isdir(group_src) or not group_id.startswith("org."):
                continue
            
            for artifact_id in os.listdir(group_src):
                artifact_src = os.path.join(group_src, artifact_id)
                if not os.path.isdir(artifact_src): continue
                
                for version in os.listdir(artifact_src):
                    version_src = os.path.join(artifact_src, version)
                    version_dst = os.path.join(self.user_plugins_dir, group_id, artifact_id, version)
                    
                    if os.path.isdir(version_src) and not os.path.exists(version_dst):
                        try:
                            shutil.copytree(version_src, version_dst)
                            logging.info(f"Installed bundled plugin: {group_id}.{artifact_id} v{version}")
                        except Exception as e:
                            logging.error(f"Failed to install bundled plugin {group_id}.{artifact_id}: {e}")

    def scan_and_load_plugins(self):
        logging.info(f"Scanning for plugins in: {self.user_plugins_dir}")
        if not os.path.isdir(self.user_plugins_dir):
            return

        for group_id in os.listdir(self.user_plugins_dir):
            group_path = os.path.join(self.user_plugins_dir, group_id)
            if not os.path.isdir(group_path): continue

            for artifact_id in os.listdir(group_path):
                artifact_path = os.path.join(group_path, artifact_id)
                if not os.path.isdir(artifact_path): continue

                self._load_artifact_versions(group_id, artifact_id, artifact_path)

    def _load_artifact_versions(self, group_id, artifact_id, artifact_path):
        for version in os.listdir(artifact_path):
            version_path = os.path.join(artifact_path, version)
            if os.path.isdir(version_path):
                try:
                    plugin_info = self._load_plugin(group_id, artifact_id, version, version_path)
                    if plugin_info:
                        plugin_type = plugin_info.metadata.get("type")
                        if not plugin_type:
                            logging.warning(f"Plugin {group_id}.{artifact_id} v{version} missing 'type' in metadata. Skipping.")
                            continue
                        
                        if plugin_type not in self.registry:
                            self.registry[plugin_type] = {}

                        full_id = f"{group_id}.{artifact_id}"
                        if full_id not in self.registry[plugin_type]:
                            self.registry[plugin_type][full_id] = []
                        self.registry[plugin_type][full_id].append(plugin_info)
                        logging.info(f"Successfully loaded plugin: {full_id} v{version} (type: {plugin_type})")
                except Exception as e:
                    logging.error(f"Failed to load plugin from {version_path}: {e}", exc_info=True)
        
        for plugin_type in self.registry:
            for full_id in self.registry[plugin_type]:
                self.registry[plugin_type][full_id].sort(key=lambda p: p.version, reverse=True)

    def _load_plugin(self, group_id, artifact_id, version, version_path):
        metadata_path = os.path.join(version_path, "metadata.json")
        if not os.path.exists(metadata_path):
            raise FileNotFoundError("metadata.json not found")

        with open(metadata_path, 'r') as f:
            metadata = json.load(f)

        entry_point = metadata.get("entry_point")
        class_name = metadata.get("class_name")
        if not entry_point or not class_name:
            raise ValueError("'entry_point' or 'class_name' missing in metadata.json")

        module_name = os.path.splitext(entry_point)[0]
        
        # Add plugin directory to path and import, then remove
        sys.path.insert(0, version_path)
        try:
            module = importlib.import_module(module_name)
            importlib.reload(module) # Ensure we get the latest version
        finally:
            sys.path.pop(0)
        
        plugin_class = getattr(module, class_name)
        return PluginInfo(group_id, artifact_id, version, version_path, metadata, plugin_class)

    def get_archive_plugins(self) -> list[ArchivePlugin]:
        plugins = []
        if "archive" in self.registry:
            for artifact_id, versions in self.registry["archive"].items():
                if versions:
                    plugins.append(versions[0].get_instance())
        return plugins

    def get_archiver_for_extension(self, extension: str) -> ArchivePlugin | None:
        for plugin in self.get_archive_plugins():
            if extension.lower() in plugin.get_supported_extensions():
                return plugin
        return None

    def get_checksum_plugins(self) -> list[ChecksumPlugin]:
        plugins = []
        if "checksum" in self.registry:
            for artifact_id, versions in self.registry["checksum"].items():
                if versions:
                    plugins.append(versions[0].get_instance())
        return plugins

    def get_search_plugins(self) -> list[SearchPlugin]:
        plugins = []
        if "search" in self.registry:
            for artifact_id, versions in self.registry["search"].items():
                if versions:
                    plugins.append(versions[0].get_instance())
        return plugins

    def get_viewer_plugins(self) -> list[ViewerPlugin]:
        plugins = []
        if "viewer" in self.registry:
            for artifact_id, versions in self.registry["viewer"].items():
                if versions:
                    plugins.append(versions[0].get_instance())
        return plugins

    def get_viewer_for_file(self, file_path: str) -> ViewerPlugin | None:
        for plugin in self.get_viewer_plugins():
            if plugin.can_view(file_path):
                return plugin
        return None

    def get_attribute_editor_plugin(self) -> AttributeEditorPlugin | None:
        if "attribute_editor" in self.registry:
            for artifact_id, versions in self.registry["attribute_editor"].items():
                if versions:
                    plugin = versions[0].get_instance()
                    if plugin.is_supported():
                        return plugin
        return None

    def get_view_mode_plugins(self) -> list[ViewModePlugin]:
        plugins = []
        if "view_mode" in self.registry:
            for artifact_id, versions in self.registry["view_mode"].items():
                if versions:
                    plugins.append(versions[0].get_instance())
        return plugins

    def get_view_mode_plugin(self, name: str) -> ViewModePlugin | None:
        for plugin in self.get_view_mode_plugins():
            if plugin.view_mode_name == name:
                return plugin
        return None

    def get_symlink_plugin(self) -> SymlinkPlugin | None:
        if "symlink" in self.registry:
            for artifact_id, versions in self.registry["symlink"].items():
                if versions:
                    plugin = versions[0].get_instance()
                    if plugin.is_supported():
                        return plugin
        return None

    def get_standard_operations_plugin(self) -> StandardOperationsPlugin | None:
        if "standard_operations" in self.registry:
            for artifact_id, versions in self.registry["standard_operations"].items():
                if versions:
                    # Return the first available plugin (highest version)
                    return versions[0].get_instance()
        return None
