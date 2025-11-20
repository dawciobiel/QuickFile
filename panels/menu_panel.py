import os
from PyQt5.QtWidgets import QAction, QInputDialog, QStyle
from PyQt5.QtGui import QIcon, QKeySequence


class MenuPanel:
    def __init__(self, main_window):
        self.main_window = main_window
        self.menu_bar = main_window.menuBar()
        self.toolbar = main_window.toolbar
        self.file_manager = main_window.file_manager

        self._create_file_menu()
        self._create_operations_menu()

    def _create_file_menu(self):
        file_menu = self.menu_bar.addMenu("Plik")

        # Usunięto akcję "Zapisz"
        # save_action = QAction(self.main_window.style().standardIcon(QStyle.SP_DialogSaveButton), "Zapisz", self.main_window)
        # save_action.setShortcut(QKeySequence.Save)
        # save_action.triggered.connect(self.save_current_file)
        # file_menu.addAction(save_action)
        # self.toolbar.addAction(save_action)

        # file_menu.addSeparator()

        exit_action = QAction(self.main_window.style().standardIcon(QStyle.SP_DialogCancelButton), "Wyjdź", self.main_window)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.main_window.close)
        file_menu.addAction(exit_action)

    def _create_operations_menu(self):
        operations_menu = self.menu_bar.addMenu("Operacje")
        self.toolbar.addSeparator()

        go_up_action = QAction(self.main_window.style().standardIcon(QStyle.SP_ArrowUp), "Idź w górę", self.main_window)
        go_up_action.setShortcut(QKeySequence("Alt+Up"))
        go_up_action.triggered.connect(self.main_window.folder_browser.go_up_directory)
        operations_menu.addAction(go_up_action)
        self.toolbar.addAction(go_up_action)

        refresh_action = QAction(self.main_window.style().standardIcon(QStyle.SP_BrowserReload), "Odśwież", self.main_window)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self.main_window.folder_browser.refresh_view)
        operations_menu.addAction(refresh_action)
        self.toolbar.addAction(refresh_action)

        operations_menu.addSeparator()
        self.toolbar.addSeparator()

        create_file_action = QAction(self.main_window.style().standardIcon(QStyle.SP_FileIcon), "Nowy Plik", self.main_window)
        create_file_action.setShortcut(QKeySequence("Ctrl+N"))
        create_file_action.triggered.connect(self.create_new_file)
        operations_menu.addAction(create_file_action)
        self.toolbar.addAction(create_file_action)

        create_directory_action = QAction(self.main_window.style().standardIcon(QStyle.SP_DirIcon), "Nowy Folder", self.main_window)
        create_directory_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        create_directory_action.triggered.connect(self.create_new_directory)
        operations_menu.addAction(create_directory_action)
        self.toolbar.addAction(create_directory_action)

        operations_menu.addSeparator()
        self.toolbar.addSeparator()

        search_action = QAction(self.main_window.style().standardIcon(QStyle.SP_FileDialogDetailedView), "Szukaj", self.main_window)
        search_action.setShortcut(QKeySequence("Ctrl+F"))
        search_action.triggered.connect(self.main_window.search_input.setFocus)
        operations_menu.addAction(search_action)
        self.toolbar.addAction(search_action)

        operations_menu.addSeparator()
        self.toolbar.addSeparator()

        copy_action = QAction(self.main_window.style().standardIcon(QStyle.SP_FileLinkIcon), "Kopiuj", self.main_window)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.copy_selected_item)
        operations_menu.addAction(copy_action)
        self.toolbar.addAction(copy_action)

        paste_action = QAction(self.main_window.style().standardIcon(QStyle.SP_FileIcon), "Wklej", self.main_window)
        paste_action.setShortcut(QKeySequence.Paste)
        paste_action.triggered.connect(self.paste_item_to_current_dir)
        operations_menu.addAction(paste_action)
        self.toolbar.addAction(paste_action)

        move_action = QAction(self.main_window.style().standardIcon(QStyle.SP_DirLinkIcon), "Przenieś", self.main_window)
        move_action.setShortcut(QKeySequence.Cut)
        move_action.triggered.connect(self.cut_selected_item)
        operations_menu.addAction(move_action)
        self.toolbar.addAction(move_action)

        rename_action = QAction(self.main_window.style().standardIcon(QStyle.SP_LineEditClearButton), "Zmień nazwę", self.main_window)
        rename_action.setShortcut(QKeySequence("F2"))
        rename_action.triggered.connect(self.rename_selected_item)
        operations_menu.addAction(rename_action)
        self.toolbar.addAction(rename_action)

        delete_action = QAction(self.main_window.style().standardIcon(QStyle.SP_TrashIcon), "Usuń", self.main_window)
        delete_action.setShortcut(QKeySequence.Delete)
        delete_action.triggered.connect(self.delete_selected_item)
        operations_menu.addAction(delete_action)
        self.toolbar.addAction(delete_action)

    def save_current_file(self):
        # Ta metoda nie jest już potrzebna, ponieważ wewnętrzny edytor został usunięty
        pass

    def create_new_file(self):
        """Tworzy nowy plik w aktywnym panelu."""
        active_panel = self.main_window.folder_browser.active_panel
        if active_panel:
            current_root_index = self.main_window.folder_browser.current_paths.get(active_panel)
            if current_root_index:
                current_dir = active_panel.model().filePath(current_root_index)
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
                current_dir = active_panel.model().filePath(current_root_index)
                directory_name, ok = QInputDialog.getText(self.main_window, "Nowy Folder", "Nazwa folderu:")
                if ok and directory_name:
                    self.file_manager.create_directory(current_dir, directory_name)
                    self.main_window.folder_browser.refresh_view()  # Odśwież widok po utworzeniu
            else:
                self.main_window.status_bar.showMessage("Nie można określić bieżącego katalogu aktywnego panelu.")
        else:
            self.main_window.status_bar.showMessage("Brak aktywnego panelu.")

    def copy_selected_item(self):
        """Kopiuje zaznaczony element z aktywnego panelu."""
        selected_path = self.main_window.folder_browser.current_selected_path
        if selected_path:
            self.file_manager.copy_item(selected_path)
        else:
            self.main_window.status_bar.showMessage("Nie wybrano żadnego pliku/folderu do skopiowania.")

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
                current_dir = active_panel.model().filePath(current_root_index)
                self.file_manager.paste_item(current_dir)
            else:
                self.main_window.status_bar.showMessage("Nie można określić bieżącego katalogu aktywnego panelu.")
        else:
            self.main_window.status_bar.showMessage("Brak aktywnego panelu.")

    def delete_selected_item(self):
        """Usuwa zaznaczony element z aktywnego panelu."""
        selected_path = self.main_window.folder_browser.current_selected_path
        if selected_path:
            self.file_manager.delete_item(selected_path)
        else:
            self.main_window.status_bar.showMessage("Nie wybrano żadnego pliku/folderu do usunięcia.")

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
