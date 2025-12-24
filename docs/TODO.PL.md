# Lista zadań (TODO)

## Główne funkcje do zaimplementowania

- [ ] **Menu kontekstowe**: Dodać menu kontekstowe (prawy przycisk myszy) dla plików i folderów z podstawowymi operacjami (Kopiuj, Przenieś, Usuń, Właściwości itp.).

- [ ] **Pasek postępu dla operacji**: Zaimplementować wizualny wskaźnik postępu (np. w pasku stanu lub w osobnym oknie) dla długotrwałych operacji, takich jak:
    - Kopiowanie
    - Przenoszenie
    - Usuwanie
    - Archiwizacja i de-archiwizacja
    - Synchronizacja katalogów

- [ ] **Wielowątkowość operacji**: Przenieść długotrwałe operacje na plikach do osobnych wątków, aby nie blokowały interfejsu użytkownika.

- [ ] **Kolejkowanie zadań**: Stworzyć system kolejkowania operacji, aby można było zlecić kilka zadań jedno po drugim (np. kopiowanie kilku różnych plików w różne miejsca).

- [ ] **Architektura pluginów**: Zaprojektować i zaimplementować system wtyczek, który w przyszłości pozwoli na łatwe dodawanie obsługi nowych formatów archiwów (np. tworzenie RAR) i innych funkcjonalności.

- [ ] **New debug feature**: Zaprojektować i wdrożyć możliwość tworzenia logów wykonywanych czynności przez aplikację. Tak, aby posiadając taki log, można było odtworzyć wykonywane przez aplikacje akcje. Mogłoby to być przydatne przy analizie potencjalnych błędów w trakcie działania aplikacji po stronie użytkownika końcowego. 