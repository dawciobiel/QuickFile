import os
import os
from PyQt6.QtWidgets import QInputDialog, QStyle, QDialog, QMessageBox
from file_operations.archive_manager import UnrarNotInstalledError
from PyQt6.QtGui import QIcon, QKeySequence, QAction
from utils.copy_dialog import CopyDialog
from utils.move_dialog import MoveDialog
from utils.delete_dialog import DeleteDialog # Dodaj import DeleteDialog
from utils.sync_dialog import SyncDialog
from utils.shortcuts_dialog import ShortcutsDialog
from utils.settings_dialog import SettingsDialog


class MenuPanel:
    def __init__(self, main_window):
        self.main_window = main_window
        self.menu_bar = main_window.menuBar()
        self.toolbar = main_window.toolbar
        self.file_manager = main_window.file_manager

        self._create_file_menu()
        self._create_operations_menu()
        self._create_archive_menu()
        self._create_view_menu() # New menu
        self._create_settings_menu()

    def _create_view_menu(self):
        view_menu = self.menu_bar.addMenu("Widok")

        flat_view_action = QAction("Widok płaski", self.main_window)
        flat_view_action.triggered.connect(lambda: self.main_window.folder_browser.set_view_mode("flat"))
        view_menu.addAction(flat_view_action)

        tree_view_action = QAction("Widok drzewa", self.main_window)
        tree_view_action.triggered.connect(lambda: self.main_window.folder_browser.set_view_mode("tree"))
        view_menu.addAction(tree_view_action)

    def _create_settings_menu(self):
        settings_menu = self.menu_bar.addMenu("Ustawienia")
        configure_shortcuts_action = QAction("Skonfiguruj skróty", self.main_window)
        configure_shortcuts_action.triggered.connect(self.open_shortcuts_dialog)
        settings_menu.addAction(configure_shortcuts_action)

        general_settings_action = QAction("Ogólne ustawienia", self.main_window)
        general_settings_action.triggered.connect(self.open_general_settings_dialog)
        settings_menu.addAction(general_settings_action)

    def open_general_settings_dialog(self):
        current_view_mode = self.main_window.settings_manager.get_setting("view_mode")
        dialog = SettingsDialog(self.main_window, current_view_mode)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_view_mode = dialog.get_selected_view_mode()
            if new_view_mode != current_view_mode:
                self.main_window.settings_manager.set_setting("view_mode", new_view_mode)
                self.main_window.folder_browser.set_view_mode(new_view_mode)
                self.main_window.status_bar.showMessage(f"Zmieniono tryb widoku na: {new_view_mode}.")

    def open_shortcuts_dialog(self):
        dialog = ShortcutsDialog(self.main_window, self.main_window.shortcuts_manager.shortcuts)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_shortcuts = dialog.get_shortcuts()
            self.main_window.shortcuts_manager.save_shortcuts(new_shortcuts)

    def _create_file_menu(self):
        self.file_menu = self.menu_bar.addMenu("Plik")

        exit_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton), "Wyjdź", self.main_window)
        exit_action.triggered.connect(self.main_window.close)
        self.file_menu.addAction(exit_action)
        self.main_window.shortcuts_manager.register_action("Wyjdź", exit_action)

    def _create_archive_menu(self):
        archive_menu = self.menu_bar.addMenu("Archiwum")

        create_archive_action = QAction("Utwórz archiwum", self.main_window)
        create_archive_action.triggered.connect(self.create_archive)
        archive_menu.addAction(create_archive_action)
        self.main_window.shortcuts_manager.register_action("Utwórz archiwum", create_archive_action)

        extract_archive_action = QAction("Wypakuj archiwum", self.main_window)
        extract_archive_action.triggered.connect(self.extract_archive)
        archive_menu.addAction(extract_archive_action)
        self.main_window.shortcuts_manager.register_action("Wypakuj archiwum", extract_archive_action)

    def create_archive(self):
        selected_path = self.main_window.folder_browser.current_selected_path
        if not selected_path:
            self.main_window.status_bar.showMessage("Nie wybrano pliku/folderu do archiwizacji.")
            return

        archive_name, ok = QInputDialog.getText(self.main_window, "Utwórz archiwum", "Nazwa archiwum (bez rozszerzenia):")
        if ok and archive_name:
            # Domyślnie tworzymy archiwum w tym samym katalogu
            archive_path = os.path.join(os.path.dirname(selected_path), archive_name + ".zip")
            self.main_window.archive_manager.create_zip_archive(selected_path, archive_path)
            self.main_window.folder_browser.refresh_view()

    def extract_archive(self):
        selected_path = self.main_window.folder_browser.current_selected_path
        if not selected_path or not selected_path.endswith(('.zip', '.tar', '.gz', '.bz2', '.xz', '.rar')):
            self.main_window.status_bar.showMessage("Nie wybrano pliku archiwum do wypakowania.")
            return

        extract_path, ok = QInputDialog.getText(self.main_window, "Wypakuj archiwum", "Ścieżka docelowa:", text=os.path.dirname(selected_path))
        if ok and extract_path:
            if not os.path.exists(extract_path):
                os.makedirs(extract_path)

            try:
                if selected_path.endswith('.zip'):
                    self.main_window.archive_manager.extract_zip_archive(selected_path, extract_path)
                elif selected_path.endswith('.rar'):
                    self.main_window.archive_manager.extract_rar_archive(selected_path, extract_path)
                else:
                    self.main_window.archive_manager.extract_tar_archive(selected_path, extract_path)
                
                self.main_window.folder_browser.refresh_view()

            except UnrarNotInstalledError as e:
                QMessageBox.warning(self.main_window, "Błąd", str(e))
            except Exception as e:
                self.main_window.status_bar.showMessage(f"Błąd podczas wypakowywania: {e}")

    def _create_operations_menu(self):
        operations_menu = self.menu_bar.addMenu("Operacje")
        self.toolbar.addSeparator()

        go_up_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp), "Idź w górę", self.main_window)
        go_up_action.triggered.connect(self.main_window.folder_browser.go_up_directory)
        operations_menu.addAction(go_up_action)
        self.toolbar.addAction(go_up_action)
        self.main_window.shortcuts_manager.register_action("Idź w górę", go_up_action)

        refresh_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload), "Odśwież", self.main_window)
        refresh_action.triggered.connect(self.main_window.folder_browser.refresh_view)
        operations_menu.addAction(refresh_action)
        self.toolbar.addAction(refresh_action)
        self.main_window.shortcuts_manager.register_action("Odśwież", refresh_action)

        operations_menu.addSeparator()
        self.toolbar.addSeparator()

        create_file_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon), "Nowy Plik", self.main_window)
        create_file_action.triggered.connect(self.create_new_file)
        operations_menu.addAction(create_file_action)
        self.toolbar.addAction(create_file_action)
        self.main_window.shortcuts_manager.register_action("Nowy Plik", create_file_action)

        create_directory_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon), "Nowy Folder", self.main_window)
        create_directory_action.triggered.connect(self.create_new_directory)
        operations_menu.addAction(create_directory_action)
        self.toolbar.addAction(create_directory_action)
        self.main_window.shortcuts_manager.register_action("Nowy Folder", create_directory_action)

        operations_menu.addSeparator()
        self.toolbar.addSeparator()

        search_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView), "Szukaj", self.main_window)
        search_action.triggered.connect(self.main_window.search_input.setFocus)
        operations_menu.addAction(search_action)
        self.toolbar.addAction(search_action)
        self.main_window.shortcuts_manager.register_action("Szukaj", search_action)

        operations_menu.addSeparator()
        self.toolbar.addSeparator()

        copy_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileLinkIcon), "Kopiuj", self.main_window)
        copy_action.triggered.connect(self.copy_selected_item)
        operations_menu.addAction(copy_action)
        self.toolbar.addAction(copy_action)
        self.main_window.shortcuts_manager.register_action("Kopiuj", copy_action)

        paste_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon), "Wklej", self.main_window)
        operations_menu.addAction(paste_action)
        self.toolbar.addAction(paste_action)
        self.main_window.shortcuts_manager.register_action("Wklej", paste_action)

        move_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_DirLinkIcon), "Przenieś", self.main_window)
        move_action.triggered.connect(self.move_selected_item) # Zmieniono na move_selected_item
        operations_menu.addAction(move_action)
        self.toolbar.addAction(move_action)
        self.main_window.shortcuts_manager.register_action("Przenieś", move_action)

        rename_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_LineEditClearButton), "Zmień nazwę", self.main_window)
        rename_action.triggered.connect(self.rename_selected_item)
        operations_menu.addAction(rename_action)
        self.toolbar.addAction(rename_action)
        self.main_window.shortcuts_manager.register_action("Zmień nazwę", rename_action)

        delete_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "Usuń", self.main_window)
        delete_action.triggered.connect(self.delete_selected_item)
        operations_menu.addAction(delete_action)
        self.toolbar.addAction(delete_action)
        self.main_window.shortcuts_manager.register_action("Usuń", delete_action)

        compare_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogToParent), "Porównaj", self.main_window)
        compare_action.triggered.connect(self.main_window._compare_selected_items)
        operations_menu.addAction(compare_action)
        self.toolbar.addAction(compare_action)
        self.main_window.shortcuts_manager.register_action("Porównaj", compare_action)

        synchronize_action = QAction(self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_DirLinkIcon), "Synchronizuj", self.main_window)
        synchronize_action.triggered.connect(self.synchronize_directories)
        operations_menu.addAction(synchronize_action)
        self.toolbar.addAction(synchronize_action)
        self.main_window.shortcuts_manager.register_action("Synchronizuj", synchronize_action)

    def synchronize_directories(self):
        left_path = self.main_window.folder_browser.left_panel.model().filePath(self.main_window.folder_browser.current_paths[self.main_window.folder_browser.left_panel])
        right_path = self.main_window.folder_browser.right_panel.model().filePath(self.main_window.folder_browser.current_paths[self.main_window.folder_browser.right_panel])

        dialog = SyncDialog(self.main_window, left_path, right_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            options = dialog.get_options()
            self.main_window.directory_synchronizer.synchronize(left_path, right_path, options)

    def create_new_file(self):
        """Tworzy nowy plik w aktywnym panelu."""
        active_panel = self.main_window.folder_browser.active_panel
        if active_panel:
            current_root_index = self.main_window.folder_browser.current_paths.get(active_panel)
            if current_root_index:
                current_dir = current_root_index
                file_name, ok = QInputDialog.getText(self.main_window, "Nowy Plik", "Nazwa pliku:")
                if ok and file_name:
                    self.file_manager.create_file(current_dir, file_name)
                    self.main_window.folder_browser.refresh_view()  # Odśwież widok po utworzeniu
            else:
                self.main_window.status_bar.showMessage("Nie można określić bieżącego katalogu aktywnego panelu.")
        else:
            self.main_window.status_bar.showMessage("Brak aktywnego panelu.")

    def create_new_directory(self):
        """Tworzy nowy folder w aktywnym panelu."""
        active_panel = self.main_window.folder_browser.active_panel
        if active_panel:
            current_root_index = self.main_window.folder_browser.current_paths.get(active_panel)
            if current_root_index:
                current_dir = current_root_index
                directory_name, ok = QInputDialog.getText(self.main_window, "Nowy Folder", "Nazwa folderu:")
                if ok and directory_name:
                    self.file_manager.create_directory(current_dir, directory_name)
                    self.main_window.folder_browser.refresh_view()  # Odśwież widok po utworzeniu
            else:
                self.main_window.status_bar.showMessage("Nie można określić bieżącego katalogu aktywnego panelu.")
        else:
            self.main_window.status_bar.showMessage("Brak aktywnego panelu.")

    def copy_selected_item(self):
        """Otwiera dialog kopiowania dla zaznaczonego elementu."""
        source_path = self.main_window.folder_browser.current_selected_path
        if not source_path:
            self.main_window.status_bar.showMessage("Nie wybrano żadnego pliku/folderu do skopiowania.")
            return

        # Określenie ścieżki docelowej (nieaktywne panele)
        active_panel = self.main_window.folder_browser.active_panel
        inactive_panel = self.main_window.folder_browser.right_panel if active_panel == self.main_window.folder_browser.left_panel else self.main_window.folder_browser.left_panel
        destination_path = inactive_panel.model().filePath(self.main_window.folder_browser.current_paths[inactive_panel])

        dialog = CopyDialog(self.main_window, source_path, destination_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            options = dialog.get_options()
            self.file_manager.copy_item_with_options(source_path, destination_path, options)

    def move_selected_item(self):
        """Otwiera dialog przenoszenia dla zaznaczonego elementu."""
        source_path = self.main_window.folder_browser.current_selected_path
        if not source_path:
            self.main_window.status_bar.showMessage("Nie wybrano żadnego pliku/folderu do przeniesienia.")
            return

        # Określenie ścieżki docelowej (nieaktywne panele)
        active_panel = self.main_window.folder_browser.active_panel
        inactive_panel = self.main_window.folder_browser.right_panel if active_panel == self.main_window.folder_browser.left_panel else self.main_window.folder_browser.left_panel
        destination_path = inactive_panel.model().filePath(self.main_window.folder_browser.current_paths[inactive_panel])

        dialog = MoveDialog(self.main_window, source_path, destination_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            options = dialog.get_options()
            self.file_manager.move_item_with_options(source_path, destination_path, options)

    def cut_selected_item(self):
        """Kopiuje zaznaczony element z aktywnego panelu w celu jego przeniesienia."""
        selected_path = self.main_window.folder_browser.current_selected_path
        if selected_path:
            self.file_manager.cut_item(selected_path)
        else:
            self.main_window.status_bar.showMessage("Nie wybrano żadnego pliku/folderu do wycięcia.")

    def paste_item_to_current_dir(self):
        """Wkleja element do bieżącego katalogu aktywnego panelu."""
        active_panel = self.main_window.folder_browser.active_panel
        if active_panel:
            current_root_index = self.main_window.folder_browser.current_paths.get(active_panel)
            if current_root_index:
                current_dir = current_root_index
                self.file_manager.paste_item(current_dir)
            else:
                self.main_window.status_bar.showMessage("Nie można określić bieżącego katalogu aktywnego panelu.")
        else:
            self.main_window.status_bar.showMessage("Brak aktywnego panelu.")

    def delete_selected_item(self):
        """Usuwa zaznaczony element z aktywnego panelu."""
        print("MenuPanel: delete_selected_item called") # Dodano komunikat debugujący
        selected_path = self.main_window.folder_browser.current_selected_path
        if not selected_path:
            self.main_window.status_bar.showMessage("Nie wybrano żadnego pliku/folderu do usunięcia.")
            return

        dialog = DeleteDialog(self.main_window, selected_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.file_manager.delete_item_with_confirmation(selected_path)

    def rename_selected_item(self):
        """Zmienia nazwę zaznaczonego elementu."""
        selected_path = self.main_window.folder_browser.current_selected_path
        if selected_path:
            old_name = os.path.basename(selected_path)
            new_name, ok = QInputDialog.getText(self.main_window, "Zmień nazwę", "Nowa nazwa:", text=old_name)
            if ok and new_name:
                self.file_manager.rename_item(selected_path, new_name)
            elif not new_name:
                self.main_window.status_bar.showMessage("Nowa nazwa nie może być pusta.")
        else:
            self.main_window.status_bar.showMessage("Nie wybrano żadnego pliku/folderu do zmiany nazwy.")
