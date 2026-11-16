# Architektura Systemu Wtyczek (Plugin Architecture)

## Przegląd

QuickFile wykorzystuje system wtyczek oparty na interfejsach, aby umożliwić łatwe rozszerzanie funkcjonalności aplikacji bez konieczności
modyfikowania jej rdzenia. Głównym celem jest obsługa różnych formatów archiwów (ZIP, RAR, 7z), ale architektura jest zaprojektowana tak,
aby wspierać również inne typy operacji w przyszłości (np. sumy kontrolne, szyfrowanie, operacje dyskowe, rozszerzenia UI, podgląd plików).

## Izolacja Procesów (Piaskownica)

Aby zapewnić stabilność i responsywność interfejsu użytkownika, wtyczki wykonujące długotrwałe lub potencjalnie niestabilne operacje (np. operacje na plikach, archiwizacja, wyszukiwanie) są uruchamiane w **osobnych procesach**.

**Co to daje:**
*   **Stabilność:** Awaria lub zawieszenie wtyczki nie powoduje zawieszenia ani zamknięcia całej aplikacji — proces można zakończyć.
*   **Responsywność UI:** Operacje w tle nie blokują głównego wątku interfejsu użytkownika.
*   **Izolacja awarii:** Wyciek pamięci lub nieskończona pętla we wtyczce nie psuje stanu aplikacji.

**Czego to NIE daje — bezpieczeństwo:**

Plugin działający w osobnym procesie **nie jest odizolowany bezpieczeństwem**. Działa z tymi samymi uprawnieniami co użytkownik: ma dostęp do całego jego systemu plików, sieci, `os.environ`, kluczy SSH itd. Złośliwy kod wtyczki zostanie wykonany i może zrobić wszystko, co może zrobić użytkownik.

W związku z tym:
*   **Zaufanie deklaruje użytkownik**, nie wtyczka. Pole `sandboxed` w metadanych wybiera jedynie tryb uruchomienia — nie jest deklaracją bezpieczeństwa.
*   Wtyczki należy instalować wyłącznie z zaufanych źródeł, tak jak każdy inny kod wykonywalny.
*   Realne ograniczenie uprawnień (Landlock/seccomp/bubblewrap lub WASM) to osobny, przyszły etap — opisany w `docs/project_management/plan-naprawy-2026-11-14.md`.

## Struktura Katalogów

Wtyczki są przechowywane w katalogu konfiguracyjnym użytkownika, co pozwala na łatwą instalację i aktualizację bez uprawnień administratora.

**Lokalizacja produkcyjna:** `~/.config/QuickFile/plugins/`
**Lokalizacja w repozytorium (dev):** `plugins/`

Przy starcie `PluginManager` porównuje wersje wtyczek wbudowanych z tymi w katalogu użytkownika i w razie potrzeby kopiuje nowszą wersję. Wbudowane wtyczki są częścią pakietu (dane, nie kod importowalny — patrz „Kontrakt ładowania”).

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

## Kontrakt ładowania modułów

Katalogi wtyczek zawierają kropkę w nazwie (`org.quickfile.copy_operation`), więc **nie są importowalnymi pakietami Pythona**. `PluginManager` ładuje `plugin.py` po ścieżce pliku (`importlib.util.spec_from_file_location`), a katalog wtyczki trafia na `sys.path`.

Konsekwencje, których trzeba przestrzegać:

1.  **Moduły na najwyższym poziomie katalogu wtyczki nie mogą używać importów relatywnych.**
    `from .tasks import CopyTask` kończy się błędem `attempted relative import with no known parent package`.
    Poprawnie: `from tasks import CopyTask`.
2.  **Podkatalogi z `__init__.py` są pakietami** i wewnątrz nich importy relatywne są w porządku
    (np. `widgets/editor_dialog.py` może robić `from .editor_widget import EditorWidget`).
3.  Nazwa wersji w `metadata.json` **musi** być identyczna z nazwą katalogu wersji.

Punkty 1 i 3 są pilnowane przez testy w `tests/unit/test_plugin_structure.py`.

## Zależności wtyczek

Wtyczka może zadeklarować zależności w `metadata.json`:

```json
"python_dependencies": ["some-library>=1.0"]
```

Zasady:

*   **Ładowanie wtyczki nigdy nie instaluje zależności.** QuickFile nie uruchamia `pip` przy starcie —
    wymagałoby to sieci, zmieniało środowisko aplikacji i uniemożliwiało reprodukcję błędów.
*   Zależności, które host już posiada (np. `PyQt6`), są traktowane jako spełnione i nie wymagają deklaracji.
*   Instalacja to jawna akcja (`PluginDependencyManager.install_dependencies`), wywoływana przez użytkownika
    lub instalator wtyczki. Brakująca zależność jest logowana jako ostrzeżenie, a wtyczka i tak się ładuje.

## Metadane (`metadata.json`)

Każda wtyczka musi zawierać plik `metadata.json` w swoim katalogu wersji. Plik ten definiuje podstawowe informacje o wtyczce oraz punkt wejścia dla `PluginManager`.

```json
{
  "id": "org.quickfile.zip_archiver",
  "name": "Standard ZIP Archiver",
  "version": "1.0.0",
  "author": "QuickFile Team",
  "type": "archive",
  "description": "Provides support for creating and extracting ZIP archives.",
  "entry_point": "plugin:ZipPlugin",
  "class_name": "ZipPlugin",
  "sandboxed": true,
  "platforms": ["windows", "linux", "macos"]
}
```

*   **id**: Unikalny identyfikator wtyczki (odwrócona domena).
*   **name**: Wyświetlana nazwa wtyczki.
*   **version**: Wersja wtyczki; musi być równa nazwie katalogu wersji.
*   **type**: Typ wtyczki (np. `archive`, `checksum`, `disk_utils`, `ui_extension`, `viewer`, `menu_action`). Używany przez `PluginManager` do kategoryzacji.
*   **description**: Krótki opis.
*   **entry_point**: Nazwa modułu Pythona i klasy (np. `plugin:ZipPlugin`) zawierającej klasę wtyczki.
*   **class_name**: Nazwa klasy implementującej interfejs wtyczki.
*   **sandboxed**: (Opcjonalnie, `boolean`) Jeśli `true`, wtyczka zostanie uruchomiona w osobnym procesie. **Zalecane dla wtyczek wykonujących operacje w tle.** To wybór trybu uruchomienia, a nie deklaracja bezpieczeństwa — patrz „Izolacja Procesów”.
*   **platforms**: (Opcjonalnie, `array of strings`) Lista platform, na których wtyczka jest wspierana (np. `"windows"`, `"linux"`, `"macos"`).
*   **python_dependencies**: (Opcjonalnie, `array of strings`) Zależności Pythona — patrz „Zależności wtyczek”.

## Interfejsy (Kontrakty)

Wszystkie wtyczki dziedziczą po `PluginBase` z `app/plugin_system/api.py`.
Klasy pomocnicze dla wtyczek działających w procesie głównym (UI, przeglądarki,
edytory) są w `plugins/base.py` — one również wywodzą się z `PluginBase`.

## Kontrakt zadań

Zadanie w tle można zrealizować na dwa sposoby. Protokół host↔plugin jest w obu
przypadkach **identyczny**: o wyborze adaptera decyduje klasa wtyczki wewnątrz
procesu wtyczki, więc host nie wie i nie musi wiedzieć, który styl jest użyty.

### Styl jawny (`TaskPlugin` + `PluginTask`) — dla nowych wtyczek

```python
from app.plugin_system.api import PluginTask, TaskContext, TaskPlugin


class LineCounterPlugin(TaskPlugin):
    def get_name(self) -> str:
        return "Line Counter"

    def get_description(self) -> str:
        return "Counts lines in a text file."

    def create_task(self, action_id: str, **kwargs) -> PluginTask:
        if action_id != "count_lines":
            raise ValueError(f"Unknown action_id: {action_id}")
        return CountLinesTask(kwargs["path"])


class CountLinesTask(PluginTask):
    def __init__(self, path: str):
        self.path = path

    def run(self, ctx: TaskContext):
        with open(self.path, encoding="utf-8", errors="replace") as handle:
            total = sum(1 for _ in handle)
        ctx.progress(100)
        return {"lines": total}
```

`PluginTask` to jednostka pracy z `app/plugin_system/api.py`. Nie mylić z `Task`
z `app/task_queue_manager.py` — tamten jest wpisem w kolejce po stronie UI.

Kontrakt `PluginTask.run(self, ctx)`:

*   `ctx` jest **argumentem** metody. Nie ma `self.context`, nie ma
    `_initialize`, nie ma ukrytego stanu ustawianego przez runtime.
*   wartość zwrócona przez `run` trafia do `RESULT.value` i musi być
    serializowalna: `str`, `int`, `float`, `bool`, `list`, `dict`, `tuple`,
    `None`.
*   wyjątek `TaskCancelled` kończy zadanie komunikatem `CANCELLED`,
*   każdy inny wyjątek kończy zadanie komunikatem `ERROR` (`INTERNAL`)
    z tracebackiem,
*   anulowanie jest **kooperatywne**: runtime nie przerwie `run`. Wtyczka sama
    woła `ctx.check_cancelled()` w pętli; im rzadziej, tym dłużej trwa reakcja
    na anulowanie.

Metody kontekstu (`TaskContext`):

| Metoda | Znaczenie |
|---|---|
| `ctx.task_id` | identyfikator zadania nadany przez host |
| `ctx.progress(percent)` | postęp 0–100; wartości poza zakresem są przycinane |
| `ctx.event(name, payload)` | zdarzenie domenowe do UI (`handle_event` w procesie głównym) |
| `ctx.request_input(name, payload) -> dict` | pytanie do użytkownika; host v1 odpowiada `None`, czyli `{}` |
| `ctx.is_cancelled()` / `ctx.is_paused()` | bieżący stan zadania |
| `ctx.wait_if_paused()` | blokuje, dopóki zadanie nie zostanie wznowione |
| `ctx.check_cancelled()` | podnosi `TaskCancelled`, jeśli zadanie anulowano |
| `ctx.log(level, message)` | log w procesie wtyczki; `warning`/`error` trafiają też do hosta |

Przykład pętli odpornej na anulowanie i pauzę:

```python
def run(self, ctx: TaskContext):
    for index, path in enumerate(self.paths):
        ctx.check_cancelled()      # TaskCancelled -> CANCELLED
        ctx.wait_if_paused()       # śpi, dopóki użytkownik nie wznowi
        self.process(path)
        ctx.progress(int((index + 1) * 100 / len(self.paths)))
    return {"processed": len(self.paths)}
```

Zasady, które wynikają z protokołu:

*   **jedno zadanie naraz** na proces wtyczki (kolejka FIFO) — nie zakładaj
    współbieżności zadań ani nie uruchamiaj własnych wątków, które ją omijają,
*   w trakcie zadania nie wołaj metod wtyczki przez atrybuty (`wrapper.foo()`) —
    to synchroniczne `CALL`, które czeka w tej samej kolejce,
*   zadanie nie powinno trwać wiecznie bez `check_cancelled()`; host nie może
    przerwać `run`.

### Styl stary (`PluginBase` + `AbstractTask`) — zgodność

Wtyczki już istniejące (`create_task` zwracające `AbstractTask`) działają bez
zmian przez `LegacyPluginAdapter`, który przed `run()` woła prywatne
`AbstractTask._initialize(...)` i podłącza:

*   `emit_progress` → `PROGRESS`,
*   `emit_event` → `EVENT`,
*   `request_user_input` → `INPUT_REQUEST`,
*   `self.context` → `TaskContext` (anulowanie, pauza).

Ten styl jest **zamrożony**: przyjmujemy poprawki błędów, ale nowe wtyczki
piszemy w stylu jawnym. Mieszanie stylów w jednej klasie nie jest wspierane —
wtyczka musi jawnie dziedziczyć po `TaskPlugin` (styl jawny) albo po `PluginBase`
(styl stary).

### Wybór adaptera

```python
from app.plugin_system.runtime import adapter_for

adapter = adapter_for(plugin_instance)
```

`TaskPlugin` → `TaskPluginAdapter`, pozostałe `PluginBase` → `LegacyPluginAdapter`,
cokolwiek innego → `TypeError`. Wyboru dokonuje `run_plugin_process` przy starcie
procesu wtyczki; host widzi tylko `READY`.

Wzorcową migracją jest `checksum_standard`
(`plugins/org.quickfile/checksum_standard/1.0.0/`): pętla czyta plik, woła
`ctx.check_cancelled()` i `ctx.wait_if_paused()`, raportuje `ctx.progress()`.
Pozostałe bundlowane wtyczki przechodzą na nowy styl w osobnych zmianach —
stary kontrakt nadal działa i nie ma potrzeby migrować ich hurtem.


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

### `org.quickfile.delete_operation`

Sandboxowana wtyczka usuwania (`delete_items`, `TaskType.DELETE`). Respektuje
opcję `move_to_trash`:

* `move_to_trash=True` (domyślnie): element jest przenoszony do kosza przez
  `send2trash`. Jeśli platforma nie potrafi utworzyć kosza (np. partycja
  zewnętrzna bez prawa zapisu), zadanie kończy się błędem `TrashUnavailableError`
  i **nic nie jest usuwane**; komunikat podpowiada odznaczenie „Move to Trash”.
  Gdy użytkownik zaznaczy „Delete permanently if the Trash is unavailable”,
  wtyczka loguje ostrzeżenie i usuwa element trwale, zamiast przerywać zadanie.
* `move_to_trash=False`: trwałe usuwanie drzewa katalogów.
* Dowiązania symboliczne są zawsze usuwane jako dowiązania — wtyczka nigdy nie
  wchodzi do katalogu docelowego (również przy usuwaniu trwałym i dla zepsutych
  dowiązań).

### `org.quickfile.directory_size`

Sandboxowana wtyczka licząca rozmiar katalogu dla
`TaskType.CALCULATE_SIZE` (akcja `calculate_directory_size`). Używa jawnego API
zadań (`TaskPlugin` + `PluginTask`): dwa przebiegi `os.walk` (najpierw liczba
plików, potem suma rozmiarów), `ctx.check_cancelled()` między plikami i
`ctx.progress()` po każdym pliku. Wynikiem jest `int` w bajtach.

Kolejka mapuje akcję na wtyczkę przez
`PLUGIN_ID_BY_ACTION["calculate_directory_size"]`. Implementacja jest wymienna:
wtyczka dla innego systemu plików wystarczy, że zadeklaruje ten sam `action_id`,
a mapowanie wskaże ją zamiast wersji standardowej.

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
3. **Rejestrację**: Grupuje wtyczki według typu (`archive`, `checksum`, `directory_size`, `disk_utils`, `ui_extension`, `viewer`, `menu_action`) i udostępnia je reszcie
   aplikacji.
4.  **Instalację i Aktualizację**: Przy starcie porównuje wersje wtyczek wbudowanych w aplikację z tymi zainstalowanymi u użytkownika. Jeśli wbudowana wersja jest nowsza, automatycznie aktualizuje wtyczkę w katalogu użytkownika.

## Integracja z Kolejką Zadań

`TaskQueueManager` wykorzystuje `PluginManager` do delegowania zadań.
1.  Gdy użytkownik zleca operację (np. "Wypakuj", "Kopiuj", "Dziel Plik"), `DialogHandler` tworzy zadanie `Task` z odpowiednim `TaskType` i `plugin_id`.
2.  `TaskQueueManager` przekazuje zadanie do `BackgroundTaskManager`.
3.  `BackgroundTaskManager` identyfikuje wtyczkę po `plugin_id` i wywołuje jej metodę (np. `extract_archive`, `copy_items`, `split_file`) asynchronicznie, poprzez `SandboxedPluginWrapper`.
4.  `BackgroundTaskManager` nasłuchuje na sygnały z `SandboxedPluginWrapper` (postęp, zakończenie, błędy) i aktualizuje stan zadania w `TaskQueueManager`, który z kolei odświeża interfejs użytkownika.

## Wywoływanie metod wtyczki sandboxowanej

`sandboxed` wtyczka jest reprezentowana przez `SandboxedPluginWrapper`
(`app/plugin_system/host.py`). Host wysyła `HELLO`, a proces potomny odpowiada
`READY` z listą publicznych metod. Wrapper:

*   udostępnia przez atrybuty **tylko** te metody — każde wywołanie to para
    `CALL`/`RETURN` z korelacją po `call_id`,
*   dla nieznanej lub prywatnej nazwy natychmiast rzuca `AttributeError` — bez
    odpytywania i bez blokowania UI,
*   operacje długotrwałe uruchamia przez `execute_task()` (asynchronicznie,
    z postępem i kooperatywnym anulowaniem).

Zasada: do pracy w tle używaj `execute_task()`. Synchroniczne wywołania metod są
przeznaczone wyłącznie dla szybkich zapytań (np. `get_supported_extensions()`)
i mają limit czasu (10 s w hoście; domyślnie 5 s w protokole).

Anulowanie zadania czekającego w kolejce jest natychmiastowe — nie czeka za
zadaniem, które akurat trwa. To była główna wada poprzedniego runtime'u.

## Planowany kierunek rozwoju

Etap C w `docs/project_management/plan-naprawy-2026-11-14.md` jest zrealizowany
poza opcjonalną izolacją OS:

*   ✅ wątek IPC i wątek roboczy wewnątrz procesu wtyczki (`runtime.py`),
*   ✅ wersjonowany, asynchroniczny protokół (`HELLO`/`READY`, `EXECUTE_TASK`, `CANCEL_TASK`, `PAUSE_TASK`, `PROGRESS`, `RESULT`, `ERROR`),
*   ✅ adapter dla wtyczek w obecnym stylu (`LegacyPluginAdapter`) — bez przepisywania pluginów,
*   ✅ jawne API zadań dla nowych pluginów (`TaskPlugin` + `PluginTask` + `TaskPluginAdapter`, bez `AbstractTask._initialize`),
*   ✅ test protokołu dla każdego sandboxowanego pluginu — smoke `tests/unit/test_bundled_plugins_protocol.py` (handshake + `get_name` + `get_menu_actions` dla każdego sandboxowanego) oraz test e2e zadania per plugin; wtyczki in-process nie mówią protokołem,
*   ⬜ opcjonalna izolacja OS (Landlock/bubblewrap) jako osobny etap.

**Kontrakt protokołu jest zdefiniowany w [`runtime-protocol.md`](runtime-protocol.md).**
Ten dokument jest normatywny: wiadomości, pola, kody błędów, kolejność i
zachowanie przy zerwaniu kanału. Kodek (`app/plugin_system/protocol.py`) oraz
testy (`tests/unit/test_runtime_protocol.py`) egzekwują tę specyfikację.
