# TODO List

# Important notes

- Ważne: Każdą funkcjonalność rozwiązywać na własnym dla niej branch-u.

## TODO List

- **Refactoring:** Zawartość okna "About" powinna być czytana z pliku. Obecnie treść jest wpisana na sztywno w kodzie aplikacji i dodatkowo tłumaczona za pomocą wersji językowych. Zastanowić się jak to rozwiązać, bo treść tego okna powinna być tłumaczona na różne języki. Jednak jest to tylko tłumaczenie, a nie zawartość okna, jeżeli chodzi o np. odpowiednie sformatowanie i ułożenie wyświetlanego tekstu. Trzeba to przemyśleć. Być może użyć dodatkowo Qt Designer'a.

- **New Feature:** Dodać button jako rozwijalną listę, z której można wybrać napęd i ewentualne zamontowane urządzenia. Ta rozwijalna lista powinna znajdować się nad panelem do przeglądania plików.

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
