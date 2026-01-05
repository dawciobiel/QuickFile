import os

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QFileDialog, QDialogButtonBox, QMessageBox, QLineEdit, QComboBox, QPushButton

from app.translation_manager import translation_manager


class CreateArchiveDialog(QDialog):
    def __init__(self, parent, plugin_manager, default_path, default_name="archive"):
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

        uic.loadUi("ui/create_archive_dialog.ui", self)
        self.setWindowTitle(translation_manager.translate("CreateArchiveDialog", "Create Archive"))

        self.plugin_manager = plugin_manager
        self.plugin_options = {}  # Stores options for each plugin: {plugin_name: options_dict}
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
        self.plugins = self.plugin_manager.get_all_archivers()
        for plugin in self.plugins:
            # Use the first supported extension as the label, or plugin name
            exts = plugin.get_supported_extensions()
            label = f"{plugin.name} ({', '.join(exts)})"
            # noinspection PyTypeChecker
            self.type_combo.addItem(label, plugin)

            # Initialize default options for this plugin if needed
            self.plugin_options[plugin.name] = {}

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

        current_options = self.plugin_options.get(plugin.name, {})

        # Check if the plugin supports configuration
        dialog = plugin.get_configuration_dialog(self, current_options)
        if dialog:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Assuming the dialog has a method to get the new options
                # Or it modifies the passed dictionary in place (less safe but possible)
                # Let's assume it returns new options via a method, e.g., get_options()
                if hasattr(dialog, 'get_options'):
                    self.plugin_options[plugin.name] = dialog.get_options()
        else:
            QMessageBox.information(self, "Info", translation_manager.translate("CreateArchiveDialog",
                                                                                "No configuration options available for this plugin."))

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

        # Construct full archive path based on selected plugin's extension
        exts = plugin.get_supported_extensions()
        ext = exts[0] if exts else ".zip"
        if not name.lower().endswith(ext):
            full_path = os.path.join(path, name + ext)
        else:
            full_path = os.path.join(path, name)

        options = self.plugin_options.get(plugin.name, {})

        return {
            "source_paths": [],  # To be filled by caller
            "destination_path": full_path,
            "plugin": plugin,
            "options": options,
            "add_to_queue": self.add_to_queue
        }
