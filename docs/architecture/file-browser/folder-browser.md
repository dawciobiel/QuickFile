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

## Zaznaczanie klawiszem `Insert`

`FlatFileView` (wtyczka `org.quickfile.flat_view`) obsługuje `Insert` w
`handle_key_event`:

1. bieżący wiersz jest przełączany w zbiorze `insert_selected_items`
   (wiersz `..` jest pomijany),
2. kursor **natychmiast** przechodzi o jeden wiersz w dół; na ostatnim wierszu
   pozostaje bez zmian.

Przełączenie i przesunięcie muszą być synchroniczne. Odroczenie przesunięcia
przez `QTimer.singleShot` powodowało, że dwa szybkie naciśnięcia przełączały
ten sam wiersz (drugie zdejmowało zaznaczenie), a oba odroczone przesunięcia
liczyły cel od tego samego, jeszcze niezmienionego wiersza. Kursor jechał
w dół, ale elementy nie zostawały zaznaczone. Kontrakt pilnuje
`tests/unit/test_flat_view_insert_navigation.py`.

## Otwieranie klawiszem `Enter`

`AbstractFileView._handle_common_key_events` rozdziela `Enter`/`Return` na
dwie akcje:

* katalog (także wiersz `..`) — jak dotychczas, czyli wejście do katalogu
  przez `doubleClicked`,
* plik — sygnał `file_open_requested(path)`, który host podłącza do
  `ApplicationLogicHandler.open_file_with_system_default`. Plik jest
  uruchamiany programem skojarzonym z jego typem w systemie operacyjnym
  (`os.startfile` na Windows, `open` na macOS, `xdg-open` na Linuksie).

Dwuklik i `Enter` otwierają plik programem skojarzonym w systemie
operacyjnym. Domyślna konfiguracja
(`resources/config/default_file_associations.json`, wersja 2) kieruje pliki
tekstowe i obrazy do `system_default`. Konfiguracje w wersji 1 są przy
starcie migrowane: wpisy `Text Files` i `Images` z akcją `internal_viewer`
zmieniają akcję na `system_default`, a wpisy niestandardowe pozostają bez
zmian. Wbudowany podgląd i edytor nadal są dostępne przez `F3`/`F4` oraz menu,
a w `~/.config/QuickFile/file_associations.json` można przywrócić
`internal_viewer` lub `internal_editor`. Pliki spoza listy skojarzeń (np.
wideo, audio, archiwa) trafiają do `default_action`, czyli również do programu
skojarzonego w systemie — film zostanie otwarty systemowym odtwarzaczem.

Kontrakt pilnuje `tests/unit/test_flat_view_enter.py`,
`tests/unit/test_open_file_system_default.py` oraz
`tests/unit/test_file_association_manager.py`.

## Pole ścieżki (`PanelWidget.path_edit`)

Pole ścieżki to `PathLineEdit`, czyli `QLineEdit` z jednym dodatkowym
zachowaniem przy wklejaniu.

* `Ctrl+L` (`view.focus_path`) ustawia fokus na polu aktywnego panelu i zaznacza
  całą ścieżkę, więc `Ctrl+V` zastępuje ją w całości. Wklejanie w polu ścieżki
  nie może uruchamiać żadnej innej akcji.
* Wklejenie ścieżki absolutnej, gdy tekst przed kursorem kończy się separatorem
  (np. użytkownik wpisał `/`), nie może zostawić `//` na początku pola: wynik
  wklejenia ma dokładnie jeden wiodący `/`.
* Zatwierdzenie pola (`Enter`, `returnPressed`) normalizuje tekst **przed**
  sprawdzeniem ścieżki: powtarzające się separatory są zwijane (`//tmp//x` →
  `/tmp/x`), `~` jest rozwijane, a tekst przycinany. Dopiero znormalizowana
  ścieżka trafia do `file_view.set_path()`. Po nawigacji pole pokazuje tę samą
  postać przez `_on_path_changed`.
* Normalizacja nie zmienia semantyki ścieżek: nie rozwiązuje `..`, nie zmienia
  ścieżek względnych i nie dotyka prefiksu UNC na Windows.
* Nieistniejąca ścieżka nadal kończy się `set_error_state()` z
  znormalizowanym tekstem.

Kontrakt pilnuje `tests/unit/test_path_edit.py`.