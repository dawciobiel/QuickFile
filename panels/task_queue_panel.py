import os
import json
import shutil
from PyQt6 import uic
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSize
from PyQt6.QtWidgets import QWidget, QMenu, QHeaderView, QPushButton
from PyQt6.QtGui import QAction

from app.task_queue_manager import TaskQueueManager, Task, TaskStatus
from app.translation_manager import translation_manager
from panels.task_queue_delegate import TaskQueueDelegate

class TaskQueueModel(QAbstractTableModel):
    def __init__(self, task_queue_manager: TaskQueueManager):
        super().__init__()
        self.manager = task_queue_manager
        self.column_config = self._load_column_config()
        self.visible_columns = [c for c in self.column_config if c.get("visible", True)]
        
        self.manager.task_added.connect(self.on_task_added)
        self.manager.queue_cleared.connect(self.on_queue_cleared)

    def _load_column_config(self):
        default_config = [
            {"id": "progress", "name": "Progress", "visible": True},
            {"id": "type", "name": "Type", "visible": True},
            {"id": "status", "name": "Status", "visible": True},
            {"id": "actions", "name": "Actions", "visible": True},
            {"id": "source", "name": "Source", "visible": True},
            {"id": "current", "name": "Current", "visible": True},
            {"id": "output", "name": "Output", "visible": True},
        ]
        
        user_config_dir = os.path.join(os.path.expanduser("~"), ".config", "QuickFile")
        user_config_path = os.path.join(user_config_dir, "queue_style.json")
        
        default_project_config_path = os.path.join(os.path.dirname(__file__), "..", "config", "queue_style.json")

        if not os.path.exists(user_config_path):
            try:
                os.makedirs(user_config_dir, exist_ok=True)
                if os.path.exists(default_project_config_path):
                    shutil.copy(default_project_config_path, user_config_path)
                else:
                    with open(user_config_path, 'w') as f:
                        json.dump({"columns": default_config}, f, indent=4)
            except OSError:
                 return default_config

        try:
            with open(user_config_path, 'r') as f:
                return json.load(f).get("columns", default_config)
        except (FileNotFoundError, json.JSONDecodeError):
            return default_config

    def rowCount(self, parent=QModelIndex()):
        return len(self.manager.tasks)

    def columnCount(self, parent=QModelIndex()):
        return len(self.visible_columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.manager.tasks)):
            return None
        
        task = self.manager.tasks[index.row()]
        column_info = self.visible_columns[index.column()]
        column_id = column_info["id"]

        if role == Qt.ItemDataRole.DisplayRole:
            if column_id == "type":
                return task.type.value
            elif column_id == "source":
                if isinstance(task.source_paths, list):
                    count = len(task.source_paths)
                    if count > 1:
                        return f"({count}+) {os.path.basename(task.source_paths[0])}"
                    elif count == 1:
                        return os.path.basename(task.source_paths[0])
                return str(task.source_paths)
            elif column_id == "output":
                return os.path.basename(task.destination_path) if task.destination_path else ""
            elif column_id == "progress":
                return f"{task.progress}%"
            elif column_id == "status":
                return task.status.value
            elif column_id == "current":
                return task._current_details
        
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.visible_columns[section]["name"]
        return None

    def on_task_added(self, task: Task):
        self.beginInsertRows(QModelIndex(), self.rowCount() - 1, self.rowCount() - 1)
        task.status_changed.connect(lambda: self.refresh_row(task))
        task.progress_changed.connect(lambda: self.refresh_row(task))
        task.details_changed.connect(lambda: self.refresh_row(task))
        self.endInsertRows()

    def on_queue_cleared(self):
        self.layoutChanged.emit()

    def refresh_row(self, task):
        try:
            row = self.manager.tasks.index(task)
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))
        except ValueError:
            pass

class TaskQueuePanel(QWidget):
    def __init__(self, task_queue_manager: TaskQueueManager, parent=None):
        super().__init__(parent)
        uic.loadUi("ui/task_queue_panel.ui", self)
        self.manager = task_queue_manager
        self.model = TaskQueueModel(self.manager)
        self.taskTableView.setModel(self.model)
        
        # Enable alternating row colors
        self.taskTableView.setAlternatingRowColors(True)
        
        self.delegate = TaskQueueDelegate(self.manager, self.taskTableView)
        
        header = self.taskTableView.horizontalHeader()
        
        for i, col_info in enumerate(self.model.visible_columns):
            if col_info["id"] == "actions":
                self.taskTableView.setItemDelegateForColumn(i, self.delegate)
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                header.resizeSection(i, 220)
                break
        
        self.taskTableView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.taskTableView.customContextMenuRequested.connect(self.show_context_menu)

        self.clear_button = QPushButton(translation_manager.translate("TaskQueuePanel", "Clear Finished"))
        self.clear_button.clicked.connect(self.manager.clear_finished_tasks)
        self.layout().addWidget(self.clear_button)

    def show_context_menu(self, pos):
        index = self.taskTableView.indexAt(pos)
        if not index.isValid():
            return

        task = self.manager.tasks[index.row()]
        menu = QMenu(self)

        if task.status == TaskStatus.RUNNING:
            pause_action = QAction("Pause", self)
            pause_action.triggered.connect(lambda: self.manager.pause_task(task.id))
            menu.addAction(pause_action)
            
            cancel_action = QAction("Cancel", self)
            cancel_action.triggered.connect(lambda: self.manager.cancel_task(task.id))
            menu.addAction(cancel_action)
            
        elif task.status == TaskStatus.PAUSED:
            resume_action = QAction("Resume", self)
            resume_action.triggered.connect(lambda: self.manager.resume_task(task.id))
            menu.addAction(resume_action)
            
            cancel_action = QAction("Cancel", self)
            cancel_action.triggered.connect(lambda: self.manager.cancel_task(task.id))
            menu.addAction(cancel_action)
            
        elif task.status == TaskStatus.PENDING:
            cancel_action = QAction("Remove/Cancel", self)
            cancel_action.triggered.connect(lambda: self.manager.cancel_task(task.id))
            menu.addAction(cancel_action)

        menu.exec(self.taskTableView.viewport().mapToGlobal(pos))
