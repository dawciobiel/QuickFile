import os
import shutil


class FileManager:
    def __init__(self):
        self.clipboard = None  # Przechowuje ścieżkę do skopiowania/wycięcia
        self.is_cut_operation = False

    def copy_item(self, path):
        """Kopiuje ścieżkę do schowka."""
        if not path or not os.path.exists(path):
            print(f"Błąd: Ścieżka '{path}' jest nieprawidłowa lub nie istnieje.")
            return
        self.clipboard = path
        self.is_cut_operation = False
        print(f"Skopiowano do schowka: {self.clipboard}")

    def cut_item(self, path):
        """Kopiuje ścieżkę do schowka w celu jej przeniesienia."""
        if not path or not os.path.exists(path):
            print(f"Błąd: Ścieżka '{path}' jest nieprawidłowa lub nie istnieje.")
            return
        self.clipboard = path
        self.is_cut_operation = True
        print(f"Wycięto do schowka: {self.clipboard}")

    def paste_item(self, destination_path):
        """Wkleja plik/folder ze schowka do nowej lokalizacji."""
        if not self.clipboard:
            print("Schowek jest pusty.")
            return

        if not os.path.exists(destination_path):
            print(f"Błąd: Ścieżka docelowa '{destination_path}' nie istnieje.")
            return

        try:
            # Budowanie pełnej ścieżki docelowej
            base_name = os.path.basename(self.clipboard)
            destination_full_path = os.path.join(destination_path, base_name)

            # Przenoszenie lub kopiowanie
            if self.is_cut_operation:
                shutil.move(self.clipboard, destination_full_path)
                print(f"Przeniesiono '{self.clipboard}' do '{destination_full_path}'")
            else:
                if os.path.isdir(self.clipboard):
                    shutil.copytree(self.clipboard, destination_full_path)
                else:
                    shutil.copy2(self.clipboard, destination_full_path)
                print(f"Wklejono '{self.clipboard}' do '{destination_full_path}'")

        except Exception as e:
            print(f"Błąd podczas wklejania: {e}")
        finally:
            # Wyczyść schowek po operacji
            self.clipboard = None
            self.is_cut_operation = False

    def delete_item(self, path):
        """Usuwa plik lub folder."""
        if not path or not os.path.exists(path):
            print(f"Błąd: Ścieżka '{path}' jest nieprawidłowa lub nie istnieje.")
            return

        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            print(f"Usunięto: {path}")
        except Exception as e:
            print(f"Błąd podczas usuwania: {e}")

    def rename_item(self, old_path, new_name):
        """Zmienia nazwę pliku lub folderu."""
        if not old_path or not os.path.exists(old_path):
            print(f"Błąd: Ścieżka '{old_path}' jest nieprawidłowa lub nie istnieje.")
            return

        if not new_name:
            print("Błąd: Nowa nazwa nie może być pusta.")
            return

        try:
            directory = os.path.dirname(old_path)
            new_path = os.path.join(directory, new_name)
            os.rename(old_path, new_path)
            print(f"Zmieniono nazwę z '{old_path}' na '{new_path}'")
        except Exception as e:
            print(f"Błąd podczas zmiany nazwy: {e}")
