@echo off
echo ============================================
echo   Stock Analysis AI Dashboard - Install
echo ============================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found.
    echo Install Python 3.10+ from https://www.python.org/downloads/
    echo Check "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo [1/3] Creating virtual environment...
cd /d "%~dp0"
python -m venv .venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create venv
    pause
    exit /b 1
)

echo [2/3] Activating...
call ".venv\Scripts\activate.bat"

echo [3/3] Installing packages... (1-3 min)
pip install -r requirements.txt

echo.
echo ============================================
echo   Install complete!
echo ============================================
echo.
echo Run: double-click run.bat
echo.
pause
