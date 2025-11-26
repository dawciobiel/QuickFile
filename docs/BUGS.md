# BUGS

1. Błąd przy próbie wykonania akcji Copy:
```log
    2025-11-25 21:44:52,611 - __main__ - CRITICAL - Unhandled exception:
    Traceback (most recent call last):
      File "/home/dawciobiel/PycharmProjects/QuickFile/panels/menu_panel.py", line 268, in copy_selected_item
        destination_path = inactive_panel.model().filePath(self.main_window.folder_browser.current_paths[inactive_panel])
      File "/home/dawciobiel/PycharmProjects/QuickFile/browser/flat_file_system_model.py", line 141, in filePath
        if index.isValid() and 0 <= index.row() < len(self._items):
           ^^^^^^^^^^^^^
    AttributeError: 'str' object has no attribute 'isValid'
```
2. Błąd przy próbie wykonania akcji Move
3. Błąd przy wywołaniu funkcji "Compare" i aplikacja się zakańcza działanie. Pokazuje się okno dialogowe "Error" z treścią:
```log
    Critical Error Occurred

    The application encountered an unexpected error.
    Details have been written to the log file.
```
Dodatkowe informacje zapisywane są w logu aplikacji `~/.config/QuickFile/main.log`:
```log
    2025-11-25 01:24:27,029 - __main__ - CRITICAL - Unhandled exception:
    Traceback (most recent call last):
      File "/home/dawciobiel/PycharmProjects/QuickFile/core/main_window.py", line 156, in _compare_selected_items
        left_selected_path = self.folder_browser.left_panel.get_selected_path()
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    AttributeError: 'QTableView' object has no attribute 'get_selected_path'
```
Być może błąd jest to spowodowane faktem, że funkcja "Compare" została wywołana w aplikacji bez wcześniejszego zaznaczenia plików lub katalogów w panelach aplikacji.
Ewentualnie jest to poprawny błąd który powinien być przechwycony i wyświetlony jako "no items selected to compare".
4. Przy wybraniu akcji Operations -> Synchronize również wyrzuca podobnym błędem.
5. Przy wybraniu operacji Operations -> Search również wyrzuca błędem.
6. Akcja Delete po pomyślnym zakończeniu nie odświeża bierzącego katalogu. Przez co skasowany obiekt dalej widnieje na liście.
Można to naprawić:
a) odświeżając bierzący katalog - czyli wywołując akcje Refresh.
b) Za pomocą tylko skasowania wybranego obiektu z modelu "table" lub modelu "tree".
6. Akcja Operations -> New Folder po pomyślnym zakończeniu nie odświeża bierzącego katalogu.
7. Akcja Operations -> New File - to samo, czyli nie odświeża bierzącego katalogu.

