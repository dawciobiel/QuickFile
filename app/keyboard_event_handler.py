import logging
from PyQt6.QtCore import Qt, QEvent, QObject
from PyQt6.QtWidgets import QApplication, QLineEdit
from app.translation_manager import translation_manager
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
            (Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier): self.folder_browser.go_up_directory, # Added Backspace
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
            (Qt.Key.Key_E, Qt.KeyboardModifier.ControlModifier): self.application_logic_handler.set_focus_on_path_edit,
        }
        
    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.ShortcutOverride:
            # This event is sent before a shortcut is executed. We can intercept it
            # to prevent shortcuts from firing when a character with a modifier
            # (like AltGr+A for 'ą' in Polish) is being typed.
            if event.modifiers() and event.text():
                event.accept()
                return True

        # If a modal dialog is open, don't process global shortcuts here
        if QApplication.activeModalWidget() is not None:
            return False

        if event.type() == QEvent.Type.KeyPress:
            # The main shortcut system handles QActions. This is for keys
            # that are not standard shortcuts (e.g., Backspace for 'Go Up').
            
            # If the focus is on a text input, we generally want to allow typing.
            # However, we must be careful not to block our own custom key handling.
            if isinstance(QApplication.focusWidget(), QLineEdit):
                # Allow the event to be processed by the QLineEdit first.
                # If it's a shortcut, it will be handled by the QAction system.
                # If it's a regular key press, the QLineEdit will use it.
                # This logic is now simpler because we don't block events.
                pass

            return self.handle_key_event(event)
            
        return super().eventFilter(source, event)

    def handle_key_event(self, event):
        key = event.key()
        modifiers = event.modifiers()
        
        # Check if the focused widget is a text input field.
        # If so, we should not trigger single-key actions like Backspace.
        is_text_input_focused = isinstance(QApplication.focusWidget(), QLineEdit)

        if is_text_input_focused and modifiers == Qt.KeyboardModifier.NoModifier:
             # For simple key presses without modifiers (like 'F2', 'Backspace'),
             # if we are in a text field, we let the text field handle it.
             return False

        action = self.key_actions.get((key, modifiers))
        if action:
            action()
            return True
        
        if self.folder_browser.active_panel_widget:
            active_view = self.folder_browser.active_panel_widget.file_view
            if hasattr(active_view, 'handle_key_event'):
                # Pass the event to the active view (e.g., for navigation like Home/End)
                return active_view.handle_key_event(event)
            
        return False
