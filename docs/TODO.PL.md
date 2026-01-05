# Lista zadań (TODO)

## Główne funkcje do zaimplementowania

- [ ] **Feature: System powiadomień**:
    - Przemyślenie i zaprojektowanie systemu powiadomień o ukończeniu zadań w tle (np. kopiowanie, przenoszenie, archiwizacja, generowanie sum kontrolnych).
    - Należy rozważyć różne formy powiadomień:
        - Niestandardowe "baloniki" (tooltips) w rogu aplikacji.
        - Opcjonalne sygnały dźwiękowe.
        - Integracja z natywnym systemem powiadomień systemu operacyjnego (Windows, Linux).
    - System powinien być konfigurowalny w ustawieniach aplikacji.

- [ ] **Refactor, Chore, Cleaning**: Być może część starych branchy, które nie są już potrzebne i nie będą — należy skasować.

- [ ] **Feature**: Możliwość ustalania maksymalnej prędkości podczas procesu kopiowaniu plików. To powinien być jakiś suwak lub spinner w oknie dialogowym aktualnie wykonywanego procesu kopiowania. A swoją drogą nie wiem, jak zaimplementować ogranicznik prędkości kopiowanych plików. 

- [ ] **Feature**: Pod Windows (i jego systemem plików) czasami może być problem ze zbyt długimi nazwami plików lub zbyt długą ścieżką. Przyjrzeć się temu problemowi i dodać odpowiednią funkcjonalność dla "zachowania nazwy pliku".

## Zrobione / Zaimplementowane częściowo

- [x] **Feature: Budowanie paczek instalacyjnych**:
    - Zaprojektowano i wykonano skrypt/ów do budowy aplikacji jako paczki instalacyjnej (np. przy użyciu `PyInstaller` lub `cx_Freeze`).
    - **Cele**:
        1.  **Dystrybucja binarna**: Stworzenie binarnej, samodzielnej formy aplikacji, aby nie udostępniać kodu źródłowego.
        2.  **Uruchomienie**: Aplikacja jest w pełni uruchamialna z jednego pliku lub katalogu.
        3.  **Pluginy**: Architektura wspiera ładowanie zewnętrznych pluginów z dedykowanego katalogu (`plugins`) w folderze użytkownika lub instalacji.
        4.  **Zasoby**: Paczka zawiera wszystkie niezbędne zasoby (`resources`, `themes`, `translations`, `.ui` files).
        5.  **Konfiguracja**: Aplikacja poprawnie zarządza plikami konfiguracyjnymi zarówno w katalogu instalacji (domyślne), jak i w katalogu domowym użytkownika (spersonalizowane).
    - **Platformy**: Początkowo wsparcie dla systemów Linux i Windows.
    - **Skrypty**: Ewentualne skrypty pomocnicze znajdują się w dedykowanym podkatalogu wewnątrz `scripts/packaging`.

- [x] **Plugin operacji dla Windows**: Stworzono dedykowany plugin `org.quickfile.windows_operations`, który obsługuje kopiowanie,
  przenoszenie i usuwanie plików na systemie Windows, wykorzystując prefiks `\\?\` do obsługi długich ścieżek.

- [x] **Pasek nawigacyjny w panelu**: Dodano pasek małych przycisków funkcyjnych na górze każdego panelu przeglądarki plików. Przyciski:
    - `...` (Go Up): Przejdź do katalogu nadrzędnego.
    - `~` (Home): Przejdź do katalogu domowego.
    - `/` (Root): Przejdź do katalogu głównego napędu.
    - `=` (Equal): Przejdź do ścieżki z drugiego panelu.

- [x] **Ulepszenia panelu kolejki zadań (Queue)**:
    - Dodano przyciski akcji ("Pause/Resume", "Cancel", "More") bezpośrednio w wierszach aktywnych zadań.
    - Dodano kolorowanie wierszy w zależności od statusu zadania (Błąd, Pauza, Ukończone).
    - Przywrócono przyciski czyszczenia listy ("Clear Completed", "Clear Error", "Clear All").
    - Naprawiono problem ze znikającymi zadaniami i brakiem aktualizacji paska postępu.

- [x] **Refaktoryzacja operacji na plikach (Plugin)**: Przeniesiono operacje kopiowania, przenoszenia i usuwania do dedykowanego pluginu
  `org.quickfile.standard_operations`. Naprawiono szereg błędów regresji, w tym wyświetlanie zadań w panelu "Queue" i aktualizację paska
  postępu.

- [x] **Dwukolorowy pasek postępu**: Pasek postępu w oknie dialogowym kopiowania/przenoszenia jest teraz dwukolorowy, reprezentując postęp odczytu i zapisu danych.

- [x] **Uniwersalne okno tworzenia archiwum**: Zaimplementowano `CreateArchiveDialog`, który dynamicznie ładuje dostępne pluginy archiwizujące i pozwala na wybór formatu oraz konfigurację opcji.

- [x] **Plugin do obsługi linków symbolicznych**: Przeniesiono funkcjonalność tworzenia i modyfikowania linków symbolicznych do dedykowanego pluginu `org.quickfile.symlink_manager`.

- [x] **Architektura pluginów**: Zaprojektowano i zaimplementowano system wtyczek, który pozwala na łatwe dodawanie obsługi nowych formatów archiwów, widoków, edytorów atrybutów i innych funkcjonalności.

- [x] **Naprawa skrótów klawiszowych**: Naprawiono błąd, który powodował, że skróty klawiszowe (np. Ctrl+D, Ctrl+Shift+B) przestały działać po refaktoryzacji menu. Zaktualizowano `ShortcutsManager`, aby używał spójnych identyfikatorów akcji.

- [x] **Ulepszone kolorowanie plików**: Dodano obsługę kolorowania specjalnych typów plików (symlinki, hardlinki, pliki ukryte) w widoku płaskim. Zaktualizowano pliki stylów (`file_styles.json`) i logikę delegata.

- [x] **Refaktoryzacja modeli systemu plików**: Stworzono abstrakcyjną klasę bazową `AbstractFileSystemModel` oraz interfejs `ViewModePlugin`. Przeniesiono dotychczasowy widok płaski (`FlatView`) do niezależnego pluginu `org.quickfile.flat_view`. Aplikacja dynamicznie ładuje widok, co umożliwia łatwe dodanie w przyszłości widoku drzewa.

- [x] **Ulepszenie paska narzędzi (Toolbar)**: Stworzono dynamiczny pasek narzędzi, budowany na podstawie pliku konfiguracyjnego `toolbar_layout.json`. Dodano ikony SVG dla wszystkich akcji oraz opcję pokazywania/ukrywania paska w menu "Widok".

- [x] **Zaawansowana edycja atrybutów plików (Plugin)**: Stworzono fundament pod edycję atrybutów w formie pluginu. Zaimplementowano pierwszy plugin (`linux_attribute_editor`) do zmiany właściciela i grupy plików na systemach POSIX.

- [x] **Odtwarzanie logów akcji**: Stworzono skrypt `scripts/replay_actions.py`, który odtwarza zanonimizowane logi akcji użytkownika w bezpiecznej piaskownicy (sandbox), co ułatwia debugowanie. Zintegrowano logowanie z kluczowymi operacjami.

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
