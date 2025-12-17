#!/bin/bash

# Przejdź do katalogu głównego projektu
cd "$(dirname "$0")/.."

# Upewnij się, że katalog logów istnieje
mkdir -p logs

# Nazwa pliku log
LOG_FILE="logs/test_results.log"

# --- Czyszczenie starego logu ---
# Używamy '>' aby nadpisać plik i zacząć od nowa
echo "Starting test session on $(date)" > "$LOG_FILE"
echo "================================================================================" >> "$LOG_FILE"

echo "Running all tests and capturing complete output to $LOG_FILE..."

# --- Uruchomienie Pytest ---
# Używamy 'script' aby oszukać pytest/tee i myśleć, że działają w interaktywnym terminalu,
# co zmusza je do zachowania kolorów i pełnego formatowania.
# Wynik jest dopisywany do LOG_FILE.
script -q -c "pytest -v --tb=long tests/" /dev/null | tee -a "$LOG_FILE"

# --- Sprawdzenie wyniku ---
# Musimy pobrać status wyjścia z pytest, co jest trudniejsze z 'script'.
# Możemy to zrobić, sprawdzając zawartość logu w poszukiwaniu słowa "failed".
# To nie jest idealne, ale jest to proste i skuteczne obejście.
if grep -q "failed" "$LOG_FILE"; then
    echo "================================================================================" >> "$LOG_FILE"
    echo "🔴 Some tests failed. Check $LOG_FILE for details." | tee -a "$LOG_FILE"
    echo "================================================================================" >> "$LOG_FILE"
else
    echo "================================================================================" >> "$LOG_FILE"
    echo "✅ All tests passed!" | tee -a "$LOG_FILE"
    echo "================================================================================" >> "$LOG_FILE"
fi

echo "Test run finished. Full output is in $LOG_FILE"
