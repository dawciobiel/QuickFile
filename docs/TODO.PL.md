# Lista zadań (TODO)

## Główne funkcje do zaimplementowania

- [ ] **Refactor, Chore, Cleaning**: Być może część starych branchy, które nie są już potrzebne i nie będą — należy skasować.

- [ ] **Feature**: Należałoby użyć zewnętrznego, powszechnie dostępnego edytora tekstu do podglądu plików tekstowych. I zdefiniować go jako narzędzia do podglądu (View) plików tekstowych. Można też spróbować stworzyć własne, proste narzędzie tego typu. W ten sposób dla każdego systemu będzie ono miało taki sam interfejs graficzny. 

- [ ] **Refaktoryzacja modeli systemu plików**: Stworzyć abstrakcyjną klasę bazową `AbstractFileSystemModel`, która zdefiniuje wspólny interfejs dla obecnego `FlatFileSystemModel`. Pozwoli to w przyszłości na łatwe dodanie innych modeli, np. `TreeFileSystemModel` (widok drzewa), zachowując spójność API (metody `filePath`, `fileName`, `isDir`).

- [ ] **Architektura pluginów**: Zaprojektować i zaimplementować system wtyczek, który w przyszłości pozwoli na łatwe dodawanie obsługi nowych formatów archiwów (np. tworzenie RAR) i innych funkcjonalności.

- [ ] **Plugin do obsługi linków symbolicznych**: Przenieść obecną funkcjonalność tworzenia i modyfikowania linków symbolicznych do dedykowanego pluginu. Plugin powinien być dostosowany do różnych systemów operacyjnych (Linux, macOS, Windows), oferując odpowiednie opcje i interfejs dla każdego z nich.

- [ ] **Odtwarzanie logów akcji**: Stworzyć narzędzie lub tryb w aplikacji, który potrafi odtworzyć zanonimizowany plik `actions.log`, symulując działania użytkownika w celu debugowania.

- [ ] **Dynamiczne odświeżanie widoku plików**: Poprawić odświeżanie listy plików po zakończeniu operacji w tle. Zadanie w kolejce powinno emitować sygnał po każdej modyfikacji (np. usunięciu pliku), a `FolderBrowser` powinien go obsłużyć, aby zapewnić natychmiastową informację zwrotną w UI.

- [ ] **Feature**: Możliwość ustalania maksymalnej prędkości podczas procesu kopiowaniu plików. To powinien być jakiś suwak lub spinner w oknie dialogowym aktualnie wykonywanego procesu kopiowania. A swoją drogą nie wiem, jak zaimplementować ogranicznik prędkości kopiowanych plików. 

- [ ] **Feature**: Pod Windows (i jego systemem plików) czasami może być problem ze zbyt długimi nazwami plików lub zbyt długą ścieżką. Przyjrzeć się temu problemowi i dodać odpowiednią funkcjonalność dla "zachowania nazwy pliku".

- [ ] **Feature improvement**: Pasek postępu w oknie dialogowym do kopiowania/przenoszenia mógłby być w dwóch kolorach. Kolor reprezentowałby odczyt i zapis danych na nośniku. 

- [ ] **Feature improvement**: Okno dialogowe do operacji na plikach powinno być wyświetlone. Dopiero naciśnięcie w tym oknie przycisku np. "minimize" lub ewentualnie "queue" powodowałoby ukrycie okna. Przy czym sam proces działałby w tle i byłby widoczny w zakładce "Queue". 

## Zrobione / Zaimplementowane częściowo

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
