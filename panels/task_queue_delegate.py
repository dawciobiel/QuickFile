from PyQt6.QtWidgets import QStyledItemDelegate, QStyle, QApplication, QStyleOptionButton
from PyQt6.QtCore import Qt, QRect, QPoint, QSize
from PyQt6.QtGui import QMouseEvent

from app.task_queue_manager import TaskStatus

class TaskQueueDelegate(QStyledItemDelegate):
    def __init__(self, task_manager, parent=None):
        super().__init__(parent)
        self.task_manager = task_manager
        self.buttons = {}

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        
        task = index.model().manager.tasks[index.row()]
        self.buttons[index.row()] = {}

        button_width = 60
        button_height = 20
        spacing = 5
        y = option.rect.y() + (option.rect.height() - button_height) // 2
        x = option.rect.x() + spacing

        buttons_to_draw = []
        if task.status == TaskStatus.RUNNING:
            buttons_to_draw = [("Pause", "pause", True), ("Cancel", "cancel", True)]
        elif task.status == TaskStatus.PAUSED:
            buttons_to_draw = [("Resume", "resume", True), ("Cancel", "cancel", True)]
        elif task.status == TaskStatus.PENDING:
            buttons_to_draw = [("Cancel", "cancel", True)]
        elif task.status in [TaskStatus.FINISHED, TaskStatus.CANCELLED, TaskStatus.ERROR]:
            buttons_to_draw = [("Pause", "pause", False), ("Cancel", "cancel", False)]

        buttons_to_draw.append(("Settings", "settings", False))

        for text, button_id, enabled in buttons_to_draw:
            if x + button_width > option.rect.right():
                break
            self._draw_button(painter, option, x, y, button_width, button_height, text, index, button_id, enabled)
            x += button_width + spacing

    def _draw_button(self, painter, option, x, y, w, h, text, index, button_id, enabled=True):
        rect = QRect(x, y, w, h)
        self.buttons[index.row()][button_id] = {"rect": rect, "enabled": enabled}

        button_option = QStyleOptionButton()
        button_option.rect = rect
        button_option.text = text
        button_option.state = QStyle.StateFlag.State_Enabled if enabled else QStyle.StateFlag.State_None
        
        if enabled and option.state & QStyle.StateFlag.State_MouseOver and rect.contains(option.state.mousePos):
            button_option.state |= QStyle.StateFlag.State_Raised
        else:
            button_option.state |= QStyle.StateFlag.State_Sunken

        style = QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_PushButton, button_option, painter)

    def editorEvent(self, event, model, option, index):
        if event.type() == QMouseEvent.Type.MouseMove:
            model.dataChanged.emit(index, index)
            return True

        if event.type() == QMouseEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            row_buttons = self.buttons.get(index.row())
            if not row_buttons:
                return False

            task = model.manager.tasks[index.row()]
            for button_id, button_data in row_buttons.items():
                if button_data["rect"].contains(pos) and button_data["enabled"]:
                    self._handle_button_click(task.id, button_id)
                    return True
        return False

    def _handle_button_click(self, task_id, button_id):
        if button_id == "pause":
            self.task_manager.pause_task(task_id)
        elif button_id == "resume":
            self.task_manager.resume_task(task_id)
        elif button_id == "cancel":
            self.task_manager.cancel_task(task_id)
        elif button_id == "settings":
            print(f"Settings for task {task_id} clicked (not implemented).")
        
    def sizeHint(self, option, index):
        return QSize(220, 25)
