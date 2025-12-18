import logging
from PyQt6.QtCore import Qt, QEvent, QObject
from PyQt6.QtWidgets import QApplication, QLineEdit
from app.translation_manager import translation_manager # Import our new manager
from app.application_logic_handler import ApplicationLogicHandler
from browser.folder_browser import FolderBrowser

class KeyboardEventManager(QObject):
    def __init__(self, main_window, application_logic_handler: ApplicationLogicHandler, folder_browser: FolderBrowser):
        super().__init__(main_window)
        self.main_window = main_window
        self.application_logic_handler = application_logic_handler
        self.folder_browser = folder_browser

        self.key_actions = {
            (Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier): self.folder_browser.switch_active_panel,
            (Qt.Key.Key_F1, Qt.KeyboardModifier.NoModifier): lambda: self.main_window.status_bar.showMessage(translation_manager.translate("KeyboardEventManager", "F1: Help (not implemented)")),
            (Qt.Key.Key_F2, Qt.KeyboardModifier.NoModifier): self.application_logic_handler.rename_selected_item,
            (Qt.Key.Key_F3, Qt.KeyboardModifier.NoModifier): self.application_logic_handler._handle_f3_key,
            (Qt.Key.Key_F4, Qt.KeyboardModifier.NoModifier): self.application_logic_handler._handle_f4_key,
            (Qt.Key.Key_F5, Qt.KeyboardModifier.NoModifier): self.application_logic_handler.copy_selected_item,
            (Qt.Key.Key_F6, Qt.KeyboardModifier.NoModifier): self.application_logic_handler.move_selected_item,
            (Qt.Key.Key_F7, Qt.KeyboardModifier.NoModifier): self.application_logic_handler.create_new_directory,
            (Qt.Key.Key_F8, Qt.KeyboardModifier.NoModifier): self.application_logic_handler.delete_selected_item,
            (Qt.Key.Key_F9, Qt.KeyboardModifier.NoModifier): self.application_logic_handler.compare_selected_items,
            (Qt.Key.Key_F10, Qt.KeyboardModifier.NoModifier): self.main_window.close,
            (Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier): self.application_logic_handler.open_bookmark_dialog,
            (Qt.Key.Key_E, Qt.KeyboardModifier.ControlModifier): self.application_logic_handler.set_focus_on_path_edit,
        }
        
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
        
        # Handle global shortcuts using the mapping
        action = self.key_actions.get((key, modifiers))
        if action:
            action()
            return True # Event handled
        
        # Delegate to active panel's file view for local handling
        if self.folder_browser.active_panel_widget:
            active_view = self.folder_browser.active_panel_widget.file_view
            if hasattr(active_view, 'handle_key_event'):
                return active_view.handle_key_event(event)
            
        return False # Event not handled
