# Lista zadań (TODO)

## Główne funkcje do zaimplementowania

- [ ] **Architektura pluginów**: Zaprojektować i zaimplementować system wtyczek, który w przyszłości pozwoli na łatwe dodawanie obsługi nowych formatów archiwów (np. tworzenie RAR) i innych funkcjonalności.

- [ ] **Odtwarzanie logów akcji**: Stworzyć narzędzie lub tryb w aplikacji, który potrafi odtworzyć zanonimizowany plik `actions.log`, symulując działania użytkownika w celu debugowania.

- [ ] **Zarządzanie kolejką zadań**: Dodać możliwość czyszczenia listy "Queue" z zadań, które mają status "Ukończony" lub "Błąd".

- [ ] **Dynamiczne odświeżanie widoku plików**: Poprawić odświeżanie listy plików po zakończeniu operacji w tle. Zadanie w kolejce powinno emitować sygnał po każdej modyfikacji (np. usunięciu pliku), a `FolderBrowser` powinien go obsłużyć, aby zapewnić natychmiastową informację zwrotną w UI.

- [ ] **Feature**: Możliwość ustalania maksymalnej prędkości podczas procesu kopiowaniu plików. To powinien być jakiś suwak lub spinner w oknie dialogowym aktualnie wykonywanego procesu kopiowania. A swoją drogą nie wiem, jak zaimplementować ogranicznik prędkości kopiowanych plików. 

- [ ] **Feature**: Pod Windows (i jego systemem plików) czasami może być problem ze zbyt długimi nazwami plików lub zbyt długą ścieżką. Przyjrzeć się temu problemowi i dodać odpowiednią funkcjonalność dla "zachowania nazwy pliku".

## Zrobione / Zaimplementowane częściowo

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
