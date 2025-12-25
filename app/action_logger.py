import json
import logging
import os
import time
from pathlib import Path

class ActionLogger:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ActionLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self, log_dir="logs"):
        if not hasattr(self, '_initialized'):
            self.log_dir = log_dir
            self.actions_log_path = os.path.join(log_dir, "actions.log")
            self.actions_map_path = os.path.join(log_dir, "actions_map.log")
            
            self.path_map = {}
            self.file_counter = 0
            self.dir_counter = 0
            
            self._initialized = True

    def _anonymize_path(self, original_path):
        if original_path in self.path_map:
            return self.path_map[original_path]

        # Deconstruct the path
        p = Path(original_path)
        parts = p.parts
        
        anonymized_parts = []
        for part in parts:
            if part in self.path_map:
                anonymized_parts.append(self.path_map[part])
            else:
                # Anonymize this part
                if part == os.sep:
                    anonymized_parts.append(part)
                    continue
                
                is_dir = (Path(original_path).is_dir() and str(p).endswith(part)) or not p.name == part
                
                if is_dir:
                    self.dir_counter += 1
                    new_name = f"dir_{self.dir_counter}"
                else:
                    self.file_counter += 1
                    suffix = Path(part).suffix
                    new_name = f"file_{self.file_counter}{suffix}"
                
                self.path_map[part] = new_name
                anonymized_parts.append(new_name)

        anonymized_path = os.path.join(*anonymized_parts)
        # Handle root separately for posix systems
        if original_path.startswith('/') and not anonymized_path.startswith('/'):
            anonymized_path = '/' + anonymized_path
            
        self.path_map[original_path] = anonymized_path
        return anonymized_path

    def _anonymize_params(self, params):
        anonymized_params = {}
        for key, value in params.items():
            if isinstance(value, str) and (os.path.exists(value) or ('path' in key.lower())):
                anonymized_params[key] = self._anonymize_path(value)
            elif isinstance(value, list):
                anonymized_params[key] = [self._anonymize_path(v) if (isinstance(v, str) and os.path.exists(v)) else v for v in value]
            else:
                anonymized_params[key] = value
        return anonymized_params

    def log_action(self, action_name, **params):
        try:
            anonymized_params = self._anonymize_params(params)
            
            log_entry = {
                "timestamp": time.time(),
                "action": action_name,
                "params": anonymized_params
            }
            
            with open(self.actions_log_path, 'a') as f:
                f.write(json.dumps(log_entry) + "\\n")
                
            self._save_map()
        except Exception as e:
            logging.error(f"Failed to log action: {e}")

    def _save_map(self):
        try:
            with open(self.actions_map_path, 'w') as f:
                json.dump(self.path_map, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save action map: {e}")

# Singleton instance
action_logger = ActionLogger()
