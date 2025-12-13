import logging
from PyQt6.QtCore import Qt, QEvent, QObject
from PyQt6.QtWidgets import QApplication, QLineEdit
from app.translation_manager import translation_manager # Import our new manager

class KeyboardEventManager(QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        
    def eventFilter(self, source, event):
        if QApplication.activeModalWidget() is not None:
            return False # Let the modal widget handle the event

        if event.type() == QEvent.Type.KeyPress:
            # If a QLineEdit has focus, don't handle the key event here
            # so that it can process it (e.g., for typing, Enter press)
            if isinstance(QApplication.focusWidget(), QLineEdit):
                return False

            return self.handle_key_event(event)
            
        return super().eventFilter(source, event)

    def handle_key_event(self, event):
        key = event.key()
        modifiers = event.modifiers()
        
        # Handle global shortcuts (like F-keys, Ctrl+B)
        if key == Qt.Key.Key_Tab:
            self.main_window.folder_browser.switch_active_panel()
            return True # Event handled
        elif key == Qt.Key.Key_F1:
            self.main_window.status_bar.showMessage(translation_manager.translate("KeyboardEventManager", "F1: Help (not implemented)"))
            return True
        elif key == Qt.Key.Key_F2:
            self.main_window.application_logic_handler.rename_selected_item()
            return True
        elif key == Qt.Key.Key_F3:
            self.main_window.application_logic_handler._handle_f3_key()
            return True
        elif key == Qt.Key.Key_F4:
            self.main_window.application_logic_handler._handle_f4_key()
            return True
        elif key == Qt.Key.Key_F5:
            self.main_window.application_logic_handler.copy_selected_item()
            return True
        elif key == Qt.Key.Key_F6:
            self.main_window.application_logic_handler.move_selected_item()
            return True
        elif key == Qt.Key.Key_F7:
            self.main_window.application_logic_handler.create_new_directory()
            return True
        elif key == Qt.Key.Key_F8:
            self.main_window.application_logic_handler.delete_selected_item()
            return True
        elif key == Qt.Key.Key_F9:
            self.main_window.application_logic_handler.compare_selected_items()
            return True
        elif key == Qt.Key.Key_F10:
            self.main_window.close()
            return True
        elif key == Qt.Key.Key_B and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.main_window.application_logic_handler.open_bookmark_dialog()
            return True
        elif key == Qt.Key.Key_E and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.main_window.application_logic_handler.set_focus_on_path_edit()
            return True
        
        # Delegate to active panel's file view for local handling
        if self.main_window.folder_browser.active_panel_widget:
            active_view = self.main_window.folder_browser.active_panel_widget.file_view
            if hasattr(active_view, 'handle_key_event'):
                return active_view.handle_key_event(event)
            
        return False # Event not handled
