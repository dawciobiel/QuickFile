from PyQt6.QtCore import Qt, QEvent, QObject
from PyQt6.QtWidgets import QApplication

from app.application_logic_handler import ApplicationLogicHandler
from app.translation_manager import translation_manager
from browser.folder_browser import FolderBrowser


class KeyboardEventManager(QObject):
    def __init__(self, main_window, application_logic_handler: ApplicationLogicHandler, folder_browser: FolderBrowser):
        super().__init__(main_window)
        self.main_window = main_window
        self.application_logic_handler = application_logic_handler
        self.folder_browser = folder_browser

        # Explicitly handle global shortcuts here to ensure they work reliably
        # regardless of focus or QAction context issues.
        self.key_actions = {
            (Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier): self.folder_browser.switch_active_panel,
            (Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier): self.folder_browser.go_up_directory,
            (Qt.Key.Key_F1, Qt.KeyboardModifier.NoModifier): lambda: self.main_window.status_bar.showMessage(translation_manager.translate("KeyboardEventManager", "F1: Help (not implemented)")),
            (Qt.Key.Key_F2, Qt.KeyboardModifier.NoModifier): self.application_logic_handler.rename_selected_item,
            (Qt.Key.Key_F3, Qt.KeyboardModifier.NoModifier): self.application_logic_handler._handle_f3_key,
            (Qt.Key.Key_F4, Qt.KeyboardModifier.NoModifier): self.application_logic_handler._handle_f4_key,
            # noinspection PyTypeChecker
            (Qt.Key.Key_F4, Qt.KeyboardModifier.ShiftModifier): self.application_logic_handler.create_new_file,
            (Qt.Key.Key_F5, Qt.KeyboardModifier.NoModifier): self.application_logic_handler.copy_selected_item,
            (Qt.Key.Key_F6, Qt.KeyboardModifier.NoModifier): self.application_logic_handler.move_selected_item,
            (Qt.Key.Key_F7, Qt.KeyboardModifier.NoModifier): self.application_logic_handler.create_new_directory,
            (Qt.Key.Key_F8, Qt.KeyboardModifier.NoModifier): self.application_logic_handler.delete_selected_item,
            (Qt.Key.Key_F9, Qt.KeyboardModifier.NoModifier): self.application_logic_handler.compare_selected_items,
            (Qt.Key.Key_F10, Qt.KeyboardModifier.NoModifier): self.main_window.close,
            (Qt.Key.Key_E, Qt.KeyboardModifier.ControlModifier): self.application_logic_handler.set_focus_on_path_edit,

            # Handle Numpad '+' key
            (Qt.Key.Key_Plus, Qt.KeyboardModifier.KeypadModifier): self.application_logic_handler.show_select_dialog,

            # Global shortcuts restored to ensure functionality
            (Qt.Key.Key_T, Qt.KeyboardModifier.ControlModifier): self.application_logic_handler.new_tab,
            (Qt.Key.Key_W, Qt.KeyboardModifier.ControlModifier): self.application_logic_handler.close_tab,
            (Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier): self.application_logic_handler.start_file_search,
            (Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier): self.application_logic_handler.compare_selected_items,
            (Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier): self.application_logic_handler.open_favorites_dialog,
            (Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier): self.application_logic_handler.refresh_all_views,
            (Qt.Key.Key_Space, Qt.KeyboardModifier.ControlModifier): self.application_logic_handler.calculate_directory_size,
        }
        
    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.ShortcutOverride:
            if event.modifiers() and event.text():
                event.accept()
                return True

        if QApplication.activeModalWidget() is not None:
            return False

        if event.type() == QEvent.Type.KeyPress:
            was_handled = self.handle_key_event(event)
            if was_handled:
                event.accept()
                return True

        return super().eventFilter(source, event)

    def handle_key_event(self, event):
        key = event.key()
        modifiers = event.modifiers()

        action = self.key_actions.get((key, modifiers))
        if action:
            action()
            return True

        # Fallback to panel-specific key handling if no global shortcut was found
        if self.folder_browser.active_panel_widget:
            active_view = self.folder_browser.active_panel_widget.file_view
            if hasattr(active_view, 'handle_key_event'):
                return active_view.handle_key_event(event)
            
        return False
