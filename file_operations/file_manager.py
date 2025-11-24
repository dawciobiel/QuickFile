import logging
import os
import shutil
from utils.dialogs import show_error_message


class FileManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.clipboard = None
        self.is_cut_operation = False

    def copy_item_with_options(self, source_path, destination_path, options):
        """Kopiuje plik/folder z opcjami."""
        if not source_path or not os.path.exists(source_path):
            show_error_message(self.main_window, "Błąd kopiowania", f"Ścieżka źródłowa '{source_path}' jest nieprawidłowa lub nie istnieje.")
            return

        if not destination_path or not os.path.exists(destination_path):
            show_error_message(self.main_window, "Błąd kopiowania", f"Ścieżka docelowa '{destination_path}' nie istnieje.")
            return

        try:
            base_name = os.path.basename(source_path)
            destination_full_path = os.path.join(destination_path, base_name)

            if os.path.exists(destination_full_path) and not options.get("overwrite"):
                show_error_message(self.main_window, "Błąd kopiowania", f"Plik '{base_name}' już istnieje w lokalizacji docelowej. Zaznacz opcję 'Nadpisz', aby go zastąpić.")
                return

            copy_function = shutil.copy2 if options.get("preserve_timestamp") else shutil.copy
            
            if os.path.isdir(source_path):
                if os.path.exists(destination_full_path):
                    shutil.rmtree(destination_full_path)
                shutil.copytree(source_path, destination_full_path, copy_function=copy_function)
            else:
                copy_function(source_path, destination_full_path)

            self.main_window.status_bar.showMessage(f"Skopiowano '{base_name}' do '{destination_path}'")
            self.main_window.folder_browser.refresh_view()

        except Exception as e:
            logging.exception(f"Error copying item from {source_path} to {destination_path}: {e}")
            show_error_message(self.main_window, "Błąd kopiowania", str(e))

    def move_item_with_options(self, source_path, destination_path, options):
        """Przenosi plik/folder z opcjami."""
        if not source_path or not os.path.exists(source_path):
            show_error_message(self.main_window, "Błąd przenoszenia", f"Ścieżka źródłowa '{source_path}' jest nieprawidłowa lub nie istnieje.")
            return

        if not destination_path or not os.path.exists(destination_path):
            show_error_message(self.main_window, "Błąd przenoszenia", f"Ścieżka docelowa '{destination_path}' nie istnieje.")
            return

        try:
            base_name = os.path.basename(source_path)
            destination_full_path = os.path.join(destination_path, base_name)

            if os.path.exists(destination_full_path):
                if not options.get("overwrite"):
                    show_error_message(self.main_window, "Błąd przenoszenia", f"Plik '{base_name}' już istnieje w lokalizacji docelowej. Zaznacz opcję 'Nadpisz', aby go zastąpić.")
                    return
                else:
                    if os.path.isdir(destination_full_path):
                        shutil.rmtree(destination_full_path)
                    else:
                        os.remove(destination_full_path)

            shutil.move(source_path, destination_full_path)
            self.main_window.status_bar.showMessage(f"Przeniesiono '{base_name}' do '{destination_full_path}'")
            self.main_window.folder_browser.refresh_view()

        except Exception as e:
            logging.exception(f"Error moving item from {source_path} to {destination_path}: {e}")
            show_error_message(self.main_window, "Błąd przenoszenia", str(e))

    def delete_item_with_confirmation(self, item_path):
        """Usuwa plik/folder po potwierdzeniu."""
        if not item_path or not os.path.exists(item_path):
            show_error_message(self.main_window, "Błąd usuwania", f"Ścieżka '{item_path}' jest nieprawidłowa lub nie istnieje.")
            return

        try:
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
            self.main_window.status_bar.showMessage(f"Usunięto: {item_path}")
            self.main_window.folder_browser.refresh_view()
        except Exception as e:
            logging.exception(f"Error deleting item {item_path}: {e}")
            show_error_message(self.main_window, "Błąd usuwania", str(e))

    def copy_item(self, path):
        if not path or not os.path.exists(path):
            show_error_message(self.main_window, "Błąd kopiowania", f"Ścieżka '{path}' jest nieprawidłowa lub nie istnieje.")
            return
        self.clipboard = path
        self.is_cut_operation = False
        self.main_window.status_bar.showMessage(f"Skopiowano: {path}")

    def cut_item(self, path):
        if not path or not os.path.exists(path):
            show_error_message(self.main_window, "Błąd wycinania", f"Ścieżka '{path}' jest nieprawidłowa lub nie istnieje.")
            return
        self.clipboard = path
        self.is_cut_operation = True
        self.main_window.status_bar.showMessage(f"Wycięto: {path}")

    def paste_item(self, destination_path):
        if not self.clipboard:
            show_error_message(self.main_window, "Błąd wklejania", "Schowek jest pusty.")
            return

        if not os.path.exists(destination_path):
            show_error_message(self.main_window, "Błąd wklejania", f"Ścieżka docelowa '{destination_path}' nie istnieje.")
            return

        try:
            base_name = os.path.basename(self.clipboard)
            destination_full_path = os.path.join(destination_path, base_name)

            if self.is_cut_operation:
                shutil.move(self.clipboard, destination_full_path)
                self.main_window.status_bar.showMessage(f"Przeniesiono '{base_name}' do '{destination_full_path}'")
            else:
                if os.path.isdir(self.clipboard):
                    shutil.copytree(self.clipboard, destination_full_path)
                else:
                    shutil.copy2(self.clipboard, destination_full_path)
                self.main_window.status_bar.showMessage(f"Skopiowano '{base_name}' do '{destination_full_path}'")

        except Exception as e:
            logging.exception(f"Error pasting item to {destination_path}: {e}")
            show_error_message(self.main_window, "Błąd wklejania", str(e))
        finally:
            self.clipboard = None
            self.is_cut_operation = False

    def delete_item(self, path):
        if not path or not os.path.exists(path):
            show_error_message(self.main_window, "Błąd usuwania", f"Ścieżka '{path}' jest nieprawidłowa lub nie istnieje.")
            return

        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            self.main_window.status_bar.showMessage(f"Usunięto: {path}")
        except Exception as e:
            logging.exception(f"Error deleting item {path}: {e}")
            show_error_message(self.main_window, "Błąd usuwania", str(e))

    def rename_item(self, old_path, new_name):
        if not old_path or not os.path.exists(old_path):
            show_error_message(self.main_window, "Błąd zmiany nazwy", f"Ścieżka '{old_path}' jest nieprawidłowa lub nie istnieje.")
            return

        if not new_name:
            show_error_message(self.main_window, "Błąd zmiany nazwy", "Nowa nazwa nie może być pusta.")
            return

        try:
            directory = os.path.dirname(old_path)
            new_path = os.path.join(directory, new_name)
            os.rename(old_path, new_path)
            self.main_window.status_bar.showMessage(f"Zmieniono nazwę na: {new_name}")
        except Exception as e:
            logging.exception(f"Error renaming item {old_path} to {new_name}: {e}")
            show_error_message(self.main_window, "Błąd zmiany nazwy", str(e))

    def create_file(self, directory, file_name):
        """Tworzy nowy, pusty plik."""
        if not directory or not os.path.exists(directory):
            show_error_message(self.main_window, "Błąd tworzenia pliku", f"Katalog '{directory}' jest nieprawidłowy lub nie istnieje.")
            return

        if not file_name:
            show_error_message(self.main_window, "Błąd tworzenia pliku", "Nazwa pliku nie może być pusta.")
            return

        file_path = os.path.join(directory, file_name)
        if os.path.exists(file_path):
            show_error_message(self.main_window, "Błąd tworzenia pliku", f"Plik '{file_name}' już istnieje.")
            return

        try:
            with open(file_path, 'w') as f:
                pass  # Tworzy pusty plik
            self.main_window.status_bar.showMessage(f"Utworzono plik: {file_path}")
        except Exception as e:
            logging.exception(f"Error creating file {file_path}: {e}")
            show_error_message(self.main_window, "Błąd tworzenia pliku", str(e))

    def create_directory(self, parent_directory, directory_name):
        """Tworzy nowy folder."""
        if not parent_directory or not os.path.exists(parent_directory):
            show_error_message(self.main_window, "Błąd tworzenia folderu", f"Katalog nadrzędny '{parent_directory}' jest nieprawidłowy lub nie istnieje.")
            return

        if not directory_name:
            show_error_message(self.main_window, "Błąd tworzenia folderu", "Nazwa folderu nie może być pusta.")
            return

        directory_path = os.path.join(parent_directory, directory_name)
        if os.path.exists(directory_path):
            show_error_message(self.main_window, "Błąd tworzenia folderu", f"Folder '{directory_name}' już istnieje.")
            return

        try:
            os.makedirs(directory_path)
            self.main_window.status_bar.showMessage(f"Utworzono folder: {directory_path}")
        except Exception as e:
            logging.exception(f"Error creating directory {directory_path}: {e}")
            show_error_message(self.main_window, "Błąd tworzenia folderu", str(e))

    def search_files(self, root_path, pattern):
        """Wyszukuje pliki i foldery pasujące do wzorca w podanej ścieżce."""
        if not root_path or not os.path.exists(root_path):
            show_error_message(self.main_window, "Błąd wyszukiwania", f"Ścieżka początkowa '{root_path}' jest nieprawidłowa lub nie istnieje.")
            return []

        found_items = []
        for dirpath, dirnames, filenames in os.walk(root_path):
            for name in dirnames + filenames:
                if pattern.lower() in name.lower():
                    found_items.append(os.path.join(dirpath, name))
        
        if found_items:
            self.main_window.status_bar.showMessage(f"Znaleziono {len(found_items)} elementów dla '{pattern}'.")
        else:
            self.main_window.status_bar.showMessage(f"Nie znaleziono elementów dla '{pattern}'.")
        
        return found_items
