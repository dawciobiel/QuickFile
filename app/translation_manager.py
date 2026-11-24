# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import json
import os
import locale
import logging
from utils.resource_path import get_resource_path

class TranslationManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TranslationManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.translations = {}
        self.settings_manager = None
        self.current_locale = self._determine_effective_locale()
        self._load_translations(self.current_locale)

    def _settings(self):
        """Return the settings manager, importing Qt only when it is available.

        Command-line helpers such as ``scripts/build_plugin_package.py`` import
        this module without PyQt6; they fall back to the system locale.
        """
        if self.settings_manager is None:
            from app.settings_manager import SettingsManager

            self.settings_manager = SettingsManager()
        return self.settings_manager

    def _determine_effective_locale(self):
        try:
            settings = self._settings()
        except ImportError:
            settings = None

        language_mode = (
            settings.get_setting("language_mode", "auto") if settings else "auto"
        )
        if language_mode == "manual":
            return settings.get_setting("manual_language", "en_US")
        else: # auto
            lang_code = None
            try:
                # Try locale.getlocale() first
                sys_locale_tuple = locale.getlocale()
                if sys_locale_tuple and sys_locale_tuple[0]:
                    lang_code = sys_locale_tuple[0]
                else:
                    # Fallback to environment variables if getlocale() doesn't return a specific language
                    for env_var in ['LANGUAGE', 'LC_ALL', 'LANG']:
                        if env_var in os.environ:
                            env_lang = os.environ[env_var]
                            # Take the first part if it's like "en_US.UTF-8"
                            lang_code = env_lang.split('.')[0]
                            break
            except Exception as e:
                logging.warning(f"Could not detect system locale using locale.getlocale() or environment variables: {e}")

            if lang_code:
                # Ensure consistent format (e.g., en_US instead of en-US or en_US.UTF-8)
                return lang_code.replace('-', '_').split('.')[0]
            
            logging.warning("Could not determine system locale, defaulting to en_US.")
            return "en_US"

    def _load_translations(self, lang_code):
        self.translations = {} # Clear existing translations
        
        # Try to load the specific language file, e.g., 'pl_PL.json'
        file_path = get_resource_path(os.path.join("translations", f"{lang_code}.json"))
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
                logging.info(f"Loaded translations for {lang_code}")
                self.current_locale = lang_code # Update current_locale
                return
            except json.JSONDecodeError as e:
                logging.error(f"Error decoding translation file {file_path}: {e}")
            except IOError as e:
                logging.error(f"Error reading translation file {file_path}: {e}")
        
        # Fallback to base language if specific locale fails (e.g., 'en_US' if 'en_GB' fails)
        base_lang = lang_code.split('_')[0]
        if base_lang != lang_code:
            file_path = get_resource_path(os.path.join("translations", f"{base_lang}.json"))
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.translations = json.load(f)
                    logging.info(f"Loaded translations for {base_lang}")
                    self.current_locale = base_lang # Update current_locale
                    return
                except (json.JSONDecodeError, IOError) as e:
                    logging.error(f"Error loading base language translation file {file_path}: {e}")

        # Fallback to default English if all else fails
        if lang_code != "en_US":
            file_path = get_resource_path(os.path.join("translations", "en_US.json"))
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.translations = json.load(f)
                    logging.info("Loaded default English translations.")
                    self.current_locale = "en_US" # Update current_locale
                except (json.JSONDecodeError, IOError) as e:
                    logging.error(f"Error loading default English translation file {file_path}: {e}")
            else:
                logging.error("Default English translation file 'en_US.json' not found!")
        else:
            logging.warning("No translations loaded, 'en_US.json' not found or errored.")

    def translate(self, context, text):
        key = f"{context}.{text}"
        return self.translations.get(key, text)


# Global instance for easy access
translation_manager = TranslationManager()


def task_queued_message(task_type) -> str:
    """Status-bar text for a task that was just added to the queue."""
    task_name = translation_manager.translate(
        "TaskType", task_type.name.replace("_", " ").title()
    )
    template = translation_manager.translate(
        "StatusBar", "Task added to queue: {task}"
    )
    return template.format(task=task_name)
