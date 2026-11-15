# Protokół runtime'u pluginów (v1)

Status: **specyfikacja**. Ten dokument jest normatywny — testy w
`tests/unit/test_runtime_protocol.py` egzekwują opisaną tu kodę wiadomości.
Implementacja runtime'u (etap C) musi być z nią zgodna; zmiana protokołu wymaga
podniesienia wersji, nie „cichej” zmiany pól.

## 1. Zakres

Protokół opisuje komunikację między **hostem** (proces aplikacji QuickFile) a
**procesem pluginu**. Zastępuje dotychczasowe, nieformalne słowniki z kluczem
`type`, które krążyły między `SandboxedPluginWrapper` a `PluginWorker`.

Czego protokół **nie** zapewnia:

* **Bezpieczeństwa.** Proces pluginu działa z uprawnieniami użytkownika i ma
  dostęp do jego plików, sieci i środowiska. Protokół daje izolację *awarii* i
  przewidywalne sterowanie, nie piaskownicę uprawnień. Zaufanie deklaruje
  użytkownik/host — patrz `plugins.md`, sekcja „Izolacja Procesów”.
* **Przetrwania awarii hosta.** Gdy host zniknie, plugin kończy pracę.

## 2. Transport

* Kanał: `multiprocessing.Pipe(duplex=True)` (`multiprocessing.connection.Connection`).
* Ramkowanie: jedna wiadomość = jedno wywołanie `send()` / `recv()`. Warstwa
  transportu nie skleja i nie dzieli wiadomości.
* Kodowanie: pickle (ograniczenie `Connection`). W polach wolno przesyłać
  wyłącznie typy serializowalne: `None`, `bool`, `int`, `float`, `str`,
  `bytes`, `list`, `tuple`, `dict` o takich kluczach i wartościach.
  Obiekty Qt, deskryptory plików i obiekty domenowe hosta są zabronione.
* Kanał jest **duplex** i asynchroniczny: żadna ze stron nie może założyć, że
  odpowiedź przyjdzie natychmiast.

## 3. Koperta wiadomości

Każda wiadomość to słownik:

```python
{
    "v": 1,                      # wersja protokołu, int, wymagane
    "type": "EXECUTE_TASK",      # nazwa typu, str, wymagane
    "id": "0f3c...",             # opcjonalny identyfikator wiadomości (diagnostyka)
    # ...pola zależne od typu, płasko na najwyższym poziomie
}
```

Zasady:

1. `v` i `type` są zawsze obecne. Brak któregokolwiek = błąd protokołu.
2. Pola niezależne od typu są **płaskie** — bez zagnieżdżonej koperty `payload`.
3. **Nieznane pola są ignorowane** i zachowywane przy ponownym kodowaniu
   (kompatybilność w przód: nowszy nadawca, starszy odbiorca).
4. **Nieznany `type` nie jest błędem krytycznym.** Odbiorca loguje go i
   ignoruje. Wyjątkiem jest sytuacja, gdy nie da się kontynuować: surowa
   wiadomość nie jest słownikiem albo nie ma `type` — wtedy kanał jest
   zamykany, bo nie ma sposobu na resynchronizację strumienia.
5. Wartości `task_id`, `call_id`, `request_id` to nieprzezroczyste stringi
   generowane przez hosta i unikalne w czasie życia procesu.

## 4. Wersjonowanie

* Wersja bieżąca: **1**. Host i plugin deklarują zakres wspieranych wersji.
* Host wysyła pierwszy `HELLO` z `protocol_min` i `protocol_max`.
* Plugin wybiera **najwyższą wspólną** wersję i odpowiada `READY` z
  `protocol_version`. Brak części wspólnej → `ERROR` z
  `code="PROTOCOL_MISMATCH"`, potem wyjście z procesu.
* Plugin, który nie potrafi odczytać `HELLO`, kończy proces bez zgadywania
  wersji.
* Host nie wysyła wiadomości nowszego typu, jeśli wynegocjowana wersja jest
  niższa.

## 5. Wiadomości

Kolumna „Kierunek”: `H→P` (host do pluginu), `P→H` (plugin do hosta).

### 5.1. Host → plugin

| Typ | Wymagane pola | Opcjonalne | Znaczenie |
|---|---|---|---|
| `HELLO` | `protocol_min: int`, `protocol_max: int`, `plugin_id: str` | `host_version: str` | Pierwsza wiadomość sesji; negocjacja wersji. |
| `EXECUTE_TASK` | `task_id: str`, `action_id: str` | `kwargs: dict` (domyślnie `{}`) | Zlecenie zadania; `kwargs` trafia do fabryki zadań pluginu. |
| `CANCEL_TASK` | `task_id: str` | — | Prośba o anulowanie. |
| `PAUSE_TASK` | `task_id: str` | — | Prośba o wstrzymanie (kooperacyjne). |
| `RESUME_TASK` | `task_id: str` | — | Wznowienie po `PAUSE_TASK`. |
| `CALL` | `call_id: str`, `method: str` | `args: list`, `kwargs: dict` | Synchroniczne RPC dla szybkich zapytań. |
| `INPUT_RESPONSE` | `request_id: str`, `value: any` | — | Odpowiedź na `INPUT_REQUEST`; `value=None` = brak odpowiedzi / nieobsługiwane. |
| `SHUTDOWN` | — | `reason: str` | Prośba o zakończenie procesu. |

### 5.2. Plugin → host

| Typ | Wymagane pola | Opcjonalne | Znaczenie |
|---|---|---|---|
| `READY` | `protocol_version: int`, `plugin_id: str`, `plugin_version: str`, `methods: list[str]` | — | Pierwsza wiadomość pluginu; koniec startu. |
| `PROGRESS` | `task_id: str`, `percent: int` | — | Postęp 0–100. |
| `EVENT` | `task_id: str`, `name: str` | `payload: dict` | Zdarzenie domenowe dla UI (`handle_event`). |
| `RESULT` | `task_id: str` | `value: any` | Zakończenie sukcesem. |
| `ERROR` | `code: str`, `message: str` | `task_id: str\|None`, `traceback: str` | Błąd zadania (`task_id`) lub procesu (`task_id` brak/`None`). |
| `CANCELLED` | `task_id: str` | — | Zadanie przerwane na skutek anulowania. |
| `RETURN` | `call_id: str`, `ok: bool` | `value: any`, `error: str`, `traceback: str` | Odpowiedź na `CALL`. |
| `INPUT_REQUEST` | `request_id: str`, `name: str` | `task_id: str`, `payload: dict` | Prośba o dane od użytkownika (v1: opcjonalna). |
| `LOG` | `level: str`, `message: str` | `task_id: str` | Log z procesu pluginu do logu hosta. |
| `BYE` | — | `reason: str` | Grzeczne zamknięcie kanału przed wyjściem. |

### 5.3. Kody błędów

| Kod | Kiedy |
|---|---|
| `PROTOCOL_ERROR` | Wiadomość poprawnej wersji, ale niezgodna ze schematem. |
| `PROTOCOL_MISMATCH` | Brak wspólnej wersji protokołu. |
| `MISSING_DEPENDENCY` | Brak zadeklarowanej zależności Pythona. |
| `PLUGIN_UNAVAILABLE` | Kanał zerwany / proces nie żyje. |
| `CANCEL_TIMEOUT` | Zadanie nie zareagowało na anulowanie w założonym czasie. |
| `TIMEOUT` | Przekroczony czas `CALL` lub startu. |
| `INTERNAL` | Wyjątek w kodzie pluginu bez własnego kodu. |

Kody są stabilnym API — UI może je mapować na komunikaty. Nowe kody mogą się
pojawiać; nieznany kod należy traktować jak `INTERNAL`.

## 6. Cykl życia

```
        ┌──────────┐  HELLO/READY   ┌───────┐  EXECUTE_TASK   ┌──────┐
spawn ─▶│ STARTING │ ─────────────▶ │ READY │ ──────────────▶ │ BUSY │
        └──────────┘                └───────┘ ◀────────────── └──────┘
             │                          │      RESULT/ERROR/      │
             │ timeout, ERROR,          │      CANCELLED          │
             │ BYE, EOF                 │                         │
             ▼                          ▼                         ▼
        ┌──────────────────────────────────────────────────────────────┐
        │                            DEAD                              │
        └──────────────────────────────────────────────────────────────┘
```

Zasady:

1. **`READY` musi być pierwszą wiadomością pluginu.** `LOG` przed `READY` jest
   dozwolony. Cokolwiek innego przed `READY` kończy start jako błąd.
2. Host czeka na `READY` maksymalnie `startup_timeout` (domyślnie 5 s).
   Przekroczenie = proces uznany za martwy i kończony.
3. **Dokładnie jedna wiadomość terminalna na `task_id`**: `RESULT`, `ERROR` albo
   `CANCELLED`. Po niej żadna wiadomość tego zadania nie może przyjść.
4. `SHUTDOWN` kończy przyjmowanie nowych zadań. Trwające zadania dostają
   `CANCEL_TASK`-owe traktowanie (flaga anulowania), a proces ma
   `shutdown_grace` (domyślnie 2 s) na wyjście; potem `terminate()`.
5. Po `DEAD` host nie wskrzesza procesu w locie (v1). Nowe zadania dla tego
   pluginu kończą się natychmiast `ERROR` `code="PLUGIN_UNAVAILABLE"`.

### 6.1. `EXECUTE_TASK` i współbieżność

v1: **jedno zadanie naraz na proces pluginu**. Kolejne `EXECUTE_TASK` trafiają
do kolejki FIFO i startują po terminalnej wiadomości poprzedniego.

Uzasadnienie: plugin jest jedną instancją ze wspólnym stanem, a serializacja
daje deterministyczne testy i przewidywalne anulowanie. Równoległość uzyskuje
się przez wiele procesów (różne pluginy), nie przez wiele zadań w jednym.

`CANCEL_TASK` dla zadania w kolejce usuwa je z kolejki i natychmiast wysyła
`CANCELLED` — bez uruchamiania logiki pluginu.

`EXECUTE_TASK` z `task_id`, który już istnieje (aktywne lub w kolejce), jest
błędem hosta: plugin odpowiada `ERROR` `code="PROTOCOL_ERROR"` i nie uruchamia
drugiego zadania.

## 7. Anulowanie i pauza

* Anulowanie jest **kooperacyjne**. Plugin musi regularnie sprawdzać
  `ctx.is_cancelled()` i przerwać pracę. Protokół nie jest w stanie przerwać
  dowolnego wywołania I/O.
* `CANCEL_TASK` jest obsługiwane przez wątek IPC i ustawia flagę
  natychmiast — nie czeka w kolejce za logiką biznesową zadania.
  Docelowa latencja reakcji: **< 200 ms**.
* Zadanie, które zakończy się po anulowaniu, wysyła `CANCELLED` (nie `RESULT`).
* Jeśli zadanie nie zareaguje w `cancel_timeout` (domyślnie 5 s), host kończy
  proces, a wszystkie zadania dostają `ERROR` `code="CANCEL_TIMEOUT"`.
* Pauza jest również kooperacyjna: `wait_if_paused()` blokuje **wątek
  roboczy**, nigdy wątek IPC. Anulowanie w trakcie pauzy wygrywa i budzi
  zadanie.
* `PAUSE_TASK`/`RESUME_TASK`/`CANCEL_TASK` dla nieznanego `task_id` są
  ignorowane i logowane — to normalny wyścig z zakończeniem zadania.

## 8. Gwarancje kolejności i backpressure

1. Wiadomości w jednym kierunku docierają w kolejności wysłania (gwarancja
   `Pipe`).
2. `PROGRESS` i `EVENT` dla danego zadania poprzedzają jego wiadomość
   terminalną.
3. `PROGRESS` jest monotoniczny w obrębie zadania; host może go przyciąć do
   0–100 i ostrzec przy cofnięciu.
4. `PROGRESS` wolno **koalescować** (nadawca może pominąć wartości, host może
   ograniczyć częstotliwość). `RESULT`, `ERROR`, `CANCELLED`, `RETURN`
   koalescencji nie podlegają.
5. Wątek IPC hosta **nigdy** nie wykonuje logiki biznesowej ani nie blokuje się
   na UI. W przeciwnym razie pełny bufor `Pipe` zablokuje plugin.
6. `CALL` wykonuje się w kolejce wątku roboczego, więc może czekać za
   zadaniem. Host nie powinien wołać `CALL`, gdy plugin jest `BUSY`; timeout
   `CALL` (domyślnie 5 s) chroni przed zawieszeniem UI.

## 9. Zerwanie kanału

| Sytuacja | Zachowanie hosta | Zachowanie pluginu |
|---|---|---|
| `EOFError`/`BrokenPipeError` w wątku IPC hosta | wszystkie aktywne zadania → `ERROR` `code="PLUGIN_UNAVAILABLE"`; stan `DEAD`; żadna wiadomość nie jest wysyłana do martwego procesu | — |
| `EOFError`/`BrokenPipeError` w wątku IPC pluginu | — | koniec pętli, flaga anulowania dla zadań, wyjście z kodem 0 w `shutdown_grace` |
| Proces pluginu kończy się bez `BYE` | jak zerwanie kanału; kod wyjścia trafia do logu | — |
| Wyjątek w pętli IPC pluginu | `ERROR` (procesowy) z `traceback`, potem wyjście | — |

Zapis do zamkniętego kanału jest zawsze traktowany jako „kanał martwy”, nie
jako błąd do ponowienia.

## 10. Zgodność ze starymi pluginami

Pluginy w obecnym stylu (`PluginBase.create_task`, `AbstractTask.run`) nie
znają protokołu. Runtime dostarcza adapter, który:

* tłumaczy `EXECUTE_TASK` na `plugin.create_task(action_id, **kwargs)` i
  `task._initialize(ctx, progress, event, input)`,
* mapuje `emit_progress` → `PROGRESS`, `emit_event` → `EVENT`, powrót z `run()`
  → `RESULT`, wyjątek → `ERROR` (`INTERNAL`) lub `CANCELLED`, gdy flaga jest
  ustawiona,
* implementuje `TaskContext` na `WorkerTaskContext` (jak dziś) i podłącza je do
  `CANCEL_TASK`/`PAUSE_TASK`/`RESUME_TASK`.

Dzięki temu etap C nie wymaga przepisania wszystkich pluginów naraz. Nowe
pluginy mogą używać jawnego API zadań bez zmian w protokole.

## 11. Co testujemy

Testy protokołu nie wymagają Qt ani prawdziwego systemu plików:

1. **Kodek** — koperta, wymagane pola, nieznane pola, nieznany typ, zła wersja.
2. **Negocjacja** — wspólna wersja, brak wspólnej wersji.
3. **Atrapa pluginu** (`tests/support/dummy_plugin.py`) — akcje: natychmiastowy
   wynik, postęp, błąd, ignorowanie anulowania, długie zadanie.
4. **Runtime** (po implementacji) — start/`READY`, wynik, błąd, anulowanie
   < 200 ms, anulowanie zadania w kolejce, zerwanie kanału, zawieszenie
   pluginu nie blokuje UI.

Testy runtime'u uruchamiają prawdziwy proces, ale z atrapą pluginu — bez
zależności zewnętrznych i bez sieci.
