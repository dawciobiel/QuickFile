# Lista zadań (TODO)

## Główne funkcje do zaimplementowania

- [ ] **Feature: Dzielenie plików (Plugin)**:
    - Dokończenie implementacji pluginu `file_splitter`.
    - Stworzenie UI (`split_dialog.ui`) z opcjami:
        - Wybór katalogu docelowego.
        - Wybór predefiniowanego rozmiaru części (1.44 MB, 650 MB, 700 MB, 4.5 GB).
        - Możliwość podania własnego rozmiaru.
        - Opcja generowania pliku z sumami kontrolnymi (CRC32).
    - Implementacja logiki dzielenia plików w tle z obsługą postępu.

- [ ] **UI/UX: Ulepszenie przycisków w oknach operacji**:
    - Przycisk "Pauza" powinien dynamicznie zmieniać swój tekst (lub ikonę) na "Wznów" po wciśnięciu.
    - Rozważyć zastąpienie tekstów na przyciskach ("Pauza", "Anuluj") uniwersalnymi ikonami, aby poprawić spójność interfejsu. Należy zadbać o odpowiedni rozmiar i czytelność przycisków.

- [ ] **Feature: System aktualizacji**:
    - Zaprojektowanie odpowiedniego systemu pobierania i instalowania aktualizacji dla aplikacji, motywów, zasobów, tłumaczeń i pluginów.
    - System aktualizacji powinien wspierać wersję oficjalną aplikacji.
    - Przydałby się również system do aktualizacji wersji beta (przewidziana jako wersja binarna, bez kodów źródłowych).

- [ ] **Zabezpieczenie kodu źródłowego**:
    - Zabezpieczenie kodu źródłowego aplikacji przed kradzieżą.
    - Dodanie licencji, ukrycie kodu źródłowego co najmniej w wersji beta.

- [ ] **Refactor, Chore, Cleaning**: Być może część starych branchy, które nie są już potrzebne i nie będą — należy skasować.

- [ ] **Feature**: Możliwość ustalania maksymalnej prędkości podczas procesu kopiowaniu plików. To powinien być jakiś suwak lub spinner w oknie dialogowym aktualnie wykonywanego procesu kopiowania. A swoją drogą nie wiem, jak zaimplementować ogranicznik prędkości kopiowanych plików. 

- [ ] **Feature**: Pod Windows (i jego systemem plików) czasami może być problem ze zbyt długimi nazwami plików lub zbyt długą ścieżką. Przyjrzeć się temu problemowi i dodać odpowiednią funkcjonalność dla "zachowania nazwy pliku".

## Zrobione / Zaimplementowane częściowo

- [x] **Feature: System powiadomień**:
    - Zaimplementowano system powiadomień wizualnych (dymki/toasty) dla zadań w tle.
    - Dodano powiadomienia dźwiękowe dla statusów zadań (sukces, błąd, anulowanie) oraz dla blokujących okien dialogowych z błędami.
    - Dodano możliwość włączenia/wyłączenia powiadomień dźwiękowych w ustawieniach.
    - **Do zrobienia w przyszłości**:
        - [ ] Integracja z natywnym systemem powiadomień systemu operacyjnego (jako opcja).

- [x] **Testowanie (E2E)**:
    - Stworzono solidny fundament pod testy End-to-End przy użyciu `pytest-qt`.
    - Zaimplementowano testy dla kluczowych przepływów użytkownika:
        - Wyszukiwanie plików (`test_search_flow.py`)
        - Kopiowanie (`test_copy_flow.py`)
        - Przenoszenie (`test_move_flow.py`)
        - Usuwanie (`test_delete_flow.py`)
        - Zmiana nazwy (`test_rename_flow.py`)
        - Tworzenie nowego katalogu (`test_new_folder_flow.py`)
        - Synchronizacja katalogów (`test_sync_flow.py`)
    - Naprawiono błędy w środowisku testowym CI (GitHub Actions) związane z zależnościami i logiką testów.

- [x] **Architektura pluginów (Menu)**:
    - Stworzono nowy interfejs `MenuActionPlugin`, który pozwala pluginom na dynamiczne dodawanie własnych akcji do menu głównego aplikacji.
    - Zintegrowano nowy mechanizm z `PluginManager` i `MenuPanel`.
    - Stworzono szkielet pluginu `file_splitter` jako pierwszą implementację tego mechanizmu.

- [x] **Feature: Wbudowany edytor kodu (Plugin)**:
    - Stworzono wtyczkę `standard_editor` (F4) z podstawową funkcjonalnością.
    - **Zaimplementowano**:
        - Kolorowanie składni dla wielu języków (Pygments), zintegrowane z motywami aplikacji.
        - Numerację linii.
        - Pasek narzędzi z podstawowymi akcjami (Zapisz, Cofnij/Ponów, Wytnij/Kopiuj/Wklej).
        - Podstawowe wyszukiwanie tekstu (`Ctrl+F`) i znajdowanie następnego (`F3`).
    - **Do zrobienia w przyszłości**:
        - [ ] Funkcja "Zamień" (Replace).
        - [ ] Funkcja "Zapisz jako..." (Save as...).
        - [ ] Bardziej zaawansowany panel wyszukiwania.
        - [ ] Wyświetlanie informacji o kodowaniu i możliwość jego zmiany.

- [x] **Feature: Zaawansowany wbudowany podgląd plików (F3)**:
    - Znacząco rozbudowano plugin `standard_viewer`, dodając obsługę:
        - **Obrazów**: Wyświetlanie plików graficznych z automatycznym skalowaniem.
        - **Markdown**: Renderowanie sformatowanego tekstu z plików `.md`.
        - **Kodu Źródłowego**: Kolorowanie składni dla wielu języków programowania przy użyciu `Pygments`.
    - Zaimplementowano dynamiczne dopasowanie tła podglądu kodu do motywu aplikacji (jasny/ciemny).
    - Dodano możliwość przełączania między widokiem sformatowanym a surowym tekstem.
    - Zintegrowano podgląd z oknem "Właściwości" i poprawiono błędy związane z fokusem okna.

- [x] **Refactor: System skrótów klawiszowych**:
    - Przeprowadzono gruntowną refaktoryzację systemu skrótów.
    - Usunięto "sztywno" zakodowane skróty, przenosząc je do plików konfiguracyjnych `.json` w `config/shortcuts/`.
    - Stworzono fundament pod obsługę wielu profili skrótów (np. `default.json`, `explorer_like.json`).
    - `KeyboardEventManager` został przepisany, aby dynamicznie obsługiwać skróty z aktywnego profilu.

- [x] **Feature: Budowanie paczek instalacyjnych**:
    - Zaprojektowano i wykonano skrypt/ów do budowy aplikacji jako paczki instalacyjnej (np. przy użyciu `PyInstaller` lub `cx_Freeze`).
    - **Cele**:
        1.  **Dystrybucja binarna**: Stworzenie binarnej, samodzielnej formy aplikacji, aby nie udostępniać kodu źródłowego.
        2.  **Uruchomienie**: Aplikacja jest w pełni uruchamialna z jednego pliku lub katalogu.
        3.  **Pluginy**: Architektura wspiera ładowanie zewnętrznych pluginów z dedykowanego katalogu (`plugins`) w folderze użytkownika lub instalacji.
        4.  **Zasoby**: Paczka zawiera wszystkie niezbędne zasoby (`resources`, `themes`, `translations`, `.ui` files).
        5.  **Konfiguracja**: Aplikacja poprawnie zarządza plikami konfiguracyjnymi zarówno w katalogu instalacji (domyślne), jak i w katalogu domowym użytkownika (spersonalizowane).
  - **Platformy**:
      - [x] **Linux**: Skrypt budujący (`scripts/packaging/build_app.py`) został stworzony i przetestowany.
      - [ ] **Windows**: Skrypt wymaga przetestowania i ewentualnych modyfikacji (np. dodanie ikony, obsługa specyficznych dla Windows
        bibliotek DLL).

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

- [x] **Odświeżanie listy napędów**: Zaimplementowano dynamiczne odświeżanie listy napędów w pasku nawigacyjnym. Lista jest aktualizowana automatycznie w momencie rozwinięcia menu (kliknięcia), co pozwala na szybki dostęp do nowo zamontowanych urządzeń (np. pendrive).
