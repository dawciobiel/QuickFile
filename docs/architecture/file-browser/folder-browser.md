# Folder browser

Aby stworzyć menadżer plików z dwoma panelami w Pythonie z użyciem PyQt lub PySide, warto zastosować odpowiednią
strukturę opartą na kontenerach takich jak `QSplitter`. Wprowadzenie funkcjonalności aktywnego panelu i globalnej
zmiennej do śledzenia aktualnie wybranego pliku/folderu można zrealizować w następujący sposób:

### Koncepcja:

1. **Struktura paneli**:
    - Użyj `QSplitter`, aby podzielić interfejs na dwa panele (`QTreeView`, `QListView` lub inny widok plików).

2. **Aktywność panelu**:
    - Dodaj mechanizm do wykrywania aktywnego panelu (`focusInEvent` lub `QFocusEvent`).
    - Ustawiaj zmienną w klasie `FileBrowser`, która przechowuje referencję do aktywnego panelu.

3. **Globalna zmienna aktualnie wybranego pliku**:
    - Dodaj zmienną w klasie `FileBrowser`, która śledzi ścieżkę wybranego pliku/folderu.
    - Nasłuchuj zdarzeń zmiany selekcji w panelach i aktualizuj tę zmienną.

### Przykładowa implementacja

```python
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeView, QFileSystemModel, QSplitter, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QModelIndex


class FileBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Menadżer Plików")

        # Globalne pola
        self.active_panel = None  # Wskaźnik na aktywny panel
        self.current_selected_path = None  # Ścieżka aktualnie wybranego pliku/folderu

        # Ustawienie widoków plików
        self.left_panel = self.create_file_view()
        self.right_panel = self.create_file_view()

        # Dodanie paneli do splittera
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.right_panel)

        # Layout główny
        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(splitter)
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Ustawienie lewego panelu jako aktywnego na starcie
        self.set_active_panel(self.left_panel)

    def create_file_view(self):
        # Model systemu plików
        model = QFileSystemModel()
        model.setRootPath("")  # Ustaw root katalogu

        # Widok plików
        view = QTreeView()
        view.setModel(model)
        view.setRootIndex(model.index(""))  # Ustawienie początkowego folderu

        # Obsługa zdarzeń
        view.selectionModel().currentChanged.connect(self.update_current_selected_path)
        view.installEventFilter(self)  # Monitorowanie aktywności

        return view

    def set_active_panel(self, panel):
        """Ustaw aktywny panel"""
        self.active_panel = panel

    def update_current_selected_path(self, current: QModelIndex, previous: QModelIndex):
        """Aktualizuj wybraną ścieżkę"""
        if current.isValid():
            self.current_selected_path = current.model().filePath(current)
            print(f"Aktualnie wybrana ścieżka: {self.current_selected_path}")

    def eventFilter(self, source, event):
        """Wykrywanie aktywnego panelu"""
        if event.type() == event.FocusIn and (source == self.left_panel or source == self.right_panel):
            self.set_active_panel(source)
            print(f"Aktywny panel: {'lewy' if source == self.left_panel else 'prawy'}")
        return super().eventFilter(source, event)


if __name__ == "__main__":
    app = QApplication([])
    window = FileBrowser()
    window.resize(800, 600)
    window.show()
    app.exec_()
```

### Wyjaśnienie działania:

1. **Struktura paneli**:
    - Dwa `QTreeView` są dodawane do `QSplitter`, co pozwala na ich łatwe przesuwanie i dynamiczne dostosowanie
      rozmiarów.

2. **Mechanizm aktywności panelu**:
    - `eventFilter` nasłuchuje zdarzenia `FocusIn`, co pozwala określić, który panel jest aktywny.

3. **Śledzenie wybranego pliku/folderu**:
    - `currentChanged` w `QTreeView` jest używane do monitorowania zmiany zaznaczenia w panelach. Aktualizowana jest
      zmienna `current_selected_path`.

4. **Globalne pola**:
    - `self.active_panel` przechowuje referencję do aktualnie aktywnego panelu.
    - `self.current_selected_path` przechowuje ścieżkę aktualnie wybranego pliku/folderu.

### Możliwe rozszerzenia:

- Dodanie obsługi klawiatury (np. kopiowanie, wklejanie plików).
- Podświetlanie aktywnego panelu (np. zmiana ramki wokół aktywnego widoku).
- Obsługa przeciągania i upuszczania pomiędzy panelami.