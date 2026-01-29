# Plan Redesignu Architektury Pluginów

## Cel

Zaprojektowanie i implementacja nowej, wielowątkowej architektury dla pluginów uruchamianych w izolowanych procesach (
sandbox). Celem jest zapewnienie pełnej responsywności pluginu na sygnały sterujące (anulowanie, pauza) nawet podczas
intensywnych operacji I/O lub CPU, oraz uproszczenie tworzenia nowych pluginów poprzez wprowadzenie solidnych klas
abstrakcyjnych. Architektura musi być elastyczna, aby wspierać różnorodne typy pluginów i niestandardowe protokoły
komunikacji.

## Główne Założenia

### 1. Architektura Procesu Pluginu

Każdy plugin uruchamiany w trybie `sandboxed` będzie działał w oparciu o co najmniej dwa wątki:

* **Wątek Główny (IPC Thread):**
    * Odpowiedzialny wyłącznie za komunikację z procesem głównym aplikacji (QuickFile) poprzez potok (Pipe).
    * Nasłuchuje na komunikaty przychodzące (np. `EXECUTE_TASK`, `CANCEL_TASK`, `INPUT_RESPONSE`).
    * Zarządza cyklem życia wątku roboczego.
    * Przekazuje statusy (anulowanie, pauza) do kontekstu zadania w sposób bezpieczny wątkowo.
    * Nigdy nie wykonuje blokujących operacji biznesowych.

* **Wątek Roboczy (Worker Thread):**
    * Uruchamiany na żądanie wykonania konkretnej metody (np. `split_file`, `search`).
    * Wykonuje właściwą logikę biznesową pluginu.
    * Regularnie sprawdza stan `TaskContext` (czy anulowano/wstrzymano).
    * Raportuje postęp oraz **niestandardowe zdarzenia** do Wątku Głównego.

### 2. Klasy Abstrakcyjne i Interfejsy

Aby ułatwić tworzenie pluginów i wymusić poprawną architekturę, wprowadzimy zestaw klas bazowych:

* **`PluginBase` (w `plugin.py`)**:
    * Klasa, po której dziedziczą wszystkie pluginy.
    * Definiuje metadane i punkty wejścia (menu actions).
    * **Fabryka Zadań:** Zamiast implementować logikę, zwraca instancje zadań (np.
      `get_split_task(...) -> AbstractTask`).
    * **Handlery Zdarzeń:** Definiuje metody obsługi niestandardowych zdarzeń po stronie UI (np. `on_item_found`).

* **`AbstractTask` (w `tasks.py`)**:
    * Klasa bazowa dla konkretnych zadań realizowanych przez plugin.
    * Twórca pluginu implementuje metodę `run(context)`.
    * Udostępnia metody pomocnicze:
        * `emit_progress(value)`
        * `emit_event(event_name: str, payload: dict)`: Do wysyłania generycznych zdarzeń z dowolnymi danymi.
        * `request_user_input(event_name: str, payload: dict)`: Do synchronicznego żądania decyzji użytkownika.

* **`PluginWorker` (Framework)**:
    * Zarządca procesu pluginu, dostarczany przez QuickFile. Obsługuje pętlę IPC i uruchamia `AbstractTask` w wątku.

### 3. Protokół Komunikacji (IPC)

Ujednolicony protokół oparty na generycznych komunikatach:

* **Do Pluginu:**
    * `EXECUTE_TASK`: Rozpocznij zadanie (nazwa metody, argumenty).
    * `CONTROL_TASK`: Zmień stan zadania (np. `{"action": "cancel"}`).
    * `EVENT_RESPONSE`: Odpowiedź użytkownika na żądanie (np. `{"event_name": "password_provided", "payload": "..."}`).

* **Od Pluginu:**
    * `TASK_STARTED`, `TASK_FINISHED`, `TASK_FAILED`, `TASK_CANCELLED`.
    * `TASK_PROGRESS`: Standardowy postęp.
    * `DATA_EVENT`: Generyczne zdarzenie z pluginu.
        * `event_name`: Nazwa zdarzenia (np. `"item_found"`, `"password_required"`).
        * `payload`: Dowolny obiekt JSON z danymi.
        * `requires_response`: Flaga informująca, czy plugin oczekuje na odpowiedź (`EVENT_RESPONSE`).

## Etapy Implementacji

1. **Projekt API:** Szczegółowa definicja `PluginBase` i `AbstractTask` z uwzględnieniem `emit_event`.
2. **Implementacja `PluginWorker`:** Stworzenie generycznego zarządcy procesu pluginu.
3. **Refaktoryzacja `SandboxedPluginWrapper`:** Obsługa `DATA_EVENT` i przekierowywanie ich do handlerów w `PluginBase`.
4. **Migracja Pluginu Wzorcowego:** Przepisanie `file_splitter` (prosty) oraz `search_standard` (wymaga `DATA_EVENT`)
   jako PoC.
5. **Testy:** Weryfikacja anulowania, pauzowania oraz komunikacji dwukierunkowej.
6. **Migracja Pozostałych Pluginów.**
