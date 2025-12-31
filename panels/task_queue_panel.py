import logging

from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QTableView, QVBoxLayout, QHBoxLayout, QWidget, QHeaderView, QMenu, QProgressBar, QStyledItemDelegate, \
    QPushButton

from app.task_queue_manager import TaskQueueManager, TaskStatus  # Added Task, TaskType
from app.translation_manager import translation_manager


class TaskQueueModel(QAbstractTableModel):
    def __init__(self, manager: TaskQueueManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.manager.task_added.connect(self.on_task_added)
        self.manager.task_finished.connect(self.on_task_finished)
        self.manager.queue_cleared.connect(self.on_queue_cleared)
        logging.debug("TaskQueueModel initialized.")

    def on_task_added(self, task):
        logging.debug(f"TaskQueueModel: Task added {task.id}. Queue length: {len(self.manager.tasks)}")

        # Using layoutChanged as a fallback to ensure the view updates
        self.layoutChanged.emit()

        task.status_changed.connect(self.on_task_status_changed)
        task.progress_changed.connect(self.on_task_progress_changed)
        task.details_changed.connect(self.on_task_details_changed)

    def on_task_finished(self, task):
        logging.debug(f"TaskQueueModel: Task finished {task.id}")
        # Find the row for this task and update it
        try:
            row = self.manager.tasks.index(task)
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))
        except ValueError:
            pass
        self.layoutChanged.emit()

    def on_queue_cleared(self):
        logging.debug("TaskQueueModel: Queue cleared.")
        self.beginResetModel()
        self.endResetModel()

    def on_task_status_changed(self, status):
        task = self.sender()
        try:
            row = self.manager.tasks.index(task)
            self.dataChanged.emit(self.index(row, 1), self.index(row, 1))  # Status column
        except ValueError:
            pass

    def on_task_progress_changed(self, progress):
        task = self.sender()
        try:
            row = self.manager.tasks.index(task)
            self.dataChanged.emit(self.index(row, 2), self.index(row, 2))  # Progress column
        except ValueError:
            pass

    def on_task_details_changed(self, details):
        task = self.sender()
        try:
            row = self.manager.tasks.index(task)
            self.dataChanged.emit(self.index(row, 3), self.index(row, 3))  # Details column
        except ValueError:
            pass

    def rowCount(self, parent=QModelIndex()):
        count = len(self.manager.tasks)
        # logging.debug(f"TaskQueueModel: rowCount called, returning {count}")
        return count

    def columnCount(self, parent=QModelIndex()):
        return 4  # Type, Status, Progress, Details

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None

        task = self.manager.tasks[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            # logging.debug(f"TaskQueueModel: data requested for row {index.row()}, col {index.column()}")
            if index.column() == 0:
                return task.type.name
            elif index.column() == 1:
                return task.status.name
            elif index.column() == 2:
                # Progress is handled by the delegate
                return task.progress
            elif index.column() == 3:
                return task.details
        
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            if section == 0:
                return translation_manager.translate("TaskQueuePanel", "Type")
            elif section == 1:
                return translation_manager.translate("TaskQueuePanel", "Status")
            elif section == 2:
                return translation_manager.translate("TaskQueuePanel", "Progress")
            elif section == 3:
                return translation_manager.translate("TaskQueuePanel", "Details")
        return None


class ProgressDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        progress = index.data()
        if isinstance(progress, int):
            # Single progress value
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
            # Dual progress value (read, write)
            read_pct, write_pct = progress

            painter.save()

            # Draw background
            painter.fillRect(option.rect, option.palette.color(option.palette.ColorRole.AlternateBase))

            # Draw read progress (e.g., in a lighter blue)
            read_width = int(option.rect.width() * read_pct / 100)
            read_rect = option.rect.adjusted(0, 0, read_width - option.rect.width(), 0)
            painter.fillRect(read_rect, Qt.GlobalColor.cyan)

            # Draw write progress (e.g., in a darker blue)
            write_width = int(option.rect.width() * write_pct / 100)
            write_rect = option.rect.adjusted(0, 0, write_width - option.rect.width(), 0)
            painter.fillRect(write_rect, Qt.GlobalColor.blue)

            # Draw text
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

        # Force view update on layout change
        self.model.layoutChanged.connect(self.view.viewport().update)
        self.model.layoutChanged.connect(self.view.updateGeometry)

        self.view.setItemDelegateForColumn(2, ProgressDelegate(self.view))

        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.view.setColumnWidth(3, 400)

        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_context_menu)

        self.layout.addWidget(self.view)

        # Add buttons
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

    def show_context_menu(self, pos):
        index = self.view.indexAt(pos)
        if not index.isValid():
            return

        task = self.manager.tasks[index.row()]

        menu = QMenu()

        if task.status in [TaskStatus.RUNNING, TaskStatus.PAUSED]:
            pause_resume_action = QAction(translation_manager.translate("TaskQueuePanel",
                                                                        "Pause") if task.status == TaskStatus.RUNNING else translation_manager.translate(
                "TaskQueuePanel", "Resume"), self)
            pause_resume_action.triggered.connect(lambda: self.toggle_pause_resume(task.id))
            menu.addAction(pause_resume_action)

            cancel_action = QAction(translation_manager.translate("TaskQueuePanel", "Cancel"), self)
            cancel_action.triggered.connect(lambda: self.manager.cancel_task(task.id))
            menu.addAction(cancel_action)

        menu.exec(self.view.viewport().mapToGlobal(pos))

    def toggle_pause_resume(self, task_id):
        task = next((t for t in self.manager.tasks if t.id == task_id), None)
        if not task: return

        if task.status == TaskStatus.RUNNING:
            self.manager.pause_task(task_id)
        elif task.status == TaskStatus.PAUSED:
            self.manager.resume_task(task_id)

    def clear_completed_tasks(self):
        self.manager.clear_completed_tasks()

    def clear_error_tasks(self):
        self.manager.clear_error_tasks()

    def clear_all_tasks(self):
        self.manager.clear_all_tasks()
