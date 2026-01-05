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
    *   Odczytuje i zapisuje skróty do pliku `config/shortcuts.json`.
    *   Udostępnia metodę `get_shortcut_string(shortcut_id)`, z której korzysta `MenuPanel`.

### 3. `app/keyboard_event_handler.py`

*   **Rola**: Główny i najważniejszy komponent systemu skrótów. Działa jako globalny filtr zdarzeń na poziomie całej aplikacji.
*   **Logika**:
    *   Posiada słownik `key_actions`, który mapuje konkretne kombinacje klawiszy (`(Qt.Key, Qt.Modifier)`) na te same metody w `ApplicationLogicHandler`, co `MenuPanel`. Jest to **celowa redundancja**, która gwarantuje działanie.
    *   Przechwytuje zdarzenia `KeyPress` jako pierwszy.
    *   Jeśli kombinacja klawiszy pasuje do wpisu w `key_actions`, wykonuje akcję i **zatrzymuje dalsze przetwarzanie zdarzenia** (zwraca `True`), uniemożliwiając widgetom (np. tabeli) jego "zjedzenie".
    *   Jeśli kombinacja nie pasuje, **przekazuje zdarzenie dalej** (zwraca `False`), pozwalając na normalne wpisywanie tekstu lub inne domyślne zachowania.
    *   Obsługuje również zdarzenie `ShortcutOverride`, aby zapobiec konfliktom z klawiszami takimi jak `AltGr` na klawiaturach międzynarodowych.

## Przepływ Zdarzenia (Przykład: `Ctrl+T`)

1.  Użytkownik naciska `Ctrl+T`.
2.  `KeyboardEventManager`, jako globalny filtr, otrzymuje zdarzenie `KeyPress` jako pierwszy.
3.  Sprawdza swój słownik `key_actions`.
4.  Znajduje wpis dla `(Qt.Key.Key_T, Qt.KeyboardModifier.ControlModifier)`.
5.  Wywołuje przypisaną metodę: `self.application_logic_handler.new_tab()`.
6.  Zwraca `True`, co "konsumuje" zdarzenie.
7.  Widget, który miał fokus (np. tabela), nigdy nie otrzymuje tego zdarzenia. System `QAction` również nie jest aktywowany, ponieważ zdarzenie zostało obsłużone wcześniej.

## Jak Dodać Nowy Skrót Klawiszowy?

Aby dodać nową, globalną akcję (np. "Przełącz tryb widoku" pod skrótem `Ctrl+M`):

1.  **Zdefiniuj logikę**: Dodaj nową metodę w `app/application_logic_handler.py`, np. `toggle_view_mode()`.
2.  **Zdefiniuj akcję w `MenuPanel`**: W `panels/menu_panel.py`, w słowniku `action_definitions`, dodaj nowy wpis:
    ```python
    "view.toggle_mode": (translation_manager.translate("MenuPanel", "Toggle View Mode"), self.app_logic_handler.toggle_view_mode),
    ```
3.  **Dodaj skrót do `KeyboardEventManager`**: W `app/keyboard_event_handler.py`, w słowniku `key_actions`, dodaj nowy wpis:
    ```python
    (Qt.Key.Key_M, Qt.KeyboardModifier.ControlModifier): self.application_logic_handler.toggle_view_mode,
    ```
4.  **Dodaj domyślną konfigurację**: W pliku `config/shortcuts.json`, dodaj wpis dla nowej akcji:
    ```json
    {
      "id": "view.toggle_mode",
      "shortcut": "Ctrl+M"
    }
    ```
5.  **(Opcjonalnie)** Dodaj nową akcję do któregoś z menu w metodach `_build_menus()` w `MenuPanel`.

Dzięki temu nowy skrót będzie działał niezawodnie, będzie widoczny w menu i konfigurowalny przez użytkownika.
