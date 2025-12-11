# BUGS

**Fixed Bugs:**

1.  **Copy Action Error:** `AttributeError: 'str' object has no attribute 'isValid'` in `copy_selected_item` was resolved by correcting destination path retrieval.
2.  **Move Action Error:** Similar `AttributeError` in `move_selected_item` was resolved by correcting destination path retrieval.
3.  **Synchronize Operation Error:** Path retrieval and refresh issues in `synchronize_directories` were fixed. Calls were updated to `refresh_all_views()`.
4.  **Delete Action Refresh:** The directory was not refreshing after deletion. This was fixed by implementing `refresh_all_views()` for delete operations.
5.  **New Folder Action Refresh:** The directory was not refreshing after creation. Fixed by using `refresh_all_views()`.
6.  **New File Action Refresh:** The directory was not refreshing after creation. Fixed by using `refresh_all_views()`.
7.  **Translation: Main Menu:** The main application menu was not translated. Fixed by implementing a robust translation context strategy.
8.  **Translation: Tooltips:** Menu item tooltips were not translated. Fixed.
9.  **Translation: Dialogs:** Buttons and titles in "Shortcuts", "Properties", and "Error" dialogs were not translated. Fixed.
10. **Translation: About Dialog:** The "Version" label in the "About" dialog was not translated. Fixed.
11. **Wrong config file path:** The shortcuts file `.quickfile_shortcuts.json` was correctly moved to `~/.config/QuickFile/`. (Moved to fixed as it's a completed task).
12. **Invalid Index value:** After using the Home or End keys, the cursor position was not correctly updated, causing subsequent arrow key presses to fail. This was resolved by explicitly setting the current index in the selection model.
13. **Bug: Bookmarks Button Crash:** The application crashed when the "Bookmarks" button was pressed. This was resolved by adding a `get_bookmarks()` method to the `BookmarksManager` and calling it from the `ApplicationLogicHandler`.
14. **Incorrect Selection after 'Go Up':** In "flat" view mode, after going up a directory, the cursor automatically selects the first item on the list, instead of the directory that was just exited. This was resolved by ensuring the correct item is selected after navigation.

**Unresolved Bugs:**

1. **Incorrect '..' Path Navigation:** When navigating to the parent directory (using '..') after changing the path in the path control, the displayed path is one level deeper than expected (e.g., `/home/user/tmp` instead of `/home/user`). This occurs because the `_select_on_load` mechanism incorrectly prioritizes the '..' entry, leading to an unintended deeper dive into the directory structure rather than selecting the intended previous directory.
