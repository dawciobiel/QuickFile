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
**Wtyczki spoza wydania:** `~/.config/QuickFile/plugins-external/` — patrz „Wtyczki zewnętrzne”
**Lokalizacja w repozytorium (dev):** `plugins/`

Przy starcie `PluginManager` porównuje zawartość wtyczek wbudowanych z tymi w katalogu użytkownika (hash plików, nie numer wersji) i w razie różnicy odświeża kopię użytkownika. Wbudowane wtyczki są częścią pakietu (dane, nie kod importowalny — patrz „Kontrakt ładowania”).

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
~/.config/QuickFile/plugins/org.quickfile/zip_archiver/1.0.4/
```

## Kontrakt ładowania modułów

Katalogi wtyczek zawierają kropkę w nazwie (`org.quickfile.copy_operation`), więc **nie są importowalnymi pakietami Pythona**. `PluginManager` ładuje `plugin.py` po ścieżce pliku (`importlib.util.spec_from_file_location`), a katalog wtyczki trafia na `sys.path`.

Konsekwencje, których trzeba przestrzegać:

1.  **Moduły na najwyższym poziomie katalogu wtyczki nie mogą używać importów relatywnych.**
    `from .tasks import CopyTask` kończy się błędem `attempted relative import with no known parent package`.
    Poprawnie: `from tasks import CopyTask`.
2.  **Podkatalogi z `__init__.py` są pakietami** i wewnątrz nich importy relatywne są w porządku
    (np. `widgets/editor_window.py` może robić `from .editor_widget import EditorWidget`).
3.  Nazwa wersji w `metadata.json` **musi** być identyczna z nazwą katalogu wersji.

Punkty 1 i 3 są pilnowane przez testy w `tests/unit/test_plugin_structure.py`.

## Zależności wtyczek

Wtyczka może zadeklarować zależności w `metadata.json`:

```json
"python_dependencies": ["some-library>=1.0"],
"python_import_names": {"some-library": "some_library"},
"dependency_lock": "requirements.lock",
"dependency_wheels": "wheels"
```

Zasady:

*   **Ładowanie wtyczki nigdy nie instaluje zależności.** QuickFile nie uruchamia `pip` przy starcie —
    wymagałoby to sieci, zmieniało środowisko aplikacji i uniemożliwiało reprodukcję błędów.
*   Wymagania są weryfikowane z **wersją**, nie tylko po nazwie dystrybucji. Sprawdzany jest host
    (`importlib.metadata`) oraz `<plugin>/libs`; niezgodna wersja jest traktowana jak brak.
*   `python_import_names` mapuje nazwę dystrybucji na moduł dla pojedynczych plików bez metadanych
    (`PyYAML` → `yaml`). Taka mapa spełnia tylko wymagania bez specyfikatora wersji.
*   Jeśli istnieje `requirements.lock`, jego przypięcia (`==`) **zastępują** szerokie wymagania z
    metadanych i muszą pokrywać każdą zadeklarowaną dystrybucję. Lock jest w pełni rozwiązany
    (z zależnościami tranzytywnymi) i zawiera hashe.
*   Instalacja to jawna akcja (`PluginDependencyManager.install_dependencies`), wywoływana przez
    użytkownika lub instalator wtyczki. Działa **offline**:

    ```
    python -m pip install --no-index --find-links <wheels> --require-hashes \
        --target <plugin>/libs -r <lock>
    ```

    Brak locka albo lokalnych wheeli kończy się błędem — instalator nigdy nie sięga do sieci.
*   Zależności wbudowanych wtyczek są w `flake.nix`. `libs/` jest mechanizmem dla wtyczek
    zewnętrznych, a każda zainstalowana wersja wtyczki ma własny katalog `libs/`. Odświeżenie
    wtyczki usuwa `libs/` wersji, której nowa paczka już nie zawiera.
*   Wtyczka, która naprawdę potrzebuje `libs/` (host nie dostarcza zależności), **musi** mieć
    `sandboxed: true`. Ładowanie takiej wtyczki do procesu hosta jest odrzucane, a
    `install_dependencies` odmawia instalacji. Zależności dostarczane przez host (np. `PyQt6`)
    nie wymagają sandboxu, bo nic nie ląduje w `libs/`.
*   Wbudowane wtyczki deklarują tylko to, co Nix już daje (`rar_archiver` → `rarfile`,
    `delete_operation` → `send2trash`). Pilnuje tego
    `tests/unit/test_bundled_plugin_dependencies.py`: deklaracja musi być spełniona przez
    host i nie może wymagać `libs/`.
*   Brakująca zależność jest logowana jako ostrzeżenie, a wtyczka i tak się ładuje.

### Narzędzia zewnętrzne (`external_tools`)

`python_dependencies` opisuje pakiety Pythona. Niektóre wtyczki potrzebują jednak **programu
w systemie hosta**, którego nie wolno ani nie da się dołączyć do aplikacji: `rarfile` jest tylko
nakładką i wymaga `unrar`, `unar`, `bsdtar` albo `7z`. Bez deklaracji brak narzędzia wychodzi
dopiero w środku zadania, jako nieczytelny wyjątek z wnętrza biblioteki.

```json
"external_tools": [
  {
    "id": "rar_backend",
    "name": "RAR extraction backend",
    "executables": ["unrar", "unar", "bsdtar", "7z", "7zz"]
  }
]
```

Zasady:

*   Wymaganie jest **spełnione, gdy w `PATH` istnieje którykolwiek** z `executables`. Lista
    wariantów jest konieczna, bo biblioteka sama wybiera dostępny backend.
*   Wpis jest **twardym wymaganiem**. Opcjonalne narzędzia („działa bez tego, tylko wolniej”)
    nie są obsługiwane, dopóki nie pojawi się realny przypadek — inaczej każdy plugin musiałby
    opisywać, co traci bez narzędzia.
*   `id` jest stabilnym kluczem w obrębie wtyczki (przyszłe nadpisanie ścieżki w ustawieniach),
    `name` trafia do komunikatu, `executables` to **same nazwy poleceń**, nigdy ścieżki.
    Windows nie potrzebuje osobnej listy: `shutil.which` respektuje `PATHEXT`, więc `unrar`
    znajduje `UnRAR.exe`.
*   Host **tylko sprawdza obecność**: nie instaluje, nie pobiera i nie odpytuje o wersję.
    Parsowanie `--version` jest zależne od narzędzia i może zawiesić UI; minimalna wersja
    backendu to osobna decyzja, gdy pojawi się problem zgodności.
*   Błędna deklaracja (brak `id`, puste `executables`, wpis niebędący obiektem) to **błąd
    konfiguracji**: wtyczka nie jest ładowana, a powód trafia do logu. Nie da się wtedy
    stwierdzić, czy wtyczka zadziała, więc udawanie, że jest dostępna, tylko przesuwa błąd
    w czasie. Wbudowane wtyczki pilnuje `tests/unit/test_bundled_external_tools.py`.
*   Pakiet, który sam jest nakładką na binarkę (np. `rarfile`), deklaruje **oba**: wpis w
    `python_dependencies` i wymaganie w `external_tools`.

Preflight należy do **hosta i dzieje się przed dodaniem zadania do kolejki**
(`app/external_tools.py`). Gdy wymaganie nie jest spełnione, użytkownik dostaje przetłumaczony
komunikat z nazwą wtyczki i listą akceptowanych poleceń, a zadanie nie powstaje. Wtyczka
nadal waliduje swoje opcje w `create_task()`, bo kolejka może być użyta bez dialogu.

## Capabilities

`type` decyduje, do którego slotu `PluginManager.plugins` trafia wtyczka. Nie mówi jednak,
**co wtyczka potrafi** w obrębie tego slotu: archiwizator może tworzyć archiwa, wypakowywać je
albo jedno i drugie. Do tego służy `capabilities` — zamknięty słownik stałych z
`app/plugin_system/api.py` (`Capability`):

| Capability | Znaczenie | Obsługiwany `action_id` |
|---|---|---|
| `archive.create` | Wtyczka tworzy archiwa | `create_archive` |
| `archive.extract` | Wtyczka wypakowuje archiwa | `extract_archive` |

```json
"type": "archive",
"capabilities": ["archive.extract"]
```

Zasady:

*   Lista jest **deklaracją kontraktu**, nie opisem implementacji. Deklarowane capability musi
    odpowiadać obsługiwanemu `action_id` w `create_task()`; pilnuje tego
    `tests/unit/test_bundled_archive_capabilities.py`.
*   UI i routing filtrują po capability: `PluginManager.get_archivers(capability)`,
    `get_archiver_for_extension(extension, capability)` i
    `get_archiver_for_file(path, capability)`. Dzięki temu dialog tworzenia archiwum nie
    proponuje wtyczki, która tylko wypakowuje.
*   Rozszerzenia są normalizowane (wielkość liter i wiodąca kropka), bo wtyczki zwracają
    zarówno `"zip"`, jak i `".rar"`.
*   Wtyczka **bez** listy `capabilities` jest traktowana jako legacy i pasuje do każdej
    capability. To zachowuje działanie wtyczek zewnętrznych sprzed wprowadzenia słownika, ale
    nowe wtyczki powinny deklarować capabilities jawnie.
*   Słownik jest zamknięty. Nową capability dodajemy jako stałą w `Capability`, razem z
    mapowaniem na `action_id` i testem kontraktowym.

## Metadane (`metadata.json`)

Każda wtyczka musi zawierać plik `metadata.json` w swoim katalogu wersji. Plik ten definiuje podstawowe informacje o wtyczce oraz punkt wejścia dla `PluginManager`.

```json
{
  "id": "org.quickfile.zip_archiver",
  "name": "Standard ZIP Archiver",
  "version": "1.0.0",
  "author": "QuickFile Team",
  "type": "archive",
  "description": "Creates and extracts ZIP archives.",
  "entry_point": "plugin:ZipArchiverPlugin",
  "class_name": "ZipArchiverPlugin",
  "sandboxed": true,
  "platforms": ["windows", "linux", "macos"],
  "capabilities": ["archive.create", "archive.extract"]
}
```

*   **id**: Unikalny identyfikator wtyczki (odwrócona domena).
*   **name**: Wyświetlana nazwa wtyczki.
*   **version**: Wersja wtyczki; musi być równa nazwie katalogu wersji.
*   **type**: Typ wtyczki (np. `archive`, `checksum`, `disk_utils`, `ui_extension`, `viewer`, `menu_action`). Używany przez `PluginManager` do kategoryzacji.
*   **capabilities**: (Opcjonalnie, `array of strings`) Możliwości w obrębie typu, np. `archive.create` / `archive.extract` — patrz „Capabilities”.
*   **settings**: (Opcjonalnie, `object`) Deklaracja ustawień — patrz „Ustawienia pluginów”.
*   **description**: Krótki opis.
*   **entry_point**: Nazwa modułu Pythona i klasy (np. `plugin:ZipPlugin`) zawierającej klasę wtyczki.
*   **class_name**: Nazwa klasy implementującej interfejs wtyczki.
*   **sandboxed**: (Opcjonalnie, `boolean`) Jeśli `true`, wtyczka zostanie uruchomiona w osobnym procesie. **Wymagane, gdy wtyczka potrzebuje zależności z `libs/`**; zależności dostarczane przez host nie wymagają sandboxu. To wybór trybu uruchomienia, a nie deklaracja bezpieczeństwa — patrz „Izolacja Procesów”.
*   **platforms**: (Opcjonalnie, `array of strings`) Lista platform, na których wtyczka jest wspierana (np. `"windows"`, `"linux"`, `"macos"`).
*   **python_dependencies**: (Opcjonalnie, `array of strings`) Zależności Pythona (PEP 508) — patrz „Zależności wtyczek”.
*   **python_import_names**: (Opcjonalnie, `object`) Mapa dystrybucja → moduł dla zależności bez metadanych dystrybucji.
*   **dependency_lock**: (Opcjonalnie, `string`, domyślnie `requirements.lock`) Ścieżka do hashowanego locka wewnątrz katalogu wersji.
*   **dependency_wheels**: (Opcjonalnie, `string`, domyślnie `wheels`) Katalog z lokalnymi wheelami do instalacji offline.
*   **external_tools**: (Opcjonalnie, `array of objects`) Wymagane programy hosta — patrz „Narzędzia zewnętrzne”.

## Ustawienia pluginów (`settings.schema`)

Ustawienia **deklaruje plugin, a renderuje host**. Plugin nie dostarcza `QDialog`:

*   sandboxowana wtyczka nie może przesłać widgetów przez IPC,
*   host pilnuje spójnego wyglądu, motywów, tłumaczeń i dostępności,
*   zapis, wartości domyślne i walidacja typów są w jednym miejscu,
*   formularz można przetestować bez uruchamiania procesu wtyczki.

```json
"settings": {
  "schema": {
    "compression": {
      "type": "enum",
      "title": "Compression method",
      "default": "deflate",
      "choices": [
        {"value": "deflate", "label": "Deflate"},
        {"value": "store", "label": "Store (no compression)"}
      ]
    },
    "compresslevel": {
      "type": "integer",
      "title": "Compression level",
      "description": "Ignored when the method is Store.",
      "default": 6,
      "minimum": 1,
      "maximum": 9
    }
  }
}
```

Obsługiwany jest zamknięty podzbiór typów:

| `type` | Wymagane pola | Widget hosta |
|---|---|---|
| `string` | `default` (string) | `QLineEdit` |
| `integer` | `default` (int), opcjonalnie `minimum` / `maximum` | `QSpinBox` |
| `boolean` | `default` (bool) | `QCheckBox` |
| `enum` | `default`, `choices` (`value` + `label`) | `QComboBox` |

Każde pole ma `title`; `description` trafia do tooltipa. `default` jest wymagany, żeby host
zawsze miał deterministyczną wartość początkową. Schemat jest walidowany przez
`app/plugin_settings.py`; nieznany `type`, brak `default`, wartość poza zakresem albo
`default` spoza `choices` to błąd konfiguracji.

Zasady:

*   Wartości są zapisywane w `settings.json` pod `plugin_settings.<plugin_id>`, a nie pod nazwą
    wyświetlaną. Nieznane klucze są zachowywane, więc aktualizacja pluginu nie kasuje
    ustawień, których nowa wersja hosta jeszcze nie zna.
*   Host tylko renderuje i sprawdza typy. Semantyczna walidacja (np. czy metoda kompresji
    jest obsługiwana) należy do pluginu, który i tak waliduje opcje w `create_task()`.
*   **Nie pokazujemy ustawienia, którego plugin nie honoruje.** Dlatego docelowo wspólne
    grupy (np. `archive.compression`) będą deklarowane jawnie przez plugin; na razie
    schemat opisuje tylko ustawienia konkretnej wtyczki.
*   Własny dialog pluginu (`settings.mode: "dialog"`) **nie jest** obsługiwany. To ewentualny
    wyjątek dla wtyczek in-process, nigdy dla sandboxowanych.
*   Kontrakt dla wbudowanych wtyczek pilnuje `tests/unit/test_bundled_plugin_settings.py`.

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

Wszystkie bundlowane, sandboxowane wtyczki z zadaniami używają stylu jawnego:
`checksum_standard`, `directory_size`, `copy_operation`, `delete_operation`,
`move_operation`, `file_splitter`, `rar_archiver`, `search_standard` oraz
`zip_archiver`. Kontrakt pilnuje `tests/unit/test_bundled_task_plugins_api.py`:
klasa wtyczki dziedziczy po `TaskPlugin`, `create_task` zwraca `PluginTask`,
`run` przyjmuje kontekst, a moduły wtyczki nie używają `AbstractTask`,
`self.context`, `emit_progress`, `emit_event` ani `request_user_input`.

`LegacyPluginAdapter` i `AbstractTask` pozostają w API dla wtyczek zewnętrznych,
które nie zostały jeszcze zmigrowane. Nowe wtyczki zawsze piszemy w stylu
jawnym.


### `FileOperationPlugin` (Bazowy)
Wspólny interfejs dla wszystkich wtyczek.
*   `name`: Nazwa wtyczki.
*   `description`: Opis wtyczki.

### `ArchivePlugin` (Typ: `archive`)
Interfejs dla wtyczek obsługujących archiwizację.
*   `get_supported_extensions()`: Zwraca listę obsługiwanych rozszerzeń (np. `['.zip']` albo `['zip']`; host normalizuje wielkość liter i wiodącą kropkę).
*   `create_archive(source_paths, destination_path, options, progress_callback, task_context, task, send_trace)`: Tworzy archiwum.
*   `extract_archive(archive_path, destination_path, options, progress_callback, task_context, task, send_trace)`: Wypakowuje archiwum. Wpisy wychodzące poza katalog docelowy (`../`, ścieżki absolutne) muszą być odrzucone przed zapisem — `zip_archiver` zgłasza wtedy `ValueError`.

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

### `org.quickfile.standard_editor`

Wbudowany edytor (F4) otwiera plik w **niemieszającym** oknie `EditorWindow`,
czyli `QMainWindow` z flagami `WindowMinMaxButtonsHint` i
`WindowCloseButtonHint`, a nie w modalnym `QDialog`.

* Jedno okno na ścieżkę pliku. Ponowne otwarcie tego samego pliku podnosi
  istniejące okno (`raise_`/`activateWindow`) zamiast tworzyć drugie.
* `Save` zapisuje plik i zamyka okno (dotychczasowe zachowanie). `Cancel`
  oraz zamknięcie okna przy niezapisanych zmianach pytają
  `Save` / `Discard` / `Cancel`; wybór `Cancel` zostawia okno otwarte.
* Zamknięcie okna bez zmian nie pokazuje pytania.
* `EditorWidget.has_unsaved_changes()` odpowiada
  `QTextDocument.isModified()`, a udany `save_file()` zeruje tę flagę.
* Okno jest usuwane po zamknięciu i wyrejestrowywane z listy otwartych
  edytorów wtyczki.

## Zarządzanie Wtyczkami (`PluginManager`)

Klasa `PluginManager` (`app/plugin_manager.py`) odpowiada za:
1.  **Skanowanie**: Przeszukuje katalog `plugins/` w poszukiwaniu poprawnych struktur wtyczek.
2.  **Ładowanie**: Dynamicznie ładuje moduły Pythona i tworzy instancje klas wtyczek. Dla wtyczek oznaczonych jako `sandboxed`, tworzy instancję `SandboxedPluginWrapper`, która uruchamia wtyczkę w osobnym procesie.
3. **Rejestrację**: Grupuje wtyczki według typu (`archive`, `checksum`, `directory_size`, `disk_utils`, `ui_extension`, `viewer`, `menu_action`) i udostępnia je reszcie
   aplikacji.
4.  **Instalację i Aktualizację**: Przy starcie porównuje zawartość wtyczek wbudowanych w aplikację z tymi zainstalowanymi u użytkownika (hash plików, nie numer wersji). Różnica oznacza odświeżenie kopii użytkownika z zachowaniem zainstalowanych `libs/`.

## Wtyczki zewnętrzne (`plugins-external`)

Nie każda wtyczka powinna być częścią wydania. Do katalogu zewnętrznego przenosimy wtyczkę, gdy:

*   wymaga programu w systemie hosta, którego aplikacja nie może dostarczyć (`rar_archiver` → `unrar`/`unar`/`bsdtar`/`7z`),
*   zależy od licencji, której nie wolno redystrybuować,
*   jest użyteczna tylko dla wąskiej grupy użytkowników.

**Lokalizacja:** `~/.config/QuickFile/plugins-external/`, z tym samym układem `groupId/artifactId/version`, co katalog instalacyjny.

Zasady:

*   Host skanuje oba katalogi; `plugins-external/` może nie istnieć i nie jest tworzony przy starcie.
*   Katalog zewnętrzny **nigdy** nie jest celem instalacji wbudowanych wtyczek: `_ensure_bundled_plugins` pisze wyłącznie do pierwszego wpisu `plugin_dirs`. Aktualizacja aplikacji nie dotyka plików użytkownika.
*   Brak sieci i auto-aktualizacji: instalacja to rozpakowanie katalogu wtyczki i restart. Sklep i instalator to osobny etap.
*   Wtyczka zewnętrzna podlega **wszystkim** regułom wydania: `sandboxed` przy `libs/`, `capabilities`, `settings.schema`, `external_tools` i walidacji metadanych.
*   **Kolizja `id`:** jeśli wtyczka o danym `id` jest już załadowana z katalogu instalacyjnego, kopia z `plugins-external/` jest pomijana, a konflikt trafia do logu jako błąd. Katalog użytkownika nie przesłania wtyczki z wydania — inaczej zgłoszenia błędów dotyczyłyby kodu, którego nie wydaliśmy.
*   Wtyczka usunięta z wydania **nie jest usuwana** z katalogu użytkownika; działa dalej, dopóki użytkownik sam jej nie usunie. To świadoma cena: stara kopia nie dostaje poprawek. Dlatego przeniesienie do external robimy dopiero wtedy, gdy istnieje sposób instalacji, który nie wymaga ręcznego kopiowania plików.

### `rar_archiver`

Wtyczka pozostaje wbudowana (1.0.4) do czasu powstania ścieżki instalacji. Dopiero potem jej katalog trafia do `plugins-external/`, a `plugins/` przestaje ją zawierać. Do tego czasu użytkownik bez backendu dostaje komunikat preflight, a nie błąd w środku zadania.

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
*   ✅ adapter dla wtyczek w obecnym stylu (`LegacyPluginAdapter`) — bez przepisywania pluginów zewnętrznych,
*   ✅ jawne API zadań dla nowych pluginów (`TaskPlugin` + `PluginTask` + `TaskPluginAdapter`, bez `AbstractTask._initialize`),
*   ✅ migracja wszystkich bundlowanych wtyczek zadań na styl jawny (kontrakt: `tests/unit/test_bundled_task_plugins_api.py`),
*   ✅ test protokołu dla każdego sandboxowanego pluginu — smoke `tests/unit/test_bundled_plugins_protocol.py` (handshake + `get_name` + `get_menu_actions` dla każdego sandboxowanego) oraz test e2e zadania per plugin; wtyczki in-process nie mówią protokołem,
*   ⬜ opcjonalna izolacja OS (Landlock/bubblewrap) jako osobny etap.

**Kontrakt protokołu jest zdefiniowany w [`runtime-protocol.md`](runtime-protocol.md).**
Ten dokument jest normatywny: wiadomości, pola, kody błędów, kolejność i
zachowanie przy zerwaniu kanału. Kodek (`app/plugin_system/protocol.py`) oraz
testy (`tests/unit/test_runtime_protocol.py`) egzekwują tę specyfikację.
