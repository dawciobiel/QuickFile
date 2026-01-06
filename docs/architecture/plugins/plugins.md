# Architektura Systemu Wtyczek (Plugin Architecture)

## Przegląd

QuickFile wykorzystuje system wtyczek oparty na interfejsach, aby umożliwić łatwe rozszerzanie funkcjonalności aplikacji bez konieczności
modyfikowania jej rdzenia. Głównym celem jest obsługa różnych formatów archiwów (ZIP, RAR, 7z), ale architektura jest zaprojektowana tak,
aby wspierać również inne typy operacji w przyszłości (np. sumy kontrolne, szyfrowanie, operacje dyskowe, rozszerzenia UI, podgląd plików).

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
  "entry_point": "plugin.py",
  "class_name": "ZipPlugin"
}
```

*   **name**: Wyświetlana nazwa wtyczki.
* **type**: Typ wtyczki (np. `archive`, `checksum`, `disk_utils`, `ui_extension`, `viewer`). Używany przez `PluginManager` do kategoryzacji.
*   **description**: Krótki opis.
*   **entry_point**: Nazwa pliku `.py` zawierającego klasę wtyczki.
*   **class_name**: Nazwa klasy implementującej interfejs wtyczki.

## Interfejsy (Kontrakty)

Wszystkie wtyczki muszą dziedziczyć po klasach bazowych zdefiniowanych w `plugins/base.py`.

### `FileOperationPlugin` (Bazowy)
Wspólny interfejs dla wszystkich wtyczek.
*   `name`: Nazwa wtyczki.
*   `description`: Opis wtyczki.

### `ArchivePlugin` (Typ: `archive`)
Interfejs dla wtyczek obsługujących archiwizację.
*   `get_supported_extensions()`: Zwraca listę obsługiwanych rozszerzeń (np. `['.zip']`).
*   `create_archive(source_paths, destination_path, options, ...)`: Tworzy archiwum.
*   `extract_archive(archive_path, destination_path, options, ...)`: Wypakowuje archiwum.

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
2.  **Ładowanie**: Dynamicznie ładuje moduły Pythona i tworzy instancje klas wtyczek.
3. **Rejestrację**: Grupuje wtyczki według typu (`archive`, `checksum`, `disk_utils`, `ui_extension`, `viewer`) i udostępnia je reszcie
   aplikacji.
4.  **Instalację i Aktualizację**: Przy starcie porównuje wersje wtyczek wbudowanych w aplikację z tymi zainstalowanymi u użytkownika. Jeśli wbudowana wersja jest nowsza, automatycznie aktualizuje wtyczkę w katalogu użytkownika.

## Integracja z Kolejką Zadań

`TaskQueueManager` wykorzystuje `PluginManager` do delegowania zadań archiwizacji.
1.  Gdy użytkownik zleca operację (np. "Wypakuj"), `DialogHandler` tworzy zadanie `TaskType.EXTRACT`.
2.  `TaskQueueManager` pobiera rozszerzenie pliku.
3.  Pyta `PluginManager` o wtyczkę obsługującą to rozszerzenie (`get_archiver_for_extension`).
4.  Uruchamia metodę wtyczki w tle.
