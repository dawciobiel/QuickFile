# Notatka dotycząca obsługi archiwów RAR

Implementacja pełnej obsługi archiwów RAR (zarówno tworzenia, jak i wypakowywania) w aplikacji wieloplatformowej jest problematyczna z kilku powodów, głównie licencyjnych i technicznych.

## 1. Wypakowywanie (Dearchiwizacja)

- **Możliwość implementacji**: Tak, jest to możliwe przy użyciu darmowych narzędzi.
- **Problem**: Najpopularniejsza biblioteka w Pythonie, `rarfile`, jest jedynie nakładką (wrapperem) na zewnętrzny program konsolowy `unrar` dostarczany przez RARLAB.
- **Zależność**: Aby funkcja działała, użytkownik końcowy musi samodzielnie zainstalować program konsolowy w swoim systemie operacyjnym (Windows, macOS, Linux) i dodać go do ścieżki systemowej (PATH). `rarfile` akceptuje `unrar`, `unar`, `bsdtar`, `7z` lub `7zz` i sam wybiera pierwszy dostępny.
- **Rozwiązanie**: Zaimplementowane. `rar_archiver` deklaruje wymaganie w `external_tools`, a host sprawdza je w `app/external_tools.py` **przed** dodaniem zadania do kolejki. Brak narzędzia kończy się komunikatem z listą akceptowanych poleceń, a nie błędem w środku zadania. Kontrakt opisuje `docs/architecture/plugins/plugins.md` („Narzędzia zewnętrzne”).

## 2. Tworzenie (Archiwizacja)

- **Możliwość implementacji**: Bardzo ograniczona i problematyczna.
- **Problem**: Oficjalny enkoder (program do tworzenia archiwów RAR) jest oprogramowaniem komercyjnym. Jego licencja nie pozwala na swobodne dołączanie go do innych aplikacji. Nie istnieją w pełni funkcjonalne, darmowe i otwarte alternatywy, które moglibyśmy zintegrować z naszym projektem.
- **Wniosek**: Nie możemy w legalny i niezawodny sposób zaimplementować tworzenia archiwów RAR w naszej aplikacji.

## Podsumowanie i proponowana strategia

- **Implementujemy**: **Tylko wypakowywanie** archiwów RAR.
- **Wymagania**: Użytkownik musi samodzielnie zainstalować jedno z narzędzi: `unrar`, `unar`, `bsdtar`, `7z` lub `7zz`.
- **Logika aplikacji**: Host weryfikuje obecność narzędzia i przy jego braku wyświetla komunikat przed rozpoczęciem zadania. Wtyczka nie instaluje narzędzi i nie odpytuje ich o wersję.
