@echo off
chcp 65001 >nul
echo ========================================
echo    TestCase Builder - Starting...
echo ========================================
cd /d "%~dp0"

:: Zkontroluj Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

:: Instalace závislostí z requirements.txt
echo Installing dependencies...
if exist requirements.txt (
    pip install -r requirements.txt
) else (
    pip install streamlit pandas openpyxl
)

if errorlevel 1 (
    echo ERROR: Failed to install packages
    pause
    exit /b 1
)

echo.
echo Starting application...
echo The app will open in your browser shortly...
echo.
python -m streamlit run gui_app/app.py

echo.
echo Application closed.
pause