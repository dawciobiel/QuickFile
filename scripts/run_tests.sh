#!/bin/bash

# Upewnij się, że jesteś w katalogu głównym projektu
cd "$(dirname "$0")/.."

# Utwórz katalog logs, jeśli nie istnieje
mkdir -p logs

# Nazwa pliku log
LOG_FILE="logs/test_results.log"

echo "Running tests and saving output to $LOG_FILE"
echo "================================================================================" > "$LOG_FILE"
date >> "$LOG_FILE"
echo "================================================================================" >> "$LOG_FILE"

# Uruchom pytest i przekieruj wyjście do pliku log
# Używamy -s, aby zobaczyć printy w konsoli, jeśli testy przejdą, ale nadal zapisujemy do pliku
# Używamy -v dla bardziej szczegółowego wyjścia
# Możesz dodać --tb=no, aby ukryć tracebacki w konsoli, jeśli chcesz, ale w logu są przydatne
pytest tests/test_properties_dialog.py "$@" | tee -a "$LOG_FILE"

# Sprawdź status wyjścia pytest
if [ $? -eq 0 ]; then
    echo "================================================================================" >> "$LOG_FILE"
    echo "All tests passed!" | tee -a "$LOG_FILE"
    echo "================================================================================" >> "$LOG_FILE"
else
    echo "================================================================================" >> "$LOG_FILE"
    echo "Some tests failed. Check $LOG_FILE for details." | tee -a "$LOG_FILE"
    echo "================================================================================" >> "$LOG_FILE"
fi

echo "Test run finished. Results are in $LOG_FILE"
