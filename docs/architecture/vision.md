# Wizja Architektury QuickFile

## Cel: Platform-Agnostic Core

Aplikacja ma być **platform-agnostic** w warstwie UI i logiki biznesowej. Cała "brudna robota" specyficzna dla systemu operacyjnego (jak kopiowanie, wyszukiwanie, archiwizacja) ma być delegowana do **pluginów**.

## Zasady Architektoniczne

1.  **Chudy Koordynator**: `FileManager` (i inne menedżery) powinien stać się "chudym" koordynatorem, który nie implementuje logiki bezpośrednio (np. `shutil.copy`), ale deleguje ją do odpowiedniego pluginu.
2.  **Abstrakcyjne Interfejsy**: Interfejsy pluginów muszą być na tyle ogólne, by obsłużyć różnice między systemami (np. uprawnienia plików na Linux vs ACL na Windows), ale na tyle konkretne, by UI wiedziało, co wyświetlić.
3.  **Wszystko jest Pluginem**: Każda kluczowa operacja (wyszukiwanie, kopiowanie, archiwizacja, sumy kontrolne) powinna być realizowana przez plugin.

## Przykład: Wyszukiwanie Plików

Wyszukiwanie plików (nasz obecny cel) również musi być pluginem. Pozwoli to na łatwą wymianę implementacji w zależności od systemu:
*   `StandardSearchPlugin` (uniwersalny, oparty na `os.walk`).
*   `LinuxFindPlugin` (oparty na `find`).
*   `WindowsSearchPlugin` (oparty na Windows Indexing Service).
*   `EverythingPlugin` (integracja z narzędziem "Everything").
