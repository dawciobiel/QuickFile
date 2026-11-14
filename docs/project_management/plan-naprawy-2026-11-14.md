# Plan naprawy QuickFile — decyzje i kolejność prac

**Data:** 2026-11-14
**Status:** zatwierdzony kierunek, wykonanie w nowej sesji
**Autor analizy:** sesja AI po przeglądzie architektury, historii git i środowiska

---

## 1. Decyzje (wiążące)

| Obszar | Decyzja |
|---|---|
| Droga rozwoju | **A: recovery-first od `d4fb01d`**, następnie **C: nowy runtime pluginów (v3)** |
| Środowisko | **Nix-only** — `flake.nix` jest jedynym źródłem prawdy |
| Odrzucone | B (dokańczanie refaktoru na HEAD), D (de-scope pluginów) |
| Model zaufania | proces = izolacja awarii, **nie** bezpieczeństwo; zaufanie decyduje host/użytkownik |

---

## 2. Punkt odniesienia (baseline)

**`d4fb01d`** — `master` / `origin/master`, „Remove drag-and-drop and clipboard functionality”.

Zmierzone w worktree `/tmp/opencode/qf-d4fb01d` (Python 3.12.8, PyQt6 6.8, `QT_QPA_PLATFORM=offscreen`, izolowany `HOME`):

| Zestaw | Wynik |
|---|---|
| `tests/unit` | **96 passed, 3 skipped** |
| `tests/e2e` | **7 passed** (copy, delete, move, rename, new folder, search, sync) |

Wymagania wstępne testów (inaczej testy wiszą):

```bash
export HOME=/tmp/opencode/qf-home
mkdir -p "$HOME/.config/QuickFile/plugins"
cp -r plugins/* "$HOME/.config/QuickFile/plugins/"
mkdir -p "$HOME/.config/QuickFile/plugins/org.quickfile/file_splitter/1.1.1/libs"
touch "$HOME/.config/QuickFile/plugins/org.quickfile/file_splitter/1.1.1/libs/.keep"
```

Powód: plugin `file_splitter` przy starcie robi `pip install PyQt6` do `libs/` — przy braku sieci to zawiesza test. **Ten mechanizm trzeba usunąć** (patrz krok A3).

---

## 3. Co zepsuło HEAD (`b84c30a`)

`b84c30a` „Extensive refactor…” — 264 pliki, refaktor zastosowany w połowie:

1. Usunięte `tasks.py` z `copy_operation`, `delete_operation`, `move_operation`
   (`git show b84c30a -- plugins/org.quickfile/copy_operation` → `181 ---`).
2. `plugin.py` importuje `from .tasks import CopyTask`, ale loader importuje `plugin.py`
   **po ścieżce pliku, bez pakietu** → `ImportError: attempted relative import with no known parent package`.
3. Katalogi wersji przemianowane `1.0.0` → `1.0.4` bez porządku; w jednym drzewie jest
   6 wersji (`1.0.0`, `1.0.3`, `1.0.4`, `1.1.0`, `1.1.1`, `1.3.0`).
4. UI wywołuje nieistniejące API: `get_context_menu_plugins_for_paths`,
   `execute_plugin_action`, `get_archiver_for_file`, `plugin.get_configuration_dialog`, `plugin.id`.
   Efekt: `get_plugin_for_action("copy_items")` = **30 s** (3 × 10 s timeout) i `None`.
5. `SandboxedPluginWrapper.__getattr__` robi **synchroniczne RPC** → każde sprawdzenie
   „czy plugin ma metodę” blokuje UI na 10 s.
6. `background_task_manager.resume_task` używa nieistniejących
   `self.active_tasks` / `self.background_task_manager`.
7. `task_queue_manager` zakłada sygnały Qt `progress_updated` od procesu sandboxowanego.
8. Wheel: 157 plików, tylko `quickfile/plugins/base.py`, **zero pluginów i tłumaczeń**.

`c52cb4b` dotyczy wyłącznie flake/direnv — nie naprawia niczego z powyższego.

**Wniosek:** HEAD to niedokończony eksperyment. Nie łatać — odtworzyć.

---

## 4. Diagnoza środowiska

`direnv` **nie** jest przyczyną problemów z pluginami. Pod direnv sandboxowane pluginy
startują i komunikują się przez `Pipe` (potwierdzone w logach: 8 procesów, `Sandbox process started`).

Prawdziwy problem: **cztery konkurencyjne źródła prawdy**.

| Źródło | Co mówi |
|---|---|
| `flake.nix` | Python 3.12 + PyQt6 6.8 (nixpkgs 24.11) |
| `.envrc` | `use flake`, potem tworzy `.venv` na nixowym Pythonie + `pip install -e .` |
| `pyproject.toml` | `PyQt6==6.10.1` |
| `requirements.txt` | `pip freeze`, PyQt6 6.8.0 + `-e git+ssh://…@d4fb01d#egg=QuickFile` |
| plugin `file_splitter` | runtime `pip install PyQt6` do `libs/` |

Zmierzone skutki:

- `.venv/pyvenv.cfg` → `command = … -m venv /home/dawciobiel/tmp/QuickFile_alma_version/.venv` (stara ścieżka)
- `.venv/bin/pip` → `zły interpreter: Nie ma takiego pliku ani katalogu`
- `direnv status` → `No .envrc or .env loaded` (środowisko nieaktywne w sesji)
- poza devShellem `python3` = **3.9.25**, brak `quickfile`, brak `pytest`
- `requirements.txt` przypina projekt do `d4fb01d` — „instalacja z repo” cofa kod do mastera

To tłumaczy niereprodukowalność: zależnie od sesji trafiasz w devShell, `.venv` albo Python 3.9.

---

## 5. Zasada bezpieczeństwa pluginów

- Izolacja procesowa = izolacja **awarii**, nie bezpieczeństwo.
- Obecny „sandbox” to `fork()` + `Pipe`: ten sam UID, cały FS użytkownika, sieć, `os.environ`,
  `~/.ssh`. Złośliwy plugin może wszystko, co użytkownik.
- `"sandboxed": true` w `metadata.json` to **przełącznik trybu**, nie granica bezpieczeństwa.
  Docelowo przemianować na `isolation: "process"`, żeby nazwa nie obiecywała ochrony.
- Zaufanie deklaruje **host/użytkownik** (źródło instalacji, explicite „instaluję na własną
  odpowiedzialność”), nigdy sam plugin w metadanych.
- Realne bezpieczeństwo (później, opcjonalnie): `bubblewrap`/Landlock/seccomp dla limitów
  FS/syscalli, albo WASM dla kodu naprawdę niezaufanego. Nie w ramach etapu A.

Komunikat dla użytkownika: **„pluginy trzecich stron uruchamiasz na własne ryzyko”**.

---

## 6. Etap A — recovery-first

Zasada: **każdy krok = osobny commit, testy zielone po commicie**. Jeśli krok nie może
przejść na zielono, jest za duży — dzielić.

### A0. Przygotowanie (przed przeniesieniem projektu)

```bash
# 1. Zabezpiecz niezacommitowaną migrację (tłumaczenia, resources, docs, launch.sh, todo/)
git status --short          # zapisz listę
git stash push -u -m "wip: ręczny powrót do layoutu sprzed src/"   # ALBO commit na boku

# 2. Usuń zepsuty worktree (po przeniesieniu ścieżka /tmp/opencode/qf-d4fb01d i tak umrze)
git worktree remove --force /tmp/opencode/qf-d4fb01d

# 3. Wyczyść artefakty ze ścieżkami absolutnymi — odtworzą się same
rm -rf .venv .direnv .direnv_pyproject_hash .direnv_freeze_hash

# 4. Po przeniesieniu: sprawdź, czy nic nie zostało ze starych ścieżek
grep -rn "PyCharmProjects\|/home/dawciobiel/tmp" .idea/ 2>/dev/null
```

Nie kopiuj: `.venv/`, `.direnv/`, `__pycache__/`, `logs/`, `.pytest_cache/`, `dist/`, `build/`.
`git` sam jest przenośny; `worktree` i `.venv` — nie.

### A1. Baseline

```bash
git switch -c recovery/plugin-runtime master    # master == d4fb01d
```

Kryterium: `tests/unit` 96 passed / 3 skipped, `tests/e2e` 7 passed.

### A2. Środowisko Nix-only

`flake.nix` — Python 3.12 z pakietami (bez `pip` w shellu, żeby nie kusiło):

```nix
(pkgs.python312.withPackages (ps: with ps; [
  pyqt6 requests psutil rarfile send2trash docopt
  pytest pytest-mock pytest-order pytest-qt
  ruff pyright
]))
```

`.envrc` — redukcja do:

```bash
use flake
export QUICKFILE_PLUGIN_PATH="$PWD/plugins"
# QUICKFILE_SANDBOX / RESOURCES / THEMES / TRANSLATIONS: kod ich NIE używa
# — albo usunąć, albo najpierw zaimplementować ich odczyt w kodzie
```

Usunąć z `.envrc`: tworzenie `.venv`, `source .venv/bin/activate`, `pip install -e .`,
`pip install -r`, `pip freeze > requirements.txt`, cache hashów.

`requirements.txt` — **usunąć z repo** (to artefakt `pip freeze`, a nie lock; dodatkowo
przypina `d4fb01d`). Metadane projektu żyją w `pyproject.toml`.

`pyproject.toml` — usunąć `PyQt6==6.10.1`, zostawić zakres zgodny z flake (`>=6.8,<6.9`)
albo w ogóle nie pinować w metadanych.

Kryterium: `which python` → ścieżka z `/nix/store/`, `python -c "import PyQt6; print(PyQt6.__file__)"`,
`pytest --version`, `direnv status` pokazuje załadowany `.envrc`. Zero `.venv` w repo.

### A3. Higiena pluginów (drobne, niezależne commity)

1. **Usunąć runtime `pip install`** z `file_splitter` — plugin nie instaluje zależności.
   Brakującą zależność deklaruje `metadata.json` (`dependencies`), a instaluje ją host
   przy instalacji pluginu, nie przy starcie.
2. **Naprawić wersjonowanie katalogów** — jedna wersja na plugin; stare wersje usuwać
   świadomie, nie trzymać 6 wersji równolegle.
3. **Loader pluginów**: import przez `importlib.util.spec_from_file_location` z poprawnym
   `submodule_search_locations` albo — prościej i bezpieczniej — **zakazać importów
   relatywnych w `plugin.py`** i wymagać `from tasks import ...` (tak jak w `d4fb01d`).
   Wybrać jedno i zapisać w `docs/architecture/plugins/`.
4. **`PluginManager`: minimalne API.** Każda metoda, której brakuje, to albo 2 linie kodu,
   albo usunięcie wywołania z UI. Preferować usunięcie — mniejsze API = mniej długu.
5. **Zakaz synchronicznego RPC w `__getattr__`.** Jawne `has_method()` / `call(method, *args)`
   z timeoutem, wołane tylko tam, gdzie wynik jest naprawdę potrzebny w danej chwili.

Kryterium po każdym punkcie: testy zielone, `get_plugin_for_action("copy_items")` < 1 s.

### A4. Pakowanie

Decyzja do potwierdzenia w nowej sesji (rekomendacja poniżej):

- **Kod rdzenia** → `src/quickfile/` (`app`, `ui`, `utils`, `panels`, `browser`,
  `file_operations`, `favorites`, `config`) + mechaniczna zmiana importów `app.` → `quickfile.app.`.
  Testy jako brama — to duży, ale czysto mechaniczny commit.
- **Pluginy zostają POZA pakietem.** To nie przypadek, że `b84c30a` wsadził je do
  `src/quickfile/plugins/` i natychmiast zrobił bałagan z wersjami. Plugin zewnętrzny
  nie jest częścią aplikacji — w produkcji żyje w `~/.config/QuickFile/plugins`,
  w dev wskazujemy `PluginManager`-em na repo `plugins/`.
- **`translations/`, `resources/`, `themes/`** — jedno miejsce, jawnie zadeklarowane
  w `pyproject.toml` jako `package-data` (lub `data_files`). Nie duplikować w `src/` i w root.

Kryterium: `python -m build`, potem `unzip -l dist/*.whl` → są tłumaczenia, zasoby, brak
`site-packages/quickfile/plugins/org.quickfile/...`; instalacja z wheel startuje aplikację.

### A5. Dokumentacja

- `docs/architecture/plugins/plugins.md` — zaktualizować: kontrakt pluginu, brak importów
  relatywnych, `isolation: "process"`, model zaufania.
- `docs/project_management/BUGS.md` — zamknąć punkty rozwiązane, dopisać nowe.
- Krótki `docs/developer_guide/environment.md` — Nix-only, jak uruchomić testy, jak
  przygotować `HOME` dla e2e.

**Koniec etapu A: aplikacja działa, testy zielone, jedno środowisko, wheel używalny.**

---

## 7. Etap C — nowy runtime pluginów (v3)

Dopiero po zielonym etapie A. Wg `docs/architecture/plugins/redesign_plan.md`:

1. **Wątek IPC** — tylko nasłuch `Pipe`, zero operacji biznesowych.
2. **Wątek roboczy** — wykonuje zadanie, raportuje postęp, sprawdza cancel/pause.
3. **Protokół asynchroniczny** — `EXECUTE_TASK`, `CANCEL_TASK`, `PAUSE_TASK`,
   `INPUT_REQUEST`/`INPUT_RESPONSE`, `PROGRESS`, `RESULT`, `ERROR`. Wersjonowany.
4. **Jawne API zadań** — `AbstractTask` z kontraktem `run(ctx)`, `ctx.progress()`,
   `ctx.is_cancelled()`. Koniec z magicznymi metodami przez `__getattr__`.
5. **Adapter** dla pluginów w starym stylu, żeby nie przepisywać wszystkiego naraz.
6. **Testy protokołu** na atrapie pluginu (bez Qt, bez FS) — szybkie, deterministyczne.
7. Opcjonalnie, jako osobny etap: `isolation: "process"` + limity OS (Landlock/bubblewrap).

Kryterium: anulowanie działa w < 200 ms podczas kopiowania dużego pliku; zawieszenie
pluginu nie blokuje UI; każdy plugin ma test protokołu.

---

## 8. Pułapki, które już raz zabolały

- **Nie** przenosić `pip install -e .` do `.envrc` razem z Nixem — to był root cause bałaganu.
- **Nie** robić `pip freeze > requirements.txt` — to nie lock, a zapis stanu lokalnego.
- **Nie** trzymać wielu wersji tego samego pluginu w jednym drzewie bez powodu.
- **Nie** wołać metod pluginu przez `__getattr__` w kodzie synchronicznym UI.
- **Nie** importować `plugin.py` jako części pakietu, jeśli plugin ma być instalowany
  przez użytkownika — używać importu po ścieżce i płaskich importów wewnątrz pluginu.
- **Nie** ufać `metadata.json` w kwestii bezpieczeństwa.
- Testy sandboxowane wymagają przygotowanego `HOME` i `QT_QPA_PLATFORM=offscreen`.

---

## 9. Komendy weryfikacyjne (działające)

```bash
# środowisko
direnv allow
which python && python -V          # → /nix/store/.../python3.12

# testy jednostkowe
HOME=/tmp/opencode/qf-home QT_QPA_PLATFORM=offscreen \
  python -m pytest tests/unit -q

# e2e
HOME=/tmp/opencode/qf-home QT_QPA_PLATFORM=offscreen \
  python -m pytest tests/e2e -q

# pakowanie
python -m build && unzip -l dist/*.whl | less
```
