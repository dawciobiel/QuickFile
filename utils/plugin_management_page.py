# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

"""
Settings page for external plugins.

The page only scans the external plugin directory when it is built. Talking to
the feed is an explicit action; the call runs through an injected runner so the
UI never blocks and tests can run synchronously. Every action goes through the
same functions as ``plugin_updater`` and ``plugin_state``, so the page adds no
second implementation of update, rollback or enable/disable.

Specification: ``docs/architecture/plugins/plugins.md``
("Zarządzanie wtyczkami zewnętrznymi").
"""

from typing import Callable, Optional

from PyQt6.QtCore import QObject, QRunnable, Qt, QThreadPool, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.plugin_management import PluginManagementService
from app.translation_manager import translation_manager

COLUMN_PLUGIN = 0
COLUMN_INSTALLED = 1
COLUMN_AVAILABLE = 2
COLUMN_STATUS = 3

STATUS_NOT_CHECKED = "not-checked"
STATUS_DISABLED = "disabled"

_ACTIVE_JOBS = set()


class _JobSignals(QObject):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)


class _Job(QRunnable):
    def __init__(self, function, signals):
        super().__init__()
        self.function = function
        self.signals = signals

    def run(self):
        try:
            result = self.function()
        except Exception as error:  # noqa: BLE001 - reported in the UI
            self.signals.failed.emit(str(error))
        else:
            self.signals.succeeded.emit(result)


def run_in_thread_pool(function, on_success, on_error):
    """Run ``function`` off the UI thread and deliver its result there."""
    signals = _JobSignals()
    job = _Job(function, signals)
    _ACTIVE_JOBS.add((job, signals))

    def finish(*_):
        _ACTIVE_JOBS.discard((job, signals))
        signals.deleteLater()

    signals.succeeded.connect(on_success)
    signals.failed.connect(on_error)
    signals.succeeded.connect(finish)
    signals.failed.connect(finish)
    QThreadPool.globalInstance().start(job)


class PluginManagementPage(QWidget):
    def __init__(
        self,
        parent=None,
        service: Optional[PluginManagementService] = None,
        runner: Callable = run_in_thread_pool,
    ):
        super().__init__(parent)
        self.service = service or PluginManagementService()
        self._runner = runner
        self._busy = False
        self._report = None
        self._plugins = {}
        self._statuses = {}
        self._available = {}

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.feed_label = QLabel(self.service.feed)
        self.feed_label.setWordWrap(True)
        layout.addWidget(self.feed_label)

        self.description_label = QLabel(
            translation_manager.translate(
                "PluginManagement",
                "External plugins are managed explicitly. Updates are verified "
                "before installation and take effect after restart.",
            )
        )
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label)

        self.table = QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(
            [
                translation_manager.translate("PluginManagement", "Plugin"),
                translation_manager.translate("PluginManagement", "Installed"),
                translation_manager.translate("PluginManagement", "Available"),
                translation_manager.translate("PluginManagement", "Status"),
            ]
        )
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COLUMN_PLUGIN, QHeaderView.ResizeMode.Stretch)
        for column in (COLUMN_INSTALLED, COLUMN_AVAILABLE, COLUMN_STATUS):
            header.setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        self.table.itemSelectionChanged.connect(self._update_actions)
        layout.addWidget(self.table, 1)

        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        buttons = QHBoxLayout()
        self.install_button = QPushButton(
            translation_manager.translate(
                "PluginManagement", "Install from file..."
            )
        )
        self.check_button = QPushButton(
            translation_manager.translate(
                "PluginManagement", "Check for updates"
            )
        )
        self.update_button = QPushButton(
            translation_manager.translate("PluginManagement", "Update")
        )
        self.rollback_button = QPushButton(
            translation_manager.translate("PluginManagement", "Rollback")
        )
        self.toggle_button = QPushButton(
            translation_manager.translate("PluginManagement", "Disable")
        )
        self.refresh_button = QPushButton(
            translation_manager.translate("PluginManagement", "Refresh")
        )
        for button in (
            self.install_button,
            self.check_button,
            self.update_button,
            self.rollback_button,
            self.toggle_button,
            self.refresh_button,
        ):
            buttons.addWidget(button)
        layout.addLayout(buttons)

        self.install_button.clicked.connect(self.install_from_file)
        self.check_button.clicked.connect(self.check)
        self.update_button.clicked.connect(self.update_selected)
        self.rollback_button.clicked.connect(self.rollback_selected)
        self.toggle_button.clicked.connect(self.toggle_selected)
        self.refresh_button.clicked.connect(self.refresh)
        self._update_actions()

    def refresh(self):
        """Reload the local list without touching the network."""
        try:
            plugins = self.service.plugins()
        except Exception as error:  # noqa: BLE001 - shown in the UI
            self._plugins = {}
            self.table.setRowCount(0)
            self.message_label.setText(str(error))
            self._update_actions()
            return

        self._plugins = {plugin.plugin_id: plugin for plugin in plugins}
        self._populate()

    def install_from_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            translation_manager.translate(
                "PluginManagement", "Install plugin package"
            ),
            "",
            translation_manager.translate(
                "PluginManagement", "Plugin packages (*.zip);;All files (*)"
            ),
        )
        if path:
            self.install_path(path)

    def install_path(self, path):
        self.message_label.setText(
            translation_manager.translate("PluginManagement", "Installing...")
        )
        self._run_job(
            lambda: self.service.install(path),
            self._installed,
            self._failed,
        )

    def check(self):
        self.message_label.setText(
            translation_manager.translate("PluginManagement", "Checking...")
        )
        self._run_job(
            self.service.check, self._checked, self._failed
        )

    def update_selected(self):
        plugin_id = self._selected_plugin_id()
        if plugin_id is None:
            return
        self._run_job(
            lambda: self.service.update(plugin_id),
            self._updated,
            self._failed,
        )

    def rollback_selected(self):
        plugin_id = self._selected_plugin_id()
        if plugin_id is None:
            return
        self._run_job(
            lambda: self.service.rollback(plugin_id),
            self._rolled_back,
            self._failed,
        )

    def toggle_selected(self):
        plugin_id = self._selected_plugin_id()
        if plugin_id is None:
            return
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            return
        action = self.service.enable if not plugin.enabled else self.service.disable
        self._run_job(
            lambda: action(plugin_id), self._toggled, self._failed
        )

    def _run_job(self, function, on_success, on_error):
        self._busy = True
        self._update_actions()

        def success(result):
            self._busy = False
            on_success(result)
            self._update_actions()

        def failure(message):
            self._busy = False
            on_error(message)
            self._update_actions()

        self._runner(function, success, failure)

    def _checked(self, report):
        self._report = report
        self.refresh()
        self.message_label.setText(
            translation_manager.translate(
                "PluginManagement", "Update check completed."
            )
        )

    def _installed(self, result):
        self._report = None
        self.refresh()
        message = translation_manager.translate(
            "PluginManagement",
            "Installed {plugin} {version} at {path}. "
            "Restart QuickFile to load it.",
        ).format(
            plugin=result.plugin_id,
            version=result.version,
            path=result.path,
        )
        if result.warnings:
            message += "\n" + "\n".join(
                f"warning: {warning}" for warning in result.warnings
            )
        self.message_label.setText(message)

    def _updated(self, result):
        self._report = None
        self.refresh()
        if result.status == "up-to-date":
            self.message_label.setText(
                translation_manager.translate(
                    "PluginManagement", "The plugin is up to date."
                )
            )
            return
        self.message_label.setText(
            translation_manager.translate(
                "PluginManagement",
                "Installed {plugin} {version}. Restart QuickFile to load it.",
            ).format(plugin=result.plugin_id, version=result.version)
        )

    def _rolled_back(self, result):
        self._report = None
        self.refresh()
        self.message_label.setText(
            translation_manager.translate(
                "PluginManagement",
                "Disabled {plugin} {version}; active version is {active}. "
                "Restart QuickFile.",
            ).format(
                plugin=result.plugin_id,
                version=result.disabled_version,
                active=result.active_version,
            )
        )

    def _toggled(self, result):
        self._report = None
        self.refresh()
        if result.enabled:
            message = translation_manager.translate(
                "PluginManagement",
                "Enabled {plugin}. Restart QuickFile to load it.",
            )
        else:
            message = translation_manager.translate(
                "PluginManagement",
                "Disabled {plugin}. Restart QuickFile.",
            )
        self.message_label.setText(message.format(plugin=result.plugin_id))

    def _failed(self, message):
        self.message_label.setText(message)

    def _populate(self):
        selected = self._selected_plugin_id()
        self.table.setRowCount(0)
        self._statuses = {}
        self._available = {}

        checked = {}
        if self._report is not None:
            checked = {
                item.plugin_id: item for item in self._report.packages
            }

        for plugin_id in sorted(self._plugins):
            plugin = self._plugins[plugin_id]
            if not plugin.enabled:
                status = STATUS_DISABLED
                available = ""
            elif plugin_id in checked:
                status = checked[plugin_id].status
                available = checked[plugin_id].available or ""
            else:
                status = STATUS_NOT_CHECKED
                available = ""

            self._statuses[plugin_id] = status
            self._available[plugin_id] = available
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._set_item(row, COLUMN_PLUGIN, plugin_id, plugin_id)
            self._set_item(row, COLUMN_INSTALLED, plugin.version)
            self._set_item(row, COLUMN_AVAILABLE, available)
            self._set_item(row, COLUMN_STATUS, self._status_label(status))

        if selected is not None:
            self._select_plugin(selected)
        self._update_actions()

    def _set_item(self, row, column, text, plugin_id=None):
        item = QTableWidgetItem(text)
        if plugin_id is not None:
            item.setData(Qt.ItemDataRole.UserRole, plugin_id)
        self.table.setItem(row, column, item)

    def _status_label(self, status):
        labels = {
            STATUS_NOT_CHECKED: "Not checked",
            STATUS_DISABLED: "Disabled",
            "update-available": "Update available",
            "up-to-date": "Up to date",
            "not-in-feed": "Not in feed",
            "managed-by-application": "Managed by application",
        }
        return translation_manager.translate(
            "PluginManagement", labels.get(status, status)
        )

    def _selected_plugin_id(self):
        items = self.table.selectedItems()
        if not items:
            return None
        item = self.table.item(items[0].row(), COLUMN_PLUGIN)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _select_plugin(self, plugin_id):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, COLUMN_PLUGIN)
            if item and item.data(Qt.ItemDataRole.UserRole) == plugin_id:
                self.table.selectRow(row)
                return

    def _update_actions(self):
        plugin_id = self._selected_plugin_id()
        plugin = self._plugins.get(plugin_id) if plugin_id else None
        status = self._statuses.get(plugin_id) if plugin_id else None

        self.install_button.setEnabled(not self._busy)
        self.check_button.setEnabled(not self._busy)
        self.refresh_button.setEnabled(not self._busy)
        self.update_button.setEnabled(
            not self._busy
            and plugin is not None
            and plugin.enabled
            and status == "update-available"
        )
        self.rollback_button.setEnabled(
            not self._busy
            and plugin is not None
            and plugin.enabled
            and len(plugin.versions) > 1
        )
        manageable = (
            plugin is not None and status != "managed-by-application"
        )
        self.toggle_button.setEnabled(not self._busy and manageable)
        if plugin is not None and not plugin.enabled:
            self.toggle_button.setText(
                translation_manager.translate("PluginManagement", "Enable")
            )
        else:
            self.toggle_button.setText(
                translation_manager.translate("PluginManagement", "Disable")
            )
