# TODO List

# Important notes

- **Important**: Każdą funkcjonalność rozwiązywać na własnym dla niej branch-u.

## Planowane Funkcjonalności (Planned Features)

### Interfejs Użytkownika (User Interface)

- **New Feature:** Dodać button jako rozwijalną listę, z której można wybrać napęd i ewentualne zamontowane urządzenia. Ta rozwijalna lista
  powinna znajdować się nad panelem do przeglądania plików.
- **New Feature:** W dolnej części panelu przeglądania plików dodać pole podsumowania. Wyświetlające np. ilość i wielkość zaznaczonych
  plików. Lub np. pełne dane pliku, na którym znajduje się kursor.
- **New Feature:** Panel do przeglądania zawartości plików powinien być osadzony wewnątrz komponentu "Multi Tabs". W ten sposób będzie można
  mieć otwartych jednocześnie wiele zakładek z katalogami.
- **New Feature:** Dodać możliwość zapamiętania domyślnej lokalizacji paneli do przeglądania plików. Trzeba się zastanowić jaki rodzaj GUI
  do tej funkcji stworzyć.
- **New Feature:** Okno Ustawień Aplikacji powinno być zrobione z użyciem "Multi Tabs" lub "Tree View".
- **New Feature:** Dodać buttons przy text-filed ze ścieżką wskazującą na aktualny przeglądany katalog. Musi działać zależnie od systemu, na
  którym uruchomiona jest aplikacja (linux, Windows, MacOS). Buttony te powinny być konfigurowalne i umożliwiać zmianę obecnie przeglądanego
  katalogu na ścieżkę np. do:
  - katalog domowy użytkownika
  - katalog /etc
  - katalog /tmp
  - katalog ~/Download
  - katalog ~/Documents
  - katalog główny napędu :`/` .
- **New Feature:** Podgląd zawartości pliku wewnątrz panelu. Np. pliku tekstowego lub grafiki. Ew. pliku binarnego za pomocą narzędzia
  `xxd`.
- **New Feature:** Wyświetlenie konsoli na wybranej ścieżce. Jako pełne okno zewnętrznej aplikacji czy raczej wbudowana kontrolka w główne
  okno aplikacji?
- **New Feature:** Dodać przycisk z rozwijalną listą, który wyświetli ścieżki z listy katalogów dodanych do "Ulubionych".

### Operacje na Plikach i Katalogach (File & Directory Operations)

- **New Feature:** Dodać funkcjonalność naciśnięcia skrótu klawiszowego `Ctrl + /` które zmienia ścieżkę katalogu przeglądanego na katalog
  główny w przeglądanym napędzie.
- **New Feature:** Masowa zmiana nazwy plików/katalogów wg wzorca.
- **New Feature:** Tworzenie, modyfikacja dowiązań symbolicznych.
- **New Feature:** Wyświetlanie rozmiarów katalogów wraz z ich rekurencyjną zawartością. Sugerowana aktywacja za pomocą skrótu klawiszowego
  `Ctrl + SPACEBAR`.
- **New Feature:** Tworzenie i weryfikacja sum kontrolnych dla wybranych plików.
- **New Feature:** Większość operacji, które potrzebują czasu na zakończenie wykonywania powinna mieć możliwość bycia dodanym do Kolejki (
  `F2` Queue).
- **New Feature:** Wyszukiwanie plików powinno być możliwe w oknie dialogowym zamiast w "text field" w oknie głównym. Wyniki wyszukiwania
  powinny mieć możliwość być wyświetlone jako dodatkowa zakładka w panelu przeglądania plików.

### System i Uprawnienia (System & Permissions)

- **New Feature:** Pokazywanie ilości wolnego miejsca.
- **New Feature:** Uruchomienie aplikacji w trybie `root`.
- **New Feature:** Wykonanie pojedynczej akcji z uprawnieniami `root`. Można by to zaimplementować jako zaznaczaną opcje w oknie dialogowym.
- **New Feature:** Manager-a do montowania napędów (np. USB, DVD, dysk itp.). Przemyśleć to wraz z opcją do zapamiętywania ścieżek do
  ulubionych napędów.

### Sieć (Network)

- **New Feature:** Obsługa FTP, NFS, SMB.
- **New Feature:** SFTP (SSH-FileTransfer).

### Inne (Other)

- **New Feature:** Aplikacja powinna logować działania swojej pracy w formie listy: co robi z ew. z jakimi parametrami.
- **New Feature:** Menu użytkownika do przypinania makr lub poleceń, które mają być wykonane. Np. seria poleceń w konsoli na danym katalogu
  lub pliku.
- **Fix:** W trybie "tree" naciśnięcie klawiszy Home/End powinno przestawiać kursor tylko na początek/koniec listy plików w obecnie
  rozwiniętym katalogu. Obecnie klawisze ustawiają kursor na pierwszy/ostatni wiersz całej listy wyświetlonych wierszy na liście. Dopiero
  ponowne naciśnięcie klawisza Home/End powinno ustawić kursor na pierwszy lub ostatni element katalogu nadrzędnego.

## Zaimplementowane (Implemented)

- **New Feature:** Dodać button jako rozwijalną listę, z której można wybrać napęd i ewentualne zamontowane urządzenia. Ta rozwijalna lista powinna znajdować się nad panelem do przeglądania plików.
- **New Feature:** Dodano nowe kolumny do widoków plików (flat i tree):
    - **Uprawnienia Pliku:** Wyświetla uprawnienia w formie symbolicznej (rwx) lub numerycznej (755), z możliwością wyboru w ustawieniach.
  - **Właściciel (UID):** Wyświetla nazwę użytkownika będącego właściciela pliku/katalogu.
    - **Grupa (GID):** Wyświetla nazwę grupy będącej właścicielem pliku/katalogu.
    Ustawienia widoczności kolumn i trybu wyświetlania uprawnień są zapisywane.
    Dodano tłumaczenia dla nowych elementów interfejsu użytkownika.
- **New Feature:** Funkcjonalność przenoszenia plików i folderów do kosza systemowego (Trash/Recycle Bin).
    - Zmodyfikowano okno dialogowe usuwania (`DeleteDialog`) o opcję "Przenieś do Kosza (jeśli dostępne)".
    - Zaktualizowano `FileManager` do używania biblioteki `send2trash` do przenoszenia do kosza lub permanentnego usuwania.
    - Dodano obsługę błędów i testy jednostkowe dla nowej funkcjonalności.
- **Refactoring:** Zawartość okna "About" jest teraz ładowana z plików HTML (`docs/about/about.html`, `docs/about/about_pl.html`).
  - Zaimplementowano dynamiczne ładowanie treści w zależności od wybranego języka.
  - Zastąpiono statyczne etykiety w `AboutDialog` komponentem `QTextBrowser` do wyświetlania sformatowanego tekstu i linków.
  - Usunięto nieużywane klucze tłumaczeń z plików `en_US.json` i `pl_PL.json`.
- **New Feature:** Dodano możliwość ręcznego wyboru koloru tekstu oraz stylu czcionki (pogrubienie, kursywa) dla zaznaczenia pliku za pomocą
  klawisza "Insert".
  - Ustawienia te są konfigurowalne w oknie "Ustawienia" i są zapisywane.
  - Zapewniono automatyczne przejście do następnego wiersza po naciśnięciu klawisza "Insert".
  - Usunięto możliwość ustawiania koloru tła dla zaznaczenia "Insert", aby zachować spójność wizualną z motywami aplikacji.

## Testing Writestyle code assistant 
{collapsible="true" default-state="expanded"}

{style="warning"}
> some warning message
