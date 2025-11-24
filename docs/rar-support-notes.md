# Notatka dotycząca obsługi archiwów RAR

Implementacja pełnej obsługi archiwów RAR (zarówno tworzenia, jak i wypakowywania) w aplikacji wieloplatformowej jest problematyczna z kilku powodów, głównie licencyjnych i technicznych.

## 1. Wypakowywanie (Dearchiwizacja)

- **Możliwość implementacji**: Tak, jest to możliwe przy użyciu darmowych narzędzi.
- **Problem**: Najpopularniejsza biblioteka w Pythonie, `rarfile`, jest jedynie nakładką (wrapperem) na zewnętrzny program konsolowy `unrar` dostarczany przez RARLAB.
- **Zależność**: Aby funkcja działała, użytkownik końcowy musi samodzielnie zainstalować program `unrar` w swoim systemie operacyjnym (Windows, macOS, Linux) i dodać go do ścieżki systemowej (PATH).
- **Rozwiązanie**: Możemy zaimplementować funkcję wypakowywania, która przed uruchomieniem sprawdza, czy `unrar` jest dostępny. Jeśli nie, aplikacja poinformuje użytkownika o konieczności jego instalacji, zamiast powodować błąd.

## 2. Tworzenie (Archiwizacja)

- **Możliwość implementacji**: Bardzo ograniczona i problematyczna.
- **Problem**: Oficjalny enkoder (program do tworzenia archiwów RAR) jest oprogramowaniem komercyjnym. Jego licencja nie pozwala na swobodne dołączanie go do innych aplikacji. Nie istnieją w pełni funkcjonalne, darmowe i otwarte alternatywy, które moglibyśmy zintegrować z naszym projektem.
- **Wniosek**: Nie możemy w legalny i niezawodny sposób zaimplementować tworzenia archiwów RAR w naszej aplikacji.

## Podsumowanie i proponowana strategia

- **Implementujemy**: **Tylko wypakowywanie** archiwów RAR.
- **Wymagania**: Użytkownik musi samodzielnie zainstalować narzędzie `unrar`.
- **Logika aplikacji**: Aplikacja będzie zawierać mechanizm weryfikujący obecność `unrar` i w razie jego braku, wyświetli odpowiedni komunikat.
