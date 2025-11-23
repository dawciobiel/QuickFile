# TODO List

- Create `File viewer` module

- Zapytać ChatGPT w jaki sposób rozwiązać problem nasłuchiwania wielu modułów (folder_browser, hotkey menu) na zdarzenia klawiszowe.
Bo Python nie jest ponoć wielowątkowy

- stworzyć style dla aplikacji. Chodzi między innymi o odowiednie kolorowanie zaznaczanych plików itp.
- dodać funkcje różne aplikacji (tworzenie sum kontrolnych dla wybranych plików, sprawdzanie sum kontrolnych, obsługę FTP, NFS, SMB)


## Testing Writestyle code assistant 
{collapsible="true" default-state="expanded"}

{style="warning"}
> some warning message

## Nowe zadania (2025-11-23)

- Niech naciśnięcie klawisza `Backspace` na klawiaturze powoduje przejśćie do katalogu nadrzędnego.
- Klawisz `End` owszem przechodzi do ostatniej pozycji w panelu plików. Jednak aby klawisz ten zadziałał trzeba go nacisnąć dwa razy.
- Jest błąd po wejściu do katalogu `/home/dawciobiel/.icons`. To jest pozycja ".." nie jest wyświetlana jako pierwsza. A to z powodu faktu, że najpierw jest wyświetlana pozycja `+OxygenE` - czyli folder zawierający na początku nazwy znak `+`.
- W trybie `Tree` - nie widać pozycji ".." na liście plików. Zaimplementowanie tej funkcjonalności może być trudne.