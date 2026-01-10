# Copyright (C) 2025 Dawid Bielecki
# This file is part of QuickFile and is licensed under the GPLv3.
# See LICENSE file for details.

import logging

from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QTableView, QVBoxLayout, QHBoxLayout, QWidget, QHeaderView, QProgressBar, QStyledItemDelegate, \
    QPushButton, QMessageBox

from app.task_queue_manager import TaskQueueManager, TaskStatus
from app.translation_manager import translation_manager
from utils.formatters import format_speed

class TaskActionsWidget(QWidget):
    """A widget containing buttons for a single task."""

    def __init__(self, task, manager, parent=None):
        super().__init__(parent)
        self.task = task
        self.manager = manager

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)

        self.pause_resume_btn = QPushButton()
        self.cancel_btn = QPushButton(translation_manager.translate("TaskQueuePanel", "Cancel"))
        self.more_btn = QPushButton(translation_manager.translate("TaskQueuePanel", "More"))

        self.pause_resume_btn.clicked.connect(self.toggle_pause_resume)
        self.cancel_btn.clicked.connect(self.cancel_task)
        self.more_btn.clicked.connect(self.show_more_options)

        layout.addWidget(self.pause_resume_btn)
        layout.addWidget(self.cancel_btn)
        layout.addWidget(self.more_btn)
        layout.addStretch()

        self.update_button_state()

    def toggle_pause_resume(self):
        if self.task.status == TaskStatus.IN_PROGRESS:
            self.manager.pause_task(self.task.id)
        elif self.task.status == TaskStatus.PAUSED:
            self.manager.resume_task(self.task.id)

    def cancel_task(self):
        self.manager.cancel_task(self.task.id)

    def show_more_options(self):
        QMessageBox.information(self, "Info", "More options not implemented yet.")

    def update_button_state(self):
        if self.task.status == TaskStatus.IN_PROGRESS:
            self.pause_resume_btn.setText(translation_manager.translate("TaskQueuePanel", "Pause"))
            self.pause_resume_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)
            self.more_btn.setEnabled(True)
        elif self.task.status == TaskStatus.PAUSED:
            self.pause_resume_btn.setText(translation_manager.translate("TaskQueuePanel", "Resume"))
            self.pause_resume_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)
            self.more_btn.setEnabled(True)
        else:  # FINISHED, CANCELLED, ERROR
            self.pause_resume_btn.setEnabled(False)
            self.cancel_btn.setEnabled(False)
            self.more_btn.setEnabled(False)

class TaskQueueModel(QAbstractTableModel):
    def __init__(self, manager: TaskQueueManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.manager.task_added.connect(self.on_task_added)
        self.manager.task_finished.connect(self.on_task_finished)
        self.manager.queue_cleared.connect(self.on_queue_cleared)

    def on_task_added(self, task):
        self.layoutChanged.emit()
        task.status_changed.connect(self.on_task_status_changed)
        task.progress_changed.connect(self.on_task_progress_changed)
        task.details_changed.connect(self.on_task_details_changed)
        task.speed_changed.connect(self.on_task_speed_changed)

    def on_task_finished(self, task):
        self.layoutChanged.emit()

    def on_queue_cleared(self):
        self.beginResetModel()
        self.endResetModel()

    def on_task_status_changed(self, status):
        task = self.sender()
        try:
            row = self.manager.all_tasks.index(task)
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))
        except ValueError:
            pass

    def on_task_progress_changed(self, progress):
        task = self.sender()
        try:
            row = self.manager.all_tasks.index(task)
            self.dataChanged.emit(self.index(row, 2), self.index(row, 2))
        except ValueError:
            pass

    def on_task_details_changed(self, details):
        task = self.sender()
        try:
            row = self.manager.all_tasks.index(task)
            self.dataChanged.emit(self.index(row, 3), self.index(row, 3))
        except ValueError:
            pass

    def on_task_speed_changed(self, speed):
        task = self.sender()
        try:
            row = self.manager.all_tasks.index(task)
            self.dataChanged.emit(self.index(row, 4), self.index(row, 4))
        except ValueError:
            pass

    def rowCount(self, parent=QModelIndex()):
        return len(self.manager.all_tasks)

    def columnCount(self, parent=QModelIndex()):
        return 6  # Type, Status, Progress, Details, Speed, Actions

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None

        task = self.manager.all_tasks[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0: return task.type.name
            if index.column() == 1: return task.status.name
            if index.column() == 2: return task.progress
            if index.column() == 3: return task.details
            if index.column() == 4: return format_speed(task.speed)

        if role == Qt.ItemDataRole.BackgroundRole:
            if task.status == TaskStatus.ERROR:
                return QColor(Qt.GlobalColor.red)
            elif task.status == TaskStatus.PAUSED:
                return QColor(Qt.GlobalColor.yellow)
            elif task.status == TaskStatus.FINISHED:
                return QColor(Qt.GlobalColor.darkGreen)
        
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            headers = {
                0: translation_manager.translate("TaskQueuePanel", "Type"),
                1: translation_manager.translate("TaskQueuePanel", "Status"),
                2: translation_manager.translate("TaskQueuePanel", "Progress"),
                3: translation_manager.translate("TaskQueuePanel", "Details"),
                4: translation_manager.translate("TaskQueuePanel", "Speed"),
                5: translation_manager.translate("TaskQueuePanel", "Actions")
            }
            return headers.get(section)
        return None

class ProgressDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        progress = index.data()
        if isinstance(progress, int):
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100)
            progress_bar.setValue(progress)
            progress_bar.setTextVisible(True)
            progress_bar.setGeometry(option.rect)
            painter.save()
            painter.translate(option.rect.topLeft())
            progress_bar.render(painter)
            painter.restore()
        elif isinstance(progress, tuple) and len(progress) == 2:
            read_pct, write_pct = progress
            painter.save()
            painter.fillRect(option.rect, option.palette.color(option.palette.ColorRole.AlternateBase))
            read_width = int(option.rect.width() * read_pct / 100)
            read_rect = option.rect.adjusted(0, 0, read_width - option.rect.width(), 0)
            painter.fillRect(read_rect, Qt.GlobalColor.cyan)
            write_width = int(option.rect.width() * write_pct / 100)
            write_rect = option.rect.adjusted(0, 0, write_width - option.rect.width(), 0)
            painter.fillRect(write_rect, Qt.GlobalColor.blue)
            painter.setPen(option.palette.color(option.palette.ColorRole.Text))
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, f"{write_pct}%")
            painter.restore()
        else:
            super().paint(painter, option, index)

class TaskQueuePanel(QWidget):
    def __init__(self, manager: TaskQueueManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.view = QTableView()
        self.model = TaskQueueModel(self.manager)
        self.view.setModel(self.model)

        self.manager.task_added.connect(lambda: QTimer.singleShot(0, self._update_action_widgets))
        self.manager.task_finished.connect(lambda: QTimer.singleShot(0, self._update_action_widgets))
        
        self.view.setItemDelegateForColumn(2, ProgressDelegate(self.view))

        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.view.setColumnWidth(3, 400)
        self.view.setColumnWidth(4, 100) # Speed column
        self.view.setColumnWidth(5, 250)  # Actions column
        
        self.layout.addWidget(self.view)

        self.buttons_layout = QHBoxLayout()
        self.clear_completed_btn = QPushButton(translation_manager.translate("TaskQueuePanel", "Clear Completed"))
        self.clear_error_btn = QPushButton(translation_manager.translate("TaskQueuePanel", "Clear Error"))
        self.clear_all_btn = QPushButton(translation_manager.translate("TaskQueuePanel", "Clear All"))

        self.clear_completed_btn.clicked.connect(self.clear_completed_tasks)
        self.clear_error_btn.clicked.connect(self.clear_error_tasks)
        self.clear_all_btn.clicked.connect(self.clear_all_tasks)

        self.buttons_layout.addWidget(self.clear_completed_btn)
        self.buttons_layout.addWidget(self.clear_error_btn)
        self.buttons_layout.addWidget(self.clear_all_btn)
        self.buttons_layout.addStretch()

        self.layout.addLayout(self.buttons_layout)
        logging.debug("TaskQueuePanel initialized.")

    def _update_action_widgets(self):
        row_count = self.model.rowCount()
        for row in range(row_count):
            task = self.manager.all_tasks[row]
            index = self.model.index(row, 5)  # Actions column

            if task.status in [TaskStatus.IN_PROGRESS, TaskStatus.PAUSED]:
                existing_widget = self.view.indexWidget(index)
                if existing_widget:
                    existing_widget.update_button_state()
                else:
                    widget = TaskActionsWidget(task, self.manager)
                    self.view.setIndexWidget(index, widget)
            else:
                if self.view.indexWidget(index):
                    self.view.setIndexWidget(index, None)

    def clear_completed_tasks(self):
        self.manager.clear_completed_tasks()

    def clear_error_tasks(self):
        self.manager.clear_error_tasks()

    def clear_all_tasks(self):
        self.manager.clear_all_tasks()
