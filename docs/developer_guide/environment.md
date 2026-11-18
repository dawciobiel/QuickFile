# Środowisko developerskie

## Zasada: jedno źródło prawdy

Środowisko definiuje **wyłącznie `flake.nix`**. Nie używamy `python -m venv`, `pip install`
ani `pip freeze` w katalogu projektu. Mieszanie Nix-a, pip-a i ręcznego virtualenv było
przyczyną sytuacji, w której aplikacja „raz działała, raz nie”, zależnie od tego, która
sesja terminala była aktywna.

`requirements.txt` istnieje jako **ścieżka drugorzędna** dla systemów bez Nix
(Windows, macOS, CI). Na Linuksie z Nix nie jest używany.

## Szybki start

```bash
direnv allow        # po każdej zmianie .envrc
```

Weryfikacja, że jesteś w poprawnym środowisku:

```bash
which python        # musi wskazywać /nix/store/...-python3.12...-env/bin/python
python -V           # Python 3.12.x
python -c "import PyQt6.QtCore as c; print(c.PYQT_VERSION_STR)"   # 6.8.0
```

Jeśli `which python` wskazuje `/usr/bin/python`, `.envrc` nie jest załadowany —
uruchom `direnv allow` albo wejdź w katalog projektu ponownie.

Bez direnv:

```bash
nix develop
```

## Uruchomienie aplikacji

```bash
python main.py
```

## Testy

```bash
python -m pytest tests/unit -q
python -m pytest tests/e2e -q
```

Testy nie wymagają przygotowywania `HOME` ani kopiowania pluginów: `PluginManager`
sam instaluje wbudowane wtyczki w `~/.config/QuickFile/plugins`. Do izolacji wystarczy
podstawić dowolny katalog:

```bash
HOME=/tmp/quickfile-test QT_QPA_PLATFORM=offscreen python -m pytest tests/e2e -q
```

`QT_QPA_PLATFORM=offscreen` jest wymagane na maszynie bez wyświetlacza.

Wtyczki spoza wydania (te, które wymagają programu w systemie albo nie mogą być
redystrybuowane) leżą w `~/.config/QuickFile/plugins-external/`. Ten katalog jest tylko
skanowany: aplikacja nic do niego nie instaluje i nie odświeża. Kolizja `id` z wtyczką
z wydania jest logowana jako błąd, a kopia zewnętrzna jest pomijana.

Ich źródła leżą w repozytorium w `plugins-external/<grupa>/<artefakt>/<wersja>/`. Ten katalog
nie jest częścią wydania: `PluginManager` czyta wyłącznie `plugins/`, a `plugins-external/`
służy do budowania paczek.

Instalacja wtyczki zewnętrznej to jawna akcja offline:

```bash
python -m app.plugin_installer install <paczka.zip|katalog>
```

## Dodawanie zależności

1. Dopisz pakiet do listy `python312.withPackages` w `flake.nix`.
2. `direnv reload` (albo ponowne wejście w katalog).
3. Jeśli zależność ma działać także na ścieżce pip — dopisz ją do `requirements.txt`
   i `dependencies` w `pyproject.toml`, w wersji zgodnej z nixpkgs.

Nie instaluj niczego przez `pip` w devShellu: zmiana zniknie przy następnym wejściu
w katalog i rozjedzie się z definicją środowiska.

## Pakowanie

```bash
python -m build --wheel
unzip -l dist/*.whl | less
```

Wheel zawiera kod aplikacji, zasoby (`resources/`), pliki `.ui` oraz wtyczki wbudowane
(jako dane — katalogi wtyczek nie są importowalnymi pakietami). Po instalacji
`QuickFile` jest dostępny jako komenda GUI i przy pierwszym starcie instaluje wbudowane
wtyczki w `~/.config/QuickFile/plugins`.

Dystrybucja desktopowa odbywa się przez PyInstaller: `scripts/package_builder/build_app.py`.

Paczki pojedynczych wtyczek (format przyjmowany przez instalator) buduje:

```bash
python scripts/build_plugin_package.py --all            # dist/plugins/*.zip
python scripts/build_plugin_package.py plugins/org.quickfile/zip_archiver
python scripts/build_plugin_package.py --all --source-root plugins-external --output dist/plugins-external
```

Budowanie jest deterministyczne i kończy się instalacją własnego wyniku w katalogu
tymczasowym — paczka, której nie da się zainstalować, nie powstaje. Wtyczki zewnętrzne mają
źródła w `plugins-external/`, więc buduje się je drugim wywołaniem z `--source-root`.

Publikacja paczek w GitHub Release:

```bash
python scripts/publish_plugin_packages.py --tag v0.21.15 \
    --packages dist/plugins dist/plugins-external
```

Skrypt jest idempotentny i odmawia nadpisania assetu o innym SHA-256. `--dry-run` pokazuje
plan, a `--create-release` tworzy wydanie dla istniejącego tagu. Workflow
`.github/workflows/plugin-release.yml` robi to samo na push tagu `v*` albo ręcznie.

## Najczęstsze pułapki

| Objaw | Przyczyna | Rozwiązanie |
|---|---|---|
| `ModuleNotFoundError: PyQt6` | systemowy Python 3.9 | `direnv allow`, sprawdź `which python` |
| testy wiszą | stara wersja pluginu uruchamiająca `pip` | zaktualizuj gałąź; ładowanie pluginów nie instaluje zależności |
| `attempted relative import with no known parent package` | import relatywny w `plugin.py` | użyj płaskiego importu (`from tasks import ...`) |
| brak motywów/tłumaczeń | uruchomienie z innego katalogu roboczego | uruchamiaj z katalogu projektu; zasoby są w `resources/` |
