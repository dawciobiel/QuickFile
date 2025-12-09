from PyQt6.QtCore import Qt, QEvent, QObject

class KeyboardEventHandler(QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.key_handlers = {}
        self._init_key_handlers()

    def _init_key_handlers(self):
        """Initializes a dictionary to handle key press events."""
        # Access main_window's attributes directly for now
        self.key_handlers = {
            Qt.Key.Key_F1: lambda: self.main_window.status_bar.showMessage(self.main_window.tr("F1: Help (not implemented)")),
            Qt.Key.Key_F2: self.main_window.application_logic_handler.rename_selected_item,
            Qt.Key.Key_F3: self.main_window.application_logic_handler._handle_f3_key,
            Qt.Key.Key_F4: self.main_window.application_logic_handler._handle_f4_key,
            Qt.Key.Key_F5: self.main_window.application_logic_handler.copy_selected_item,
            Qt.Key.Key_F6: self.main_window.application_logic_handler.move_selected_item,
            Qt.Key.Key_F7: self.main_window.application_logic_handler.create_new_directory,
            Qt.Key.Key_F8: self.main_window.application_logic_handler.delete_selected_item,
            Qt.Key.Key_F9: self.main_window.application_logic_handler.compare_selected_items,
            Qt.Key.Key_F10: self.main_window.close,
        }

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if handler := self.key_handlers.get(key):
                handler()
                return True
            elif event.key() == Qt.Key.Key_B and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.main_window.application_logic_handler.open_bookmark_dialog()
                return True
        return super().eventFilter(source, event)
