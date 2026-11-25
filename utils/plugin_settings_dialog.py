# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""Host-rendered form for a plugin's ``settings.schema``.

Plugins never draw their own settings UI: sandboxed plugins cannot send a
QDialog over IPC, and letting every plugin invent a form would break themes,
translations and validation. The schema contract lives in
``app/plugin_settings.py``.
"""

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from app.plugin_settings import normalize_options
from app.translation_manager import translation_manager


class PluginSettingsDialog(QDialog):
    def __init__(
        self, parent, plugin_name: str, schema: dict, current_options: dict = None
    ):
        super().__init__(parent)
        self.schema = schema
        self._options = normalize_options(schema, current_options or {})
        self._widgets = {}

        self.setWindowTitle(
            f"{translation_manager.translate('PluginSettings', 'Plugin settings')}: "
            f"{translation_manager.translate('PluginName', plugin_name)}"
        )

        layout = QVBoxLayout(self)
        form = QFormLayout()

        for name, field in schema.items():
            widget = self._create_widget(field, self._options[name])
            self._widgets[name] = widget
            description = field.get("description")
            if description:
                widget.setToolTip(
                    translation_manager.translate("PluginSettings", description)
                )
            form.addRow(
                translation_manager.translate("PluginSettings", field["title"]),
                widget,
            )

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _create_widget(self, field: dict, value):
        field_type = field["type"]

        if field_type == "boolean":
            widget = QCheckBox()
            widget.setChecked(value)
            return widget

        if field_type == "integer":
            widget = QSpinBox()
            widget.setRange(
                field.get("minimum", -1_000_000_000),
                field.get("maximum", 1_000_000_000),
            )
            widget.setValue(value)
            return widget

        if field_type == "enum":
            widget = QComboBox()
            for choice in field["choices"]:
                widget.addItem(
                    translation_manager.translate("PluginSettings", choice["label"]),
                    choice["value"],
                )
            widget.setCurrentIndex(widget.findData(value))
            return widget

        widget = QLineEdit()
        widget.setText(value)
        return widget

    def get_options(self) -> dict:
        """Return the edited values, including keys the schema does not know."""
        options = dict(self._options)

        for name, widget in self._widgets.items():
            field_type = self.schema[name]["type"]
            if field_type == "boolean":
                options[name] = widget.isChecked()
            elif field_type == "integer":
                options[name] = widget.value()
            elif field_type == "enum":
                options[name] = widget.currentData()
            else:
                options[name] = widget.text()

        return options
