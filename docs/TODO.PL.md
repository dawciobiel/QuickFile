# Lista zadań (TODO)

## Główne funkcje do zaimplementowania

- [ ] **Kolejkowanie zadań**: Stworzyć system kolejkowania operacji, aby można było zlecić kilka zadań jedno po drugim (np. kopiowanie kilku różnych plików w różne miejsca).

- [ ] **Architektura pluginów**: Zaprojektować i zaimplementować system wtyczek, który w przyszłości pozwoli na łatwe dodawanie obsługi nowych formatów archiwów (np. tworzenie RAR) i innych funkcjonalności.

- [ ] **New debug feature**: Zaprojektować i wdrożyć możliwość tworzenia logów wykonywanych czynności przez aplikację. Tak, aby posiadając taki log, można było odtworzyć wykonywane przez aplikacje akcje. Mogłoby to być przydatne przy analizie potencjalnych błędów w trakcie działania aplikacji po stronie użytkownika końcowego. 

- [ ] **Ulepszenie paska postępu**:
    - Zapewnienie płynnych aktualizacji dla wszystkich operacji.
    - Pełna obsługa błędów z informacją zwrotną dla użytkownika.
    - [x] Implementacja mechanizmu pauzy, wznowienia i anulowania zadań.

- [ ] **Rozszerzenie wielowątkowości**: Zastosowanie mechanizmu zadań w tle dla operacji:
    - Synchronizacji katalogów
    - Archiwizacji i dearchiwizacji

## Zrobione / Zaimplementowane częściowo

- [x] **Menu kontekstowe**: Dodano podstawowe menu kontekstowe (prawy przycisk myszy) dla plików i folderów.
- [x] **Wielowątkowość i pasek postępu (częściowo)**: Przeniesiono operacje kopiowania, przenoszenia i usuwania do osobnych wątków, aby nie blokowały interfejsu. Dodano wizualny wskaźnik postępu dla tych operacji.
