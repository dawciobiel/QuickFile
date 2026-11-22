# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import logging
import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QFileDialog, QDialogButtonBox, QMessageBox, QLineEdit, QComboBox, QPushButton

from app.plugin_settings import (
    PluginSettingsError,
    normalize_options,
    schema_for_plugin,
)
from app.plugin_system.api import Capability
from app.settings_manager import SettingsManager
from app.translation_manager import translation_manager
from app.ui_translation import translate_widgets
from utils.plugin_settings_dialog import PluginSettingsDialog
from utils.resource_path import get_resource_path


class CreateArchiveDialog(QDialog):
    def __init__(
        self,
        parent,
        plugin_manager,
        default_path,
        default_name="archive",
        settings_manager=None,
    ):
        super().__init__(parent)

        # --- Declare UI attributes for linter ---
        self.name_edit: QLineEdit | None = None
        self.path_edit: QLineEdit | None = None
        self.type_combo: QComboBox | None = None
        self.browse_button: QPushButton | None = None
        self.settings_button: QPushButton | None = None
        self.queue_button: QPushButton | None = None
        self.buttonBox: QDialogButtonBox | None = None
        # -----------------------------------------

        uic.loadUi(get_resource_path("ui/create_archive_dialog.ui"), self)
        translate_widgets(self)
        self.setWindowTitle(translation_manager.translate("CreateArchiveDialog", "Create Archive"))

        self.plugin_manager = plugin_manager
        self.settings_manager = settings_manager or SettingsManager()
        self.plugin_options = {}  # {plugin_id: options_dict}
        self.add_to_queue = False

        # noinspection PyTypeChecker
        self.name_edit.setText(default_name)
        # noinspection PyTypeChecker
        self.path_edit.setText(default_path)

        self._populate_plugins()

        # noinspection PyTypeChecker
        self.browse_button.clicked.connect(self.browse_path)
        # noinspection PyTypeChecker
        self.settings_button.clicked.connect(self.show_plugin_settings)
        # noinspection PyTypeChecker
        self.queue_button.clicked.connect(self.on_queue_clicked)

        # noinspection PyTypeChecker
        self.buttonBox.accepted.connect(self.accept)
        # noinspection PyTypeChecker
        self.buttonBox.rejected.connect(self.reject)

        # Rename OK button to Start
        # noinspection PyTypeChecker
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText(translation_manager.translate("Buttons", "Start"))

    def _populate_plugins(self):
        self.plugins = self.plugin_manager.get_archivers(Capability.ARCHIVE_CREATE)
        for plugin in self.plugins:
            # Use the first supported extension as the label, or plugin name
            exts = plugin.get_supported_extensions()
            plugin_name = plugin.get_name()
            label = f"{plugin_name} ({', '.join(exts)})"
            # noinspection PyTypeChecker
            self.type_combo.addItem(label, plugin)

            self.plugin_options[plugin.metadata["id"]] = self._load_plugin_options(
                plugin
            )

    def _load_plugin_options(self, plugin) -> dict:
        """Load saved options and fill defaults from the declared schema."""
        plugin_id = plugin.metadata["id"]
        stored = self.settings_manager.get_plugin_settings(plugin_id)
        schema = schema_for_plugin(plugin)
        if not schema:
            return stored

        try:
            return normalize_options(schema, stored)
        except PluginSettingsError:
            logging.warning(
                "Plugin %s has an invalid settings schema; using saved options "
                "without defaults.",
                plugin_id,
                exc_info=True,
            )
            return stored

    def browse_path(self):
        path = QFileDialog.getExistingDirectory(self, translation_manager.translate("CreateArchiveDialog", "Select Destination Directory"))
        if path:
            # noinspection PyTypeChecker
            self.path_edit.setText(path)

    def show_plugin_settings(self):
        # noinspection PyTypeChecker
        plugin = self.type_combo.currentData()
        if not plugin:
            return

        plugin_id = plugin.metadata["id"]
        schema = schema_for_plugin(plugin)
        if not schema:
            QMessageBox.information(
                self,
                translation_manager.translate("CreateArchiveDialog", "Info"),
                translation_manager.translate(
                    "CreateArchiveDialog",
                    "No configuration options available for this plugin.",
                ),
            )
            return

        try:
            dialog = PluginSettingsDialog(
                self,
                plugin.get_name(),
                schema,
                self.plugin_options.get(plugin_id, {}),
            )
        except PluginSettingsError:
            logging.warning(
                "Plugin %s has an invalid settings schema.", plugin_id, exc_info=True
            )
            QMessageBox.warning(
                self,
                translation_manager.translate("PluginSettings", "Invalid settings"),
                translation_manager.translate(
                    "PluginSettings",
                    "This plugin has an invalid settings schema.",
                ),
            )
            return

        if dialog.exec() == QDialog.DialogCode.Accepted:
            options = dialog.get_options()
            self.plugin_options[plugin_id] = options
            self.settings_manager.set_plugin_settings(plugin_id, options)

    def on_queue_clicked(self):
        self.add_to_queue = True
        self.accept()

    def get_data(self):
        # noinspection PyTypeChecker
        name = self.name_edit.text()
        # noinspection PyTypeChecker
        path = self.path_edit.text()
        # noinspection PyTypeChecker
        plugin = self.type_combo.currentData()

        if not name or not path or not plugin:
            return None

        # Construct full archive path based on selected plugin's extension.
        # Plugins return extensions both with and without a leading dot, so
        # normalise before comparing and appending.
        exts = plugin.get_supported_extensions()
        ext = exts[0].lower().lstrip(".") if exts else "zip"
        suffix = f".{ext}"
        if not name.lower().endswith(suffix):
            full_path = os.path.join(path, name + suffix)
        else:
            full_path = os.path.join(path, name)

        plugin_id = plugin.metadata["id"]
        options = dict(self.plugin_options.get(plugin_id, {}))
        options['plugin_id'] = plugin_id

        return {
            "source_paths": [],  # To be filled by caller
            "destination_path": full_path,
            "plugin": plugin,
            "options": options,
            "add_to_queue": self.add_to_queue
        }
