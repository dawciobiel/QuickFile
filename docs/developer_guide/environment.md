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

## Najczęstsze pułapki

| Objaw | Przyczyna | Rozwiązanie |
|---|---|---|
| `ModuleNotFoundError: PyQt6` | systemowy Python 3.9 | `direnv allow`, sprawdź `which python` |
| testy wiszą | stara wersja pluginu uruchamiająca `pip` | zaktualizuj gałąź; ładowanie pluginów nie instaluje zależności |
| `attempted relative import with no known parent package` | import relatywny w `plugin.py` | użyj płaskiego importu (`from tasks import ...`) |
| brak motywów/tłumaczeń | uruchomienie z innego katalogu roboczego | uruchamiaj z katalogu projektu; zasoby są w `resources/` |
