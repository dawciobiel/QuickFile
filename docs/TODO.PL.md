# Lista zadań (TODO)

## Główne funkcje do zaimplementowania

- [ ] **Refactor, Chore, Cleaning**: Być może część starych branchy, które nie są już potrzebne i nie będą — należy skasować.

- [ ] **Ulepszenie paska narzędzi (Toolbar)**:
    - [ ] Poprawić wygląd ikon na pasku narzędzi, aby były spójne i profesjonalne.
    - [ ] Dodać w menu "Widok" opcję "Pokaż/Ukryj pasek narzędzi".

- [ ] **Refaktoryzacja modeli systemu plików**: Stworzyć abstrakcyjną klasę bazową `AbstractFileSystemModel`, która zdefiniuje wspólny interfejs dla obecnego `FlatFileSystemModel`. Pozwoli to w przyszłości na łatwe dodanie innych modeli, np. `TreeFileSystemModel` (widok drzewa), zachowując spójność API (metody `filePath`, `fileName`, `isDir`).

- [ ] **Architektura pluginów**: Zaprojektować i zaimplementować system wtyczek, który w przyszłości pozwoli na łatwe dodawanie obsługi nowych formatów archiwów (np. tworzenie RAR) i innych funkcjonalności.

- [ ] **Plugin do obsługi linków symbolicznych**: Przenieść obecną funkcjonalność tworzenia i modyfikowania linków symbolicznych do dedykowanego pluginu. Plugin powinien być dostosowany do różnych systemów operacyjnych (Linux, macOS, Windows), oferując odpowiednie opcje i interfejs dla każdego z nich.

- [ ] **Feature**: Możliwość ustalania maksymalnej prędkości podczas procesu kopiowaniu plików. To powinien być jakiś suwak lub spinner w oknie dialogowym aktualnie wykonywanego procesu kopiowania. A swoją drogą nie wiem, jak zaimplementować ogranicznik prędkości kopiowanych plików. 

- [ ] **Feature**: Pod Windows (i jego systemem plików) czasami może być problem ze zbyt długimi nazwami plików lub zbyt długą ścieżką. Przyjrzeć się temu problemowi i dodać odpowiednią funkcjonalność dla "zachowania nazwy pliku".

- [ ] **Feature improvement**: Pasek postępu w oknie dialogowym do kopiowania/przenoszenia mógłby być w dwóch kolorach. Kolor reprezentowałby odczyt i zapis danych na nośniku. 

## Zrobione / Zaimplementowane częściowo

- [x] **Zaawansowana edycja atrybutów plików (Plugin)**: Stworzono fundament pod edycję atrybutów w formie pluginu. Zaimplementowano
  pierwszy plugin (`linux_attribute_editor`) do zmiany właściciela i grupy plików na systemach POSIX.

- [x] **Odtwarzanie logów akcji**: Stworzono skrypt `scripts/replay_actions.py`, który odtwarza zanonimizowane logi akcji użytkownika w
  bezpiecznej piaskownicy (sandbox), co ułatwia debugowanie. Zintegrowano logowanie z kluczowymi operacjami.

- [x] **Wbudowany podgląd plików (F3)**: Zaimplementowano zaawansowany podgląd plików jako niezależny plugin. Obsługuje tryby Text, HEX, DEC, BIN, wybór kodowania, zawijanie wierszy i numerację linii. Dodano opcję w ustawieniach do przełączania między wbudowanym a zewnętrznym viewerem.

- [x] **Dynamiczne odświeżanie widoku plików**: Zaimplementowano fundament pod dynamiczne odświeżanie. Aplikacja jest odporna na usunięcie katalogu, w którym znajduje się użytkownik (przechodzi w górę). Dodano konfigurowalny interwał odświeżania oraz wskaźnik "spinner" na kartach, na których odbywają się operacje w tle. Naprawiono szereg błędów związanych z wieloma zadaniami i zamykaniem kart.

- [x] **Przebudowa okien dialogowych operacji**: Okna dialogowe kopiowania, przenoszenia i usuwania zostały przebudowane, aby nie blokować interfejsu. Użytkownik może teraz monitorować postęp w otwartym oknie (z opcją "Ukryj") lub od razu dodać zadanie do kolejki w tle. Pasek postępu przy usuwaniu bazuje teraz na rozmiarze plików, a nie na ich liczbie.

- [x] **Zarządzanie kolejką zadań**: Dodano możliwość czyszczenia listy "Queue" z zadań, które mają status "Ukończony" lub "Błąd", a także opcję wyczyszczenia wszystkich zakończonych zadań.

- [x] **Kolejkowanie zadań**: Stworzono system kolejkowania operacji (`TaskQueueManager`) dla kopiowania, przenoszenia, usuwania i synchronizacji. Zadania są wykonywane w tle i widoczne w dedykowanym panelu.

- [x] **Logowanie akcji użytkownika (Debug Feature)**: Zaprojektowano i wdrożono możliwość tworzenia logów wykonywanych czynności (`actions.log`) z pełną anonimizacją ścieżek w celu ochrony prywatności. Stworzono również skrypt do odtwarzania logów.

- [x] **Ulepszenie paska postępu**:
    - Zapewnienie płynnych aktualizacji dla wszystkich operacji.
    - Pełna obsługa błędów z informacją zwrotną dla użytkownika.
    - Implementacja mechanizmu pauzy, wznowienia i anulowania zadań.

- [x] **Rozszerzenie wielowątkowości**: Zastosowanie mechanizmu zadań w tle dla operacji:
    - Synchronizacji katalogów
    - Kopiowania, przenoszenia, usuwania

- [x] **Menu kontekstowe**: Dodano podstawowe menu kontekstowe (prawy przycisk myszy) dla plików i folderów.
