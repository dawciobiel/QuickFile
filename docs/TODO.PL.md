# TODO List

# Important notes

- **Important**: Każdą funkcjonalność rozwiązywać na własnym dla niej branch-u.

## Zaimplementowane

- **New Feature:** Dodać button jako rozwijalną listę, z której można wybrać napęd i ewentualne zamontowane urządzenia. Ta rozwijalna lista powinna znajdować się nad panelem do przeglądania plików.
- **New Feature:** Dodano nowe kolumny do widoków plików (flat i tree):
    - **Uprawnienia Pliku:** Wyświetla uprawnienia w formie symbolicznej (rwx) lub numerycznej (755), z możliwością wyboru w ustawieniach.
    - **Właściciel (UID):** Wyświetla nazwę użytkownika będącego właścicieela pliku/katalogu.
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

## TODO List

- **Fix:** W trybie "tree" naciśnięcie klawiszy Home/End powinno przestawiać kursor tylko na początek/koniec listy plików w obecnie
  rozwiniętym katalogu. Obecnie klawisze ustawiają kursor na pierwszy/ostatni wiersz całej listy wyświetlonych wierszy na liście. Dopiero
  ponowne naciśnięcie klawisza Home/End powinno ustawić kursor na pierwszy lub ostatni element katalogu nadrzędnego.

- **New Feature:** Dodać funkcjonalność naciśnięcia skrótu klawiszowego `Ctrl + /` które zmienia ścieżkę katalogu przeglądanego na katalog
  główny w przeglądanym napędzie.

- **New Feature:** Manager-a do montowania napędów (np. USB, DVD, dysk itp.). Przemyśleć to wraz z opcją do zapamiętywania ścieżek do ulubionych napędów. 

- **New Feature:** Dodać przycisk z rozwijalną listą, który wyświetli ścieżki z listy katalogów dodanych do "Ulubionych".

- Kontrolka od przeglądania listowania plików/folderów musi być umieszczona w kontrolce "Tab Widget". W ten sposób będzie można mieć jednocześnie otwarte zakładki z różnymi katalogami bierzącymi.

- **New Feature:** Stworzyć style dla aplikacji. Tak, aby można było w łatwy sposób zmienić kolorystykę całej aplikacji.

- **New Feature:** Dodać możliwość definiowania kolorowania czcionki dla plików/folderów wg wzorca to jest według ich nazwy pliku lub rozszerzenia. Ew. można spróbować zmieniać nie kolor czcionki co kolor tła w komórce tabeli.

- **New Feature:** Dodać możliwość ręcznego wyboru koloru zaznaczania pliku za pomocą klawisza "Insert". Wydaje mi się, że tutaj trzeba zmieniać kolor czcionki zaznaczonego pliku na kolor wybrany przez użytkownika. 

- **New Feature:** Dodać kolejne funkcje aplikacji (tworzenie sum kontrolnych dla wybranych plików, sprawdzanie sum kontrolnych, obsługę FTP, NFS, SMB).

- **New Feature:** Dodać możliwość zapamiętania domyślnej lokalizacji paneli do przeglądania plików. Trzeba się zastanowić jaki rodzaj GUI do tej funkcji stworzyć.

- **New Feature:** Panel do przeglądania zawartości plików powinien być osadzony wewnątrz komponentu "Multi Tabs".

- **New Feature:** Wyszukiwanie plików powinno być możliwe w oknie dialogowym zamiast w "text field" w oknie głównym. Wyniki wyszukiwania powinny mieć możliwość być wyświetlone jako dodatkowa zakładka w panelu przeglądania plików.

- **New Feature:** Dodać buttons przy text-filed ze ścieżką wskazującą na aktualny przeglądany katalog. Musi działać zależnie od systemu, na którym uruchomiona jest aplikacja (linux, Windows, MacOS). Buttony te powinny być konfigurowalne i umożliwiać zmianę obecnie przeglądanego katalogu na ścieżkę np. do:
    - katalog domowy użytkownika
    - katalog /etc
    - katalog /tmp
    - katalog ~/Download
    - katalog ~/Documents
    - katalog główny napędu :`/` .


## Testing Writestyle code assistant 
{collapsible="true" default-state="expanded"}

{style="warning"}
> some warning message
