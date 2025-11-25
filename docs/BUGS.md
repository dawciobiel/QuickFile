# BUGS

1. Okno dialogowe błędu pojawia się w przypadku trybu przeglądania plików "table". 
W trybie przeglądania plików "tree" okno dialogowe od błędu się nie pokazuje, np. przy próbie wejścia do folderu do którego użytkownik nie posiada uprawnienia np. "/root".
2. W aplikacji nie działa funkcja zaznaczania plików/katalogów za pomocą prawego klawisza myszy lub za pomocą klawisza "Insert". Wydaje mi się, że ta funkcjonalność była już implementowana ale być może przestała działaś w momencie poprawiania działania paneli do przeglądania katalogów.
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

