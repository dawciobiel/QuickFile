@echo off
:: ==============================================================================
:: QuickFile - Development Environment Setup Script (Batch)
::
:: Description:
::   Sets up the Python virtual environment (.venv) for development.
::   Installs both production (requirements.txt) and development (requirements-dev.txt) dependencies.
::
:: Usage:
::   .\scripts\install-dev-env.bat
::
:: Project: QuickFile
:: Author:  Dawid 'Dawciobiel' Biel
:: Date:    2025-12-25
:: Version: 1.0.0
:: License: GNU General Public License v3.0
:: CLA:     Contributers License Agreement (CLA.md)
::
:: Copyright (c) 2025 Dawid Biel. All rights reserved.
:: ==============================================================================
setlocal

echo 🔧 Setting up development virtual environment (.venv)...

:: Function to find the correct python command
where python >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
) else (
    where python3 >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=python3
    ) else (
        echo ❌ Python is not installed or not in PATH.
        exit /b 1
    )
)

if not exist ".venv" (
    echo 📦 Creating a new virtual environment...
    %PYTHON_CMD% -m venv .venv
) else (
    echo ✅ Virtual environment already exists.
)

:: Activate the environment
call .venv\Scripts\activate.bat

:: Upgrade pip
echo upgrading pip...
pip install --upgrade pip

:: Install production dependencies
if exist "requirements.txt" (
    echo 📥 Installing production dependencies from requirements.txt...
    pip install -r requirements.txt
) else (
    echo ⚠️ requirements.txt not found, skipping.
)

:: Install development dependencies
if exist "requirements-dev.txt" (
    echo 📥 Installing development dependencies from requirements-dev.txt...
    pip install -r requirements-dev.txt
) else (
    echo ⚠️ requirements-dev.txt not found, skipping.
)

:: Deactivate the environment (optional, as the script ends here anyway)
:: call deactivate

echo ✅ Development environment setup complete!
endlocal