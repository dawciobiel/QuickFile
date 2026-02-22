# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import json
import os
import locale
import logging
from quickfile.app.settings_manager import SettingsManager # Import SettingsManager
from quickfile.utils.resource_path import get_resource_path

class TranslationManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TranslationManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.translations = {}
        self.settings_manager = SettingsManager() # Get an instance of SettingsManager
        self.current_locale = self._determine_effective_locale()
        self._load_translations(self.current_locale)

    def _determine_effective_locale(self):
        language_mode = self.settings_manager.get_setting("language_mode", "auto")
        if language_mode == "manual":
            return self.settings_manager.get_setting("manual_language", "en_US")
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
