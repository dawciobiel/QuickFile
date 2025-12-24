# Postępy prac z Gemini AI

## Data: 2025-12-23 (Aktualizacja 3)

### Postępy prac:
- **Naprawa obsługi wielu plików (Insert)**:
    - Naprawiono błąd, w którym kopiowany lub przenoszony był tylko jeden plik, mimo zaznaczenia wielu (np. za pomocą klawisza `Insert`).
    - Zaktualizowano `DialogHandler`, aby przekazywał pełną listę zaznaczonych ścieżek do dialogów `CopyDialog` i `MoveDialog`.
    - Dostosowano `CopyDialog` i `MoveDialog` do obsługi listy plików zamiast pojedynczej ścieżki.
    - Dodano metodę `move_items_batch` w `FileManager` do wsadowego przenoszenia plików z obsługą paska postępu, anulowania i pauzy.

## Data: 2025-12-23 (Aktualizacja 2)

### Postępy prac:
- **Pauza i wznowienie operacji w tle**:
    - Rozszerzono `BackgroundTaskManager` o klasę `TaskContext`, która obsługuje zarówno anulowanie, jak i pauzowanie zadań.
    - Zaimplementowano metody `pause()` i `resume()` w `TaskContext` przy użyciu `QMutex` i `QWaitCondition`.
    - Zaktualizowano `FileManager`, aby sprawdzał stan pauzy w pętlach kopiowania plików (`task_context.wait_if_paused()`).
    - Dodano przycisk "Pauza" (zmieniający się na "Wznów") do dialogów `CopyDialog` i `MoveDialog`.

## Data: 2025-12-23 (Aktualizacja 1)

### Postępy prac:
- **Anulowanie operacji w tle**:
    - Zaimplementowano mechanizm anulowania operacji kopiowania, przenoszenia i usuwania plików.
    - Dodano klasę `CancellationToken` w `BackgroundTaskManager` do zarządzania stanem anulowania.
    - Zmodyfikowano `FileManager` (metody `copy_item_with_options`, `move_item_with_options`, `delete_items_batch`), aby obsługiwały przerywanie operacji i czyszczenie niepełnych plików.
    - Zaktualizowano dialogi `CopyDialog` i `MoveDialog`, podłączając przycisk "Anuluj" do nowej logiki.

## Data: 2025-12-23

### Postępy prac:
- **Wielka refaktoryzacja UI**:
    - Zmigrowano `MainWindow`, `FolderBrowser` oraz dialogi (`Settings`, `Search`, `Shortcuts`, `Sync`, `About`, `Properties`, `Delete`, `Copy`, `Move`) do plików `.ui` z Qt Designer.
    - Proces wymagał cofnięcia się do stabilnej wersji i ponownego, kontrolowanego wdrożenia zmian, co pozwoliło na ustabilizowanie aplikacji.
- **Naprawa błędów**:
    - Rozwiązano liczne błędy `AttributeError` wynikające z niedopasowania kodu do nowej struktury UI.
    - Naprawiono krytyczny błąd `SIGSEGV` (segmentation fault) występujący przy zamykaniu aplikacji poprzez prawidłowe usuwanie globalnego filtra zdarzeń.
    - Poprawiono logikę ładowania ustawień paneli, aby uniknąć duplikowania kart przy starcie.
- **Nowe funkcje i ulepszenia**:
    - **Zakładki w panelach**: Zaimplementowano pełną obsługę wielu kart (zakładek), w tym ich zapisywanie i odtwarzanie przy ponownym uruchomieniu aplikacji.
    - **Skróty do zarządzania kartami**: Dodano skróty `Ctrl+T` (nowa karta) i `Ctrl+W` (zamknij kartę).
    - **Refaktoryzacja "Zakładek" na "Ulubione"**: Zmieniono terminologię w całej aplikacji, w tym w interfejsie, kodzie i plikach tłumaczeń. Dodano nowe menu "Ulubione".
    - **Konfigurowalne edytory zewnętrzne**: Dodano w ustawieniach możliwość zdefiniowania własnych komend dla podglądu (F3) i edycji (F4), np. `kate %f`.
    - **Zarządzanie ulubionymi**: Dodano przycisk "Usuń" w oknie dialogowym ulubionych.
- **Tłumaczenia**:
    - Uzupełniono brakujące tłumaczenia w pliku `pl_PL.json`.
    - Wyciszono szczegółowe logi debugowania z `PyQt6.uic`, aby poprawić czytelność głównego logu.

## Data: 2025-11-30
    
### Postępy prac:
- **Poprawka klawiszy nawigacyjnych (Home, End, Tab):**
    - Zdiagnozowano, że klawisze `Home`, `End` i `Tab` nie działały w aktywnym panelu ze względu na brak zainstalowania `FolderBrowser` jako filtra zdarzeń dla jego paneli (`left_panel`, `right_panel`).
    - Zainstalowano `FolderBrowser` jako filtr zdarzeń dla `self.left_panel` i `self.right_panel` w `browser/folder_browser.py`, zapewniając prawidłowe przetwarzanie zdarzeń klawiszy nawigacyjnych.
- **Opcja ukrywania plików/folderów z kropką:**
    - Dodano opcję `Show hidden files (Dot Files)` w ustawieniach aplikacji, aby kontrolować widoczność plików i folderów rozpoczynających się od kropki.
    - Zaktualizowano `SettingsManager` o nowe ustawienie `showDotFiles`, domyślnie ustawione na `True`.
    - Zmodyfikowano `SettingsDialog` w celu dodania pola wyboru dla tego ustawienia.
    - Zaktualizowano `MenuPanel`, aby przekazywać i zapisywać to ustawienie.
    - Zaimplementowano filtrowanie plików kropkowych w `FlatFileSystemModel` i `QFileSystemModel` na podstawie ustawienia `showDotFiles`.
- **Naprawiono błąd NameError w SettingsDialog:**
    - Dodano brakujący import `from PyQt6.QtCore import Qt` w `utils/settings_dialog.py`, aby rozwiązać błąd `NameError` podczas dostępu do `Qt.CheckState`.
- **Naprawiono błąd NameError w FolderBrowser:**
    - Dodano brakujący import `from PyQt6.QtCore import QDir` w `browser/folder_browser.py`, aby rozwiązać błąd `NameError` podczas dostępu do `QDir.Filter` w metodzie `create_file_view`.
- **Naprawiono problem z przełączaniem trybów widoku i filtrowaniem plików kropkowych:**
    - W metodzie `set_view_mode` w `FolderBrowser` ponownie zainstalowano filtry zdarzeń dla nowo utworzonych paneli (`self.left_panel`, `self.right_panel`), aby przywrócić obsługę zdarzeń klawiatury po zmianie trybu widoku.
    - Poprawiono logikę ustawiania filtra dla `QFileSystemModel` w metodzie `create_file_view`, aby `QDir.Filter.Hidden` było stosowane tylko wtedy, gdy ustawienie `_show_dot_files` jest `True`, zapewniając prawidłowe filtrowanie plików kropkowych w widoku drzewa.

## Data: 2025-11-28

### Postępy prac:
- **Internacjonalizacja (i18n):**
    - Naprawiono uszkodzony plik `translations/app_pl.ts` poprzez wygenerowanie nowego pliku z poprawną strukturą i przeniesienie istniejących tłumaczeń.
    - Zmieniono użycie `self.tr()` na `QCoreApplication.translate("MenuPanel", ...)` w `panels/menu_panel.py`, aby zapewnić poprawne działanie tłumaczeń bez konieczności dziedziczenia klasy `MenuPanel` z `QObject` lub `QWidget`.
    - Skompilowano `translations/app_pl.ts` do `translations/app_pl.qm`.
    - Potwierdzono, że nieprzetłumaczone ciągi znaków będą wyświetlane w języku angielskim.
- **Wyświetlanie okien dialogowych:**
    - Zdiagnozowano i rozwiązano problem z niewyświetlaniem się okien dialogowych (takich jak Ustawienia, Skróty, Tworzenie Archiwum, Tworzenie Katalogu). Problem był związany z dziedziczeniem klasy `MenuPanel` i użyciem `self.tr()`.
    - Zweryfikowano działanie wszystkich okien dialogowych.
- **Logowanie:**
    - Zmieniono ścieżkę zapisu logów z `~/.config/QuickFile/main.log` na `logs/main.log` w katalogu projektu.
    - Usunięto tymczasowe pliki logów i skrypty diagnostyczne.

## Data: 2025-11-26

### The implemented features so far include:
- Configurable folder view modes (flat and tree view).
- Fixed bugs after migration to PyQt6 (QSplitter.removeWidget replaced with replaceWidget, QTreeView imports, TypeError in MenuPanel, QFileIconProvider import, IconType.FolderUp updated).
- Handling archives (ZIP, TAR).
- Directory synchronization.
- Configurable keyboard shortcuts.
- File/directory comparison.
- Active panel indicator.
- Fixed F6/F7 shortcuts.
- Ctrl+R for refresh.
- Bookmarks (add current directory, quick access with Ctrl+B).
- Fixed NameError for QDialog.
- Reverted changes in file_viewer/file_editor.py (removed autocompletion, bracket matching, autoindentation; editor works with line numbers and syntax highlighting).
- Removed internal file editor, now opens files with external system tools.
- Added function key panel (F1-F10).
- Implemented saving application settings (window size/position, panel paths).
- Fixed QMainWindow::saveState() warning (set objectName for toolbar).
- Fixed SyntaxWarning in PythonHighlighter.
- Organized project files (renamed docs, removed unused files).
- Improved file search with SearchDialog.
* Konfigurowalne tryby widoku folderów (płaski i drzewa).
* Naprawiono błędy po migracji do PyQt6 (w tym ostatni błąd podwójnego kliknięcia w widoku drzewa).
* Synchronizacja katalogów.
* Konfigurowalne skróty klawiszowe.
* Porównywanie plików/katalogów.
* Wskaźnik aktywnego panelu.
* Poprawka skrótów F6/F7.
* Skrót odświeżania (Ctrl+R).
* Zakładki.
* Panel klawiszy funkcyjnych (F1-F10).
* Zapamiętywanie ustawień aplikacji (rozmiar/pozycja okna, ścieżki paneli).
* Ulepszone wyszukiwanie plików.
* Szkielet aplikacji i podstawowe operacje na plikach (kopiowanie, przenoszenie, usuwanie, zmiana nazwy).

### Zaimplementowane częściowo: 
   * Obsługa archiwów (ZIP, TAR, RAR - wypakowywanie): Tworzenie i wypakowywanie ZIP i TAR, wypakowywanie RAR.


Earlier features:
- Application skeleton (MainWindow, FolderBrowser, MenuPanel).
- Basic file operations (copy, paste, move, delete, rename).
- Improved error handling with utils/dialogs.py.
- UI improvements (icons, shortcuts, toolbar, address bar, go up, refresh, new file/folder actions, saving settings, opening files externally).
- The last implemented feature was changing the behavior of the `Tree` view so that `Enter` or double-click on a directory expands/collapses it within the tree, rather than changing the root. The user will test this feature tomorrow.
- When creating a git commit, always use a safe syntax for multi-line messages to avoid bash errors. Use separate -m flags for the title and each line of the body. For example: `git commit -m "Title" -m "Line 1 of body." -m "Line 2 of body."`   
