# BUGS

**Fixed Bugs:**

1.  **Copy Action Error:** `AttributeError: 'str' object has no attribute 'isValid'` in `copy_selected_item` was resolved by correcting destination path retrieval.
2.  **Move Action Error:** Similar `AttributeError` in `move_selected_item` was resolved by correcting destination path retrieval.
3.  **Synchronize Operation Error:** Path retrieval and refresh issues in `synchronize_directories` were fixed. Calls were updated to `refresh_all_views()`.
4.  **Delete Action Refresh:** The directory was not refreshing after deletion. This was fixed by implementing `refresh_all_views()` for delete operations.
5.  **New Folder Action Refresh:** The directory was not refreshing after creation. Fixed by using `refresh_all_views()`.
6.  **New File Action Refresh:** The directory was not refreshing after creation. Fixed by using `refresh_all_views()`.
7.  **Not Translated:** Menu główne aplikacji w całości jest w języku angielskim.

**Unresolved Bugs:**

1.   **Incorrect '..' Path Navigation:** When navigating to the parent directory (using '..') after changing the path in the path control, the displayed path is one level deeper than expected (e.g., `/home/user/tmp` instead of `/home/user`). This occurs because the `_select_on_load` mechanism incorrectly prioritizes the '..' entry, leading to an unintended deeper dive into the directory structure rather than selecting the intended previous directory.
2. **Not Translated:** Tooltip'y menu Items również są w języku angielskim.
3. **Not Translated:** Okno "Skróty Klawiszowe": przyciski "Save", "Cancel" są w języku angielskim. Wszystkie akcje przypisane do skrótów klawiszowych ("Exit", "Go up"...) są również wyświetlone w języku angielskim - ale myślę, że nazw tych akcji nie ma sensu tłumaczyć aby nie było to bardziej mylące.
4. **Not Translated:** Tytuł okna "Właściwości" "Error" jest w języku angielskim.
8.  **Wrong config file path:** Plik zapamiętujący skróty klawiszowe .quickfile_shortcuts.json został przeniesiony do `~/.config/QuickFile/`.

**Unresolved Bugs:**

1.   **Incorrect '..' Path Navigation:** When navigating to the parent directory (using '..') after changing the path in the path control, the displayed path is one level deeper than expected (e.g., `/home/user/tmp` instead of `/home/user`). This occurs because the `_select_on_load` mechanism incorrectly prioritizes the '..' entry, leading to an unintended deeper dive into the directory structure rather than selecting the intended previous directory.
2. **Not Translated:** Tooltip'y menu Items również są w języku angielskim.
3. **Not Translated:** Okno "Skróty Klawiszowe": przyciski "Save", "Cancel" są w języku angielskim. Wszystkie akcje przypisane do skrótów klawiszowych ("Exit", "Go up"...) są również wyświetlone w języku angielskim - ale myślę, że nazw tych akcji nie ma sensu tłumaczyć aby nie było to bardziej mylące.
4. **Not Translated:** Tytuł okna "Właściwości" "Error" jest w języku angielskim.
5. **Not Translated:** W oknie "O programie" jest wersja aplikacji podana z użyciem angielskiego słowa "Version".
7. **Not Translated:** Nie przetłumaczone okno dialogowe o błędzie "Error". Treść w oknie : "Critical Error Occurred" i " The application encountered an unexpected error.
Details have been written to the log file."
8. **Feature not working:** Błąd akcji pokazującej "Właściwości" wybranego pliku/katalogu:
```log
    Error
    No file or folder selected.
```
Błąd ten występuje niezależnie czy plik/katalog jest zaznaczony czy niezaznaczony. Ten błąd rozwiązywać na branchu "master".
