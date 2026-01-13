# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import json
import os
import logging
from enum import Enum
from utils.resource_path import get_resource_path

class FileAction(Enum):
    INTERNAL_VIEWER = "internal_viewer"
    INTERNAL_EDITOR = "internal_editor"
    SYSTEM_DEFAULT = "system_default"
    CUSTOM_COMMAND = "custom_command"

class FileAssociationManager:
    def __init__(self):
        self.config_dir = os.path.join(os.path.expanduser("~"), ".config", "QuickFile")
        self.config_file = os.path.join(self.config_dir, "file_associations.json")
        self.associations = []
        self.default_action = FileAction.SYSTEM_DEFAULT
        
        logging.info(f"FileAssociationManager initializing. Config file: {self.config_file}")
        self._load_config()

    def _get_default_config(self):
        default_config_path = get_resource_path("config/default_file_associations.json")
        try:
            with open(default_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load default file associations from {default_config_path}: {e}")
            # Fallback hardcoded config just in case
            return {
                "associations": [
                    {
                        "name": "Text Files",
                        "extensions": ["txt", "md", "py", "json", "xml", "log", "ini", "conf", "sh", "bat", "yml", "yaml"],
                        "action": "internal_viewer"
                    }
                ],
                "default_action": "system_default"
            }

    def _load_config(self):
        if not os.path.exists(self.config_dir):
            logging.info(f"Creating config directory: {self.config_dir}")
            os.makedirs(self.config_dir, exist_ok=True)

        if not os.path.exists(self.config_file):
            logging.info(f"Config file not found. Creating default at: {self.config_file}")
            self._save_config(self._get_default_config())
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.associations = config.get("associations", [])
                default_action_str = config.get("default_action", "system_default")
                try:
                    self.default_action = FileAction(default_action_str)
                except ValueError:
                    logging.warning(f"Invalid default action '{default_action_str}', falling back to SYSTEM_DEFAULT")
                    self.default_action = FileAction.SYSTEM_DEFAULT
            logging.info("File associations loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load file associations config: {e}")
            # Fallback to defaults in memory
            config = self._get_default_config()
            self.associations = config["associations"]

    def _save_config(self, config):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            logging.info(f"File associations config saved to {self.config_file}")
        except Exception as e:
            logging.error(f"Failed to save file associations config: {e}")

    def get_action_for_file(self, file_path):
        """
        Determines the action to take for a given file based on its extension.
        Returns a tuple (FileAction, command_string_or_None).
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower().lstrip('.') # Remove dot and lowercase

        for assoc in self.associations:
            if ext in assoc.get("extensions", []):
                action_str = assoc.get("action")
                try:
                    action = FileAction(action_str)
                    command = assoc.get("command")
                    return action, command
                except ValueError:
                    logging.warning(f"Invalid action '{action_str}' for extension '{ext}'")
                    continue
        
        return self.default_action, None
