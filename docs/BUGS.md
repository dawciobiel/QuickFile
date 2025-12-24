# BUGS

## Nierozwiązane (Unresolved)

(Brak)

## Naprawione (Fixed)

1.  **Incorrect '..' Path Navigation:** When navigating to the parent directory (using '..') after changing the path in the path control, the
    displayed path is one level deeper than expected. (Fixed during UI migration and navigation logic refactoring).
2.  **Incorrect Selection:** Sometimes, on the active panel, files/folders were not being selected with the Insert key. (Fixed during event handling and model refactoring).
3.  **Incorrect file-types rows style:** Sometimes, after starting the application in "flat" mode, the rows in the file browsing panel were not colored according to the file extension. (Fixed during theme and view refresh logic refactoring).

### Operacje na Plikach (File Operations)
4.  **Copy Action Error:** `AttributeError: 'str' object has no attribute 'isValid'` in `copy_selected_item` was resolved by correcting destination path retrieval.
5.  **Move Action Error:** Similar `AttributeError` in `move_selected_item` was resolved by correcting destination path retrieval.
6.  **Synchronize Operation Error:** Path retrieval and refresh issues in `synchronize_directories` were fixed. Calls were updated to `refresh_all_views()`.
7.  **Delete Action Refresh:** The directory was not refreshing after deletion. This was fixed by implementing `refresh_all_views()` for delete operations.
8.  **New Folder Action Refresh:** The directory was not refreshing after creation. Fixed by using `refresh_all_views()`.
9.  **New File Action Refresh:** The directory was not refreshing after creation. Fixed by using `refresh_all_views()`.

### Interfejs i Tłumaczenia (UI & Translations)
10. **Translation: Main Menu:** The main application menu was not translated. Fixed by implementing a robust translation context strategy.
11. **Translation: Tooltips:** Menu item tooltips were not translated. Fixed.
12. **Translation: Dialogs:** Buttons and titles in "Shortcuts", "Properties", and "Error" dialogs were not translated. Fixed.
13. **Translation: About Dialog:** The "Version" label in the "About" dialog was not translated. Fixed.
14. **Wrong config file path:** The shortcuts file `.quickfile_shortcuts.json` was correctly moved to `~/.config/QuickFile/`. (Moved to fixed as it's a completed task).
15. **Invalid Index value:** After using the Home or End keys, the cursor position was not correctly updated, causing subsequent arrow key presses to fail. This was resolved by explicitly setting the current index in the selection model.
16. **Bug: Bookmarks Button Crash:** The application crashed when the "Bookmarks" button was pressed. This was resolved by adding a `get_bookmarks()` method to the `BookmarksManager` and calling it from the `ApplicationLogicHandler`.
17. **Incorrect Selection after 'Go Up':** In "flat" view mode, after going up a directory, the cursor automatically selects the first item on the list, instead of the directory that was just exited. This was resolved by ensuring the correct item is selected after navigation.
