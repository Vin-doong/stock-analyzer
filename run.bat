@echo off
echo ====================================
echo   Stock Analysis AI Dashboard
echo ====================================
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv not found. Run install.bat first.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
streamlit run app.py
pause
