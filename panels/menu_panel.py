import os
from PyQt5.QtWidgets import QAction, QInputDialog


class MenuPanel:
    def __init__(self, main_window):
        self.main_window = main_window
        self.menu_bar = main_window.menuBar()
        self.file_manager = main_window.file_manager

        self._create_file_menu()
        self._create_operations_menu()

    def _create_file_menu(self):
        file_menu = self.menu_bar.addMenu("Plik")

        exit_action = QAction("Wyjdź", self.main_window)
        exit_action.triggered.connect(self.main_window.close)
        file_menu.addAction(exit_action)

    def _create_operations_menu(self):
        operations_menu = self.menu_bar.addMenu("Operacje")

        copy_action = QAction("Kopiuj", self.main_window)
        paste_action = QAction("Wklej", self.main_window)
        move_action = QAction("Przenieś", self.main_window)
        rename_action = QAction("Zmień nazwę", self.main_window)
        delete_action = QAction("Usuń", self.main_window)

        copy_action.triggered.connect(self.copy_selected_item)
        paste_action.triggered.connect(self.paste_item_to_current_dir)
        move_action.triggered.connect(self.cut_selected_item)
        rename_action.triggered.connect(self.rename_selected_item)
        delete_action.triggered.connect(self.delete_selected_item)

        operations_menu.addAction(copy_action)
        operations_menu.addAction(paste_action)
        operations_menu.addAction(move_action)
        operations_menu.addAction(rename_action)
        operations_menu.addAction(delete_action)

    def copy_selected_item(self):
        """Kopiuje zaznaczony element z aktywnego panelu."""
        selected_path = self.main_window.folder_browser.current_selected_path
        if selected_path:
            self.file_manager.copy_item(selected_path)
            self.main_window.status_bar.showMessage(f"Skopiowano: {selected_path}")
        else:
            self.main_window.status_bar.showMessage("Nie wybrano żadnego pliku/folderu do skopiowania.")

    def cut_selected_item(self):
        """Kopiuje zaznaczony element z aktywnego panelu w celu jego przeniesienia."""
        selected_path = self.main_window.folder_browser.current_selected_path
        if selected_path:
            self.file_manager.cut_item(selected_path)
            self.main_window.status_bar.showMessage(f"Wycięto: {selected_path}")
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
                self.main_window.status_bar.showMessage(f"Wklejono do: {current_dir}")
            else:
                self.main_window.status_bar.showMessage("Nie można określić bieżącego katalogu aktywnego panelu.")
        else:
            self.main_window.status_bar.showMessage("Brak aktywnego panelu.")

    def delete_selected_item(self):
        """Usuwa zaznaczony element z aktywnego panelu."""
        selected_path = self.main_window.folder_browser.current_selected_path
        if selected_path:
            self.file_manager.delete_item(selected_path)
            self.main_window.status_bar.showMessage(f"Usunięto: {selected_path}")
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
                self.main_window.status_bar.showMessage(f"Zmieniono nazwę z '{old_name}' na '{new_name}'")
            elif not new_name:
                self.main_window.status_bar.showMessage("Nowa nazwa nie może być pusta.")
        else:
            self.main_window.status_bar.showMessage("Nie wybrano żadnego pliku/folderu do zmiany nazwy.")
