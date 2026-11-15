# Adopted conventions

W przypadku struktury folderów i plików w projekcie programistycznym (zwłaszcza w kontekście dokumentacji), stosuje się
kilka zasad konwencji nazewniczych, aby utrzymać spójność i czytelność. Oto rekomendacje:

---

### **Ogólne zasady:**

1. **Foldery:**
    - **Małe litery (lowercase)** z myślnikami (`-`) jako separatorami:
      ```plaintext
      docs/
      architecture/
      file-browser/
      ```
    - Powód: Ułatwia to zarządzanie w systemach plików, które rozróżniają wielkość liter (np. Linux). Ponadto wygląda
      bardziej spójnie i jest zgodne z dobrymi praktykami.

2. **Pliki:**
    - **Małe litery (lowercase)**, również z myślnikami (`-`) jako separatorami:
      ```plaintext
      file-browser.md
      architecture-overview.md
      ```
    - Wyjątkiem mogą być pliki wymagające specyficznego formatowania (np. README.md).

3. **Rozszerzenia plików:**
    - Zawsze **małe litery**:
      ```plaintext
      file-browser.md
      ```

4. **Wielkość liter dla nazw dokumentów:**
    - W samym tekście dokumentu możesz używać wielkich liter (np. nagłówki `File Browser` w Markdown), ale nazwa pliku
      powinna pozostać w małych literach.

---

### **Twoja struktura w oparciu o powyższe zasady:**

```plaintext
docs/
|_ architecture/
   |_ file-browser.md
```

---

### **Screenshoty (`docs/screenshots/`):**

1. **Miejsce:**
    - Zrzuty ekranu dokumentacji trzymamy w `docs/screenshots/`.
    - **Nie** dodajemy ich do `resources/`: cały ten katalog jest pakowany do wheel'a
      (`[tool.setuptools.package-data]`), więc każdy obrazek trafia do dystrybucji
      i powiększa instalację. Wyjątkiem są dotychczasowe pliki w
      `resources/screenshots/` używane przez `README.md` — te zostają do czasu
      przeniesienia, ale nowych tam nie dodajemy.

2. **Nazwy plików** — `<obszar>-<temat>[-<wariant>].png`:
    - `application-` — powłoka aplikacji: start, log uruchomienia, okna systemowe,
    - `feature-` — funkcja aplikacji: motywy, kopiowanie, ustawienia języka,
    - `plugin-` — UI dostarczane przez plugin: viewer, edytor.

    ```plaintext
    application-about-dialog.png
    feature-theme-dark.png
    plugin-file-viewer-markdown.png
    ```

3. **Zasady:**
    - małe litery, myślniki, ASCII, rozszerzenie `.png` małymi literami,
    - `temat` opisuje, **co widać** (`about-dialog`), a nie czynność (`showing-about`),
    - `wariant` tylko wtedy, gdy ten sam temat ma warianty (`-dark`, `-light`,
      `-markdown`),
    - **bez daty i numeru wersji w nazwie**: odświeżenie zrzutu nie może wymagać
      poprawiania linków w dokumentacji; wersję aplikacji podaje podpis pod
      obrazkiem,
    - format PNG, pełne okno; przed commitem warto zmniejszyć rozmiar bezstratnie
      (`oxipng`, `pngquant`).

---

### Dlaczego stosować małe litery:

1. **Spójność**: Jest to standard w większości projektów open-source.
2. **Zgodność z systemami plików**: Niektóre systemy (np. Linux) rozróżniają wielkość liter, co może powodować błędy w
   przenoszeniu projektów między platformami.
3. **Czytelność**: Małe litery z myślnikami wyglądają bardziej uporządkowanie niż mieszanie wielkich liter,
   podkreślników czy spacji.
