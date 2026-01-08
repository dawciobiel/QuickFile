# Architektura Systemu Skrótów Klawiszowych

## Filozofia Projektu: Pragmatyzm i Niezawodność

System skrótów w QuickFile opiera się na pragmatycznym, dwukomponentowym podejściu, którego celem jest zapewnienie **niezawodności i spójności działania**, nawet w obliczu skomplikowanego przepływu zdarzeń w bibliotece Qt.

W aplikacji istnieją dwa systemy, które współpracują ze sobą, aby obsłużyć skróty:

1.  **System `QAction` (`MenuPanel`)**: Działa jako **"źródło prawdy"** dla wszystkich akcji w aplikacji. Definiuje, *co* dana akcja robi (np. otwiera nową kartę) i jaki jest jej domyślny skrót, który jest widoczny w menu. Jest to standardowy mechanizm Qt.

2.  **System `KeyboardEventManager`**: Działa jako **"egzekutor"** (enforcer). Jest to globalny filtr zdarzeń, który przechwytuje wciśnięcia klawiszy na najwyższym poziomie aplikacji. Jego zadaniem jest **zagwarantowanie**, że kluczowe skróty zadziałają zawsze, niezależnie od tego, który widget ma fokus i czy próbuje on "zjeść" zdarzenie klawiatury (co jest częstym problemem w przypadku `QTableView`).

Taki dualizm jest celowy. `MenuPanel` zapewnia spójność z interfejsem graficznym (menu, paski narzędzi), a `KeyboardEventManager` zapewnia niezawodność działania skrótów w każdej sytuacji.

## Opis Komponentów

### 1. `panels/menu_panel.py`

*   **Rola**: Centralne miejsce definiowania wszystkich akcji aplikacji.
*   **Logika**:
    *   W słowniku `action_definitions` każda akcja (np. `view.new_tab`) jest mapowana na metodę w `ApplicationLogicHandler`.
    *   Tworzy instancje `QAction` dla każdej zdefiniowanej akcji.
    *   Pobiera skonfigurowany przez użytkownika skrót z `ShortcutsManager` i ustawia go w `QAction`, dzięki czemu jest on widoczny w menu.
    *   Dodaje każdą akcję do `MainWindow` (`self.main_window.addAction(action)`), co jest dobrą praktyką, choć w naszym systemie nie jest to główny mechanizm wyzwalający.

### 2. `app/shortcuts_manager.py`

*   **Rola**: Zarządzanie konfiguracją skrótów.
*   **Logika**:
    * Ładuje domyślny schemat skrótów z pliku `config/shortcuts/default.json`.
    * Odczytuje i zapisuje skróty użytkownika do pliku `quickfile_shortcuts.json` w katalogu konfiguracyjnym użytkownika.
    * Łączy domyślne skróty z ustawieniami użytkownika.
    *   Udostępnia metodę `get_shortcut_string(shortcut_id)`, z której korzysta `MenuPanel`.

### 3. `app/keyboard_event_handler.py`

*   **Rola**: Główny i najważniejszy komponent systemu skrótów. Działa jako globalny filtr zdarzeń na poziomie całej aplikacji.
*   **Logika**:
    * Posiada słownik `action_handlers`, który mapuje nazwy akcji (np. `view.new_tab`) na metody w `ApplicationLogicHandler`.
    * Korzysta z `ShortcutsManager` do pobrania aktualnych skrótów dla każdej akcji.
    *   Przechwytuje zdarzenia `KeyPress` jako pierwszy.
    * Dynamicznie sprawdza, czy wciśnięta kombinacja klawiszy pasuje do któregoś ze skonfigurowanych skrótów.
    * Jeśli kombinacja pasuje, wykonuje przypisaną akcję i **zatrzymuje dalsze przetwarzanie zdarzenia** (zwraca `True`).
    * Jeśli kombinacja nie pasuje, **przekazuje zdarzenie dalej** (zwraca `False`).
    * Obsługuje również zdarzenie `ShortcutOverride`, aby zapobiec konfliktom.
    * Posiada specjalną obsługę klawiatury numerycznej (Keypad), aby zapewnić poprawne działanie skrótów takich jak `+` czy `-`.

## Przepływ Zdarzenia (Przykład: `Ctrl+T`)

1.  Użytkownik naciska `Ctrl+T`.
2.  `KeyboardEventManager`, jako globalny filtr, otrzymuje zdarzenie `KeyPress` jako pierwszy.
3. Pobiera kod klawisza i modyfikatory ze zdarzenia.
4. Iteruje po skonfigurowanych skrótach w `ShortcutsManager`.
5. Znajduje, że `Ctrl+T` jest przypisane do akcji `view.new_tab`.
6. Pobiera handler dla `view.new_tab` ze słownika `action_handlers`.
7. Wywołuje przypisaną metodę: `self.application_logic_handler.new_tab()`.
8. Zwraca `True`, co "konsumuje" zdarzenie.

## Jak Dodać Nowy Skrót Klawiszowy?

Aby dodać nową, globalną akcję (np. "Przełącz tryb widoku" pod skrótem `Ctrl+M`):

1.  **Zdefiniuj logikę**: Dodaj nową metodę w `app/application_logic_handler.py`, np. `toggle_view_mode()`.
2.  **Zdefiniuj akcję w `MenuPanel`**: W `panels/menu_panel.py`, w słowniku `action_definitions`, dodaj nowy wpis:
    ```python
    "view.toggle_mode": (translation_manager.translate("MenuPanel", "Toggle View Mode"), self.app_logic_handler.toggle_view_mode),
    ```
3. **Zarejestruj handler w `KeyboardEventManager`**: W `app/keyboard_event_handler.py`, w słowniku `action_handlers`, dodaj mapowanie:
    ```python
    "view.toggle_mode": self.application_logic_handler.toggle_view_mode,
    ```
4. **Dodaj domyślną konfigurację**: W pliku `config/shortcuts/default.json`, dodaj wpis dla nowej akcji:
    ```json
    "view.toggle_mode": "Ctrl+M"
    ```
5.  **(Opcjonalnie)** Dodaj nową akcję do któregoś z menu w metodach `_build_menus()` w `MenuPanel`.

Dzięki temu nowy skrót będzie działał niezawodnie, będzie widoczny w menu i konfigurowalny przez użytkownika.
