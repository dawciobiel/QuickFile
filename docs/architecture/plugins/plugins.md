# Architektura Systemu Wtyczek (Plugin Architecture)

## Przegląd

QuickFile wykorzystuje system wtyczek oparty na interfejsach, aby umożliwić łatwe rozszerzanie funkcjonalności aplikacji bez konieczności
modyfikowania jej rdzenia. Głównym celem jest obsługa różnych formatów archiwów (ZIP, RAR, 7z), ale architektura jest zaprojektowana tak,
aby wspierać również inne typy operacji w przyszłości (np. sumy kontrolne, szyfrowanie, operacje dyskowe, rozszerzenia UI, podgląd plików).

## Izolacja Procesów (Piaskownica)

Aby zapewnić maksymalną stabilność, bezpieczeństwo i responsywność interfejsu użytkownika, wtyczki wykonujące długotrwałe lub potencjalnie niestabilne operacje (np. operacje na plikach, archiwizacja, wyszukiwanie) są uruchamiane w **izolowanych procesach (piaskownicach)**.

**Korzyści:**
*   **Stabilność:** Awaria wtyczki nie powoduje zawieszenia ani zamknięcia całej aplikacji.
*   **Bezpieczeństwo:** Wtyczki mają ograniczony dostęp do zasobów systemu i aplikacji.
*   **Izolacja Zależności:** Każda wtyczka może używać własnych wersji bibliotek, bez konfliktu z innymi wtyczkami lub główną aplikacją.
*   **Responsywność UI:** Operacje w tle nie blokują głównego wątku interfejsu użytkownika, zapewniając płynne działanie aplikacji.

## Struktura Katalogów

Wtyczki są przechowywane w katalogu konfiguracyjnym użytkownika, co pozwala na łatwą instalację i aktualizację bez uprawnień administratora.

**Lokalizacja:** `~/.config/QuickFile/plugins/`

Struktura katalogów jest inspirowana konwencją Maven (`groupId/artifactId/version`), co zapewnia unikalność i wsparcie dla wielu wersji tej samej wtyczki.

```
plugins/
├── <groupId>/                  # Odwrócona domena autora (np. org.quickfile)
│   └── <artifactId>/           # Nazwa wtyczki (np. zip_archiver)
│       └── <version>/          # Wersja wtyczki (np. 1.0.0)
│           ├── metadata.json   # Plik metadanych
│           ├── plugin.py       # Główny kod wtyczki
│           ├── __init__.py     # Plik pakietu Python
│           └── resources/      # (Opcjonalnie) Dodatkowe zasoby
```

### Przykład

```
~/.config/QuickFile/plugins/org.quickfile/zip_archiver/1.0.0/
```

## Metadane (`metadata.json`)

Każda wtyczka musi zawierać plik `metadata.json` w swoim katalogu wersji. Plik ten definiuje podstawowe informacje o wtyczce oraz punkt wejścia dla `PluginManager`.

```json
{
  "name": "Standard ZIP Archiver",
  "type": "archive",
  "description": "Provides support for creating and extracting ZIP archives.",
  "entry_point": "plugin:ZipPlugin",
  "class_name": "ZipPlugin",
  "sandboxed": true,
  "platforms": ["windows", "linux", "macos"]
}
```

*   **name**: Wyświetlana nazwa wtyczki.
*   **type**: Typ wtyczki (np. `archive`, `checksum`, `disk_utils`, `ui_extension`, `viewer`, `menu_action`). Używany przez `PluginManager` do kategoryzacji.
*   **description**: Krótki opis.
*   **entry_point**: Nazwa modułu Pythona i klasy (np. `plugin:ZipPlugin`) zawierającej klasę wtyczki.
*   **class_name**: Nazwa klasy implementującej interfejs wtyczki.
*   **sandboxed**: (Opcjonalnie, `boolean`) Jeśli `true`, wtyczka zostanie uruchomiona w izolowanym procesie (piaskownicy). **Zalecane dla wtyczek wykonujących operacje w tle.**
*   **platforms**: (Opcjonalnie, `array of strings`) Lista platform, na których wtyczka jest wspierana (np. `"windows"`, `"linux"`, `"macos"`).

## Interfejsy (Kontrakty)

Wszystkie wtyczki muszą dziedziczyć po klasach bazowych zdefiniowanych w `plugins/base.py`.

### Dodatkowe Argumenty dla Metod Zadań w Tle

Metody wtyczek, które wykonują długotrwałe operacje w tle (np. `create_archive`, `extract_archive`, `copy_items`, `move_items`, `delete_items`, `split_file`, `join_files`, `calculate_checksum`, `search`), otrzymują dodatkowe argumenty, które umożliwiają komunikację z główną aplikacją:

*   `progress_callback`: Funkcja (lub proxy funkcji), którą wtyczka wywołuje, aby zgłosić postęp operacji (np. `progress_callback(percentage)`).
*   `task_context`: Obiekt proxy (`SandboxedTaskContext`), który pozwala wtyczce sprawdzać stan zadania (np. `task_context.is_cancelled` do anulowania, `task_context.wait_if_paused()` do pauzowania).
*   `task`: Obiekt proxy (`SandboxedTask`), który pozwala wtyczce aktualizować szczegóły zadania widoczne w UI. Dostępne metody to m.in.:
    *   `task.set_details(message: str)`: Ustawia szczegółowy opis bieżącej operacji.
    *   `task.set_progress(percentage: int)`: Ustawia postęp dla bieżącego pliku/etapu (0-100%).
    *   `task.set_overall_progress(percentage: int)`: Ustawia ogólny postęp dla całego zadania (0-100%).
    *   `task.emit_directory_changed(path: str)`: Emituje sygnał informujący główną aplikację o zmianie w danym katalogu, co może wywołać odświeżenie widoku.
*   `send_trace`: Funkcja do wysyłania komunikatów debugowania z wnętrza procesu wtyczki do głównego systemu logowania aplikacji.

**Ważne:** Obiekty `task_context` i `task` dostępne w kodzie wtyczki są **obiektami proxy**. Oznacza to, że wywołania ich metod są przekazywane przez potok do głównego procesu, który następnie wykonuje odpowiednie akcje lub emituje sygnały.

### `FileOperationPlugin` (Bazowy)
Wspólny interfejs dla wszystkich wtyczek.
*   `name`: Nazwa wtyczki.
*   `description`: Opis wtyczki.

### `ArchivePlugin` (Typ: `archive`)
Interfejs dla wtyczek obsługujących archiwizację.
*   `get_supported_extensions()`: Zwraca listę obsługiwanych rozszerzeń (np. `['.zip']`).
*   `create_archive(source_paths, destination_path, options, progress_callback, task_context, task, send_trace)`: Tworzy archiwum.
*   `extract_archive(archive_path, destination_path, options, progress_callback, task_context, task, send_trace)`: Wypakowuje archiwum.

### `DiskUtilsPlugin` (Typ: `disk_utils`)
Interfejs dla wtyczek dostarczających informacje o systemie plików i dyskach. Służy do oddzielenia warstwy prezentacji (UI) od warstwy dostępu do danych systemowych.
*   `get_disk_usage(path: str) -> tuple[int, int, int] | None`: Zwraca krotkę `(total, used, free)` w bajtach dla podanej ścieżki.

### `UiExtensionPlugin` (Typ: `ui_extension`)
Interfejs dla wtyczek, które modyfikują główny interfejs użytkownika aplikacji (np. dodają opcje do menu).
*   `initialize(main_window)`: Metoda wywoływana po zbudowaniu głównego okna, pozwalająca wtyczce na dodanie swoich elementów UI.

### `ViewerPlugin` (Typ: `viewer`)

Interfejs dla wtyczek zapewniających podgląd plików (F3).

* `can_view(file_path: str) -> bool`: Zwraca `True`, jeśli wtyczka potrafi wyświetlić dany plik.
* `view_file(file_path: str, parent: QWidget)`: Otwiera okno podglądu dla danego pliku.

## Dostępne Wtyczki Standardowe

### `org.quickfile.standard_viewer`

Wbudowana przeglądarka plików, która obsługuje:

* **Tekst**: Podgląd plików tekstowych z obsługą różnych kodowań.
* **Obrazy**: Wyświetlanie plików graficznych (PNG, JPG, BMP, GIF, SVG, ICO, TIFF, WEBP) z automatycznym skalowaniem.
* **Markdown**: Renderowanie sformatowanego tekstu z plików `.md` i `.markdown` (z obsługą linków).
* **Kod Źródłowy**: Kolorowanie składni dla wielu języków programowania (wykorzystuje bibliotekę `Pygments` i styl `monokai`).
* **Tryby Binarne**: Podgląd w trybach HEX, DEC, BIN.

## Zarządzanie Wtyczkami (`PluginManager`)

Klasa `PluginManager` (`app/plugin_manager.py`) odpowiada za:
1.  **Skanowanie**: Przeszukuje katalog `plugins/` w poszukiwaniu poprawnych struktur wtyczek.
2.  **Ładowanie**: Dynamicznie ładuje moduły Pythona i tworzy instancje klas wtyczek. Dla wtyczek oznaczonych jako `sandboxed`, tworzy instancję `SandboxedPluginWrapper`, która uruchamia wtyczkę w osobnym procesie.
3. **Rejestrację**: Grupuje wtyczki według typu (`archive`, `checksum`, `disk_utils`, `ui_extension`, `viewer`, `menu_action`) i udostępnia je reszcie
   aplikacji.
4.  **Instalację i Aktualizację**: Przy starcie porównuje wersje wtyczek wbudowanych w aplikację z tymi zainstalowanymi u użytkownika. Jeśli wbudowana wersja jest nowsza, automatycznie aktualizuje wtyczkę w katalogu użytkownika.

## Integracja z Kolejką Zadań

`TaskQueueManager` wykorzystuje `PluginManager` do delegowania zadań.
1.  Gdy użytkownik zleca operację (np. "Wypakuj", "Kopiuj", "Dziel Plik"), `DialogHandler` tworzy zadanie `Task` z odpowiednim `TaskType` i `plugin_id`.
2.  `TaskQueueManager` przekazuje zadanie do `BackgroundTaskManager`.
3.  `BackgroundTaskManager` identyfikuje wtyczkę po `plugin_id` i wywołuje jej metodę (np. `extract_archive`, `copy_items`, `split_file`) asynchronicznie, poprzez `SandboxedPluginWrapper`.
4.  `BackgroundTaskManager` nasłuchuje na sygnały z `SandboxedPluginWrapper` (postęp, zakończenie, błędy) i aktualizuje stan zadania w `TaskQueueManager`, który z kolei odświeża interfejs użytkownika.
