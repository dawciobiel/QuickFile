import os
import json
import logging
import importlib.util
import shutil
from packaging.version import Version

from plugins.base import ArchivePlugin, ChecksumPlugin

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
        self.user_plugins_dir = os.path.join(os.path.expanduser("~"), ".config", "QuickFile", "plugins")
        self.bundled_plugins_dir = os.path.join(os.path.dirname(__file__), "..", "plugins")
        os.makedirs(self.user_plugins_dir, exist_ok=True)
        
        self.registry = {
            "archive": {},
            "checksum": {}
        }
        
        self._install_bundled_plugins()
        self.scan_and_load_plugins()

    def _install_bundled_plugins(self):
        """Copies bundled plugins to the user's config directory if they don't exist."""
        if not os.path.isdir(self.bundled_plugins_dir):
            return
        
        # Bundled structure: plugins/<groupId>/<artifactId>/<version>
        for group_id in os.listdir(self.bundled_plugins_dir):
            group_src = os.path.join(self.bundled_plugins_dir, group_id)
            if not os.path.isdir(group_src): continue
            
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

        # Structure: plugins/<groupId>/<artifactId>/<version>
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
                    logging.error(f"Failed to load plugin from {version_path}: {e}")
        
        # Sort versions for each artifact in each type registry
        full_id = f"{group_id}.{artifact_id}"
        for plugin_type in self.registry:
            if full_id in self.registry[plugin_type]:
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

        module_path = os.path.join(version_path, entry_point)
        # Unique module name to avoid collisions
        module_name = f"plugins.{group_id}.{artifact_id}.{version}.{entry_point.replace('.py', '')}"

        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
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
