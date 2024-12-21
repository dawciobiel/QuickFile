# Commits good practise

### **Dobre praktyki:**

- Unikaj ogólników, takich jak "zaprojektowano architekturę", bez wskazania szczegółów.
- Jeśli commit dotyczy wielu plików, wskaż kluczowe zmiany w opisie szczegółowym.
- Pisz w czasie dokonanym (np. "dodano", "utworzono"), aby opis brzmiał bardziej jednoznacznie.

Skróty takie jak **`feat`**, **`fix`**, **`refactor`**, **`chore`**, czy **`docs`** są stosowane w nagłówkach commitów
zgodnie z konwencją [Conventional Commits](https://www.conventionalcommits.org/). Ułatwiają one czytelność historii
commitów oraz automatyzację procesów, np. generowanie changeloga.

### Najczęściej używane typy commitów:

1. **`feat`** – Gdy dodajesz nową funkcjonalność (np. zaprojektowanie szkieletu architektury).
2. **`fix`** – Gdy naprawiasz błąd.
3. **`refactor`** – Gdy zmieniasz kod, ale bez zmiany jego funkcjonalności (np. optymalizacja).
4. **`docs`** – Gdy edytujesz dokumentację.
5. **`chore`** – Drobne zmiany niezwiązane bezpośrednio z kodem (np. aktualizacja zależności, konfiguracja). ~~ ~~

### Dlaczego warto używać?

- Ułatwia zrozumienie celu każdego commita.
- Pozwala narzędziom automatycznym (np. CI/CD) analizować typy zmian.
- Dobrze współgra z wersjonowaniem semantycznym (Semantic Versioning), np. dodanie nowej funkcji (**`feat`**) może
  automatycznie podnieść numer minor w wersji (`1.x.0` → `1.x+1.0`).

### Przykłady:

1. **`feat: Add initial architecture skeleton`**
2. **`fix: Resolve issue with application startup`**
3. **`refactor: Simplify directory structure`**
4. **`docs: Update README with setup instructions`**
5. **`chore: Update project dependencies`**
