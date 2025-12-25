# BUGS

## Nierozwiązane (Unresolved)

(Brak)

## Naprawione (Fixed)

### Operacje w tle i Kolejka Zadań (Background Operations & Task Queue)
1.  **Błąd przy anulowaniu zadania:** Aplikacja ulegała awarii z błędem `AttributeError: 'NoneType' object has no attribute 'status'` podczas anulowania operacji w tle. Błąd wynikał z wyścigu warunków między slotami `_on_task_error` i `_on_task_finished`. Naprawiono przez dodanie sprawdzenia `if self.current_task:` w `_on_task_finished`.
2.  **Brak aktualizacji postępu w UI:** Wartość w kolumnie "Progress" w panelu kolejki nie była odświeżana. Naprawiono przez stworzenie dedykowanego slotu `_on_task_progress` w `TaskQueueManager`, który aktualizuje stan obiektu `Task`.
3.  **Kopiowanie/Przenoszenie tylko jednego pliku:** Mimo zaznaczenia wielu plików (np. klawiszem `Insert`), operacje kopiowania i przenoszenia dotyczyły tylko jednego pliku. Naprawiono przez przekazanie całej listy zaznaczonych ścieżek do dialogów i zaimplementowanie metod `copy_items_batch` i `move_items_batch`.

### Interfejs i Ustawienia (UI & Settings)
4.  **Błędy `AttributeError` w Oknie Ustawień:** Seria błędów `AttributeError` uniemożliwiała otwarcie okna ustawień po refaktoryzacji UI. Błędy wynikały z niedopasowania nazw widżetów w kodzie `.py` i pliku `.ui`. Naprawiono przez przywrócenie stabilnej wersji pliku `utils/settings_dialog.py`.
5.  **Białe tło w panelu kolejki:** Wiersze w tabeli kolejki zadań miały białe tło, które nie pasowało do ciemnego motywu. Naprawiono przez dodanie odpowiednich reguł (`QTableView::item:selected:!active`) do pliku `style.qss` motywu i zapewnienie, że `ThemeManager` poprawnie wstrzykuje kolor `inactive_selection_background`.

### Wcześniejsze (Older)
6.  **Incorrect '..' Path Navigation:** When navigating to the parent directory (using '..') after changing the path in the path control, the displayed path is one level deeper than expected. (Fixed during UI migration and navigation logic refactoring).
7.  **Incorrect Selection:** Sometimes, on the active panel, files/folders were not being selected with the Insert key. (Fixed during event handling and model refactoring).
8.  **Incorrect file-types rows style:** Sometimes, after starting the application in "flat" mode, the rows in the file browsing panel were not colored according to the file extension. (Fixed during theme and view refresh logic refactoring).
9.  **Copy/Move/Delete/Sync/New Folder/New File Action Refresh:** The directory was not refreshing after these operations. Fixed by implementing `refresh_all_views()`.
10. **Translation Issues:** Various issues with untranslated UI elements (Main Menu, Tooltips, Dialogs) were fixed by implementing a robust translation context strategy.
11. **Wrong config file path:** The shortcuts file `.quickfile_shortcuts.json` was correctly moved to `~/.config/QuickFile/`.
12. **Invalid Index value:** After using the Home or End keys, the cursor position was not correctly updated. Resolved by explicitly setting the current index in the selection model.
13. **Bug: Bookmarks Button Crash:** The application crashed when the "Bookmarks" button was pressed. Resolved by adding a `get_bookmarks()` method to the `BookmarksManager`.
14. **Incorrect Selection after 'Go Up':** In "flat" view mode, after going up a directory, the cursor automatically selects the first item on the list. Resolved by ensuring the correct item is selected after navigation.
