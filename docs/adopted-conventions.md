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

### Dlaczego stosować małe litery:

1. **Spójność**: Jest to standard w większości projektów open-source.
2. **Zgodność z systemami plików**: Niektóre systemy (np. Linux) rozróżniają wielkość liter, co może powodować błędy w
   przenoszeniu projektów między platformami.
3. **Czytelność**: Małe litery z myślnikami wyglądają bardziej uporządkowanie niż mieszanie wielkich liter,
   podkreślników czy spacji.
