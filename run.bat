@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
chcp 65001 > nul
python app.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application terminated with error code %errorlevel%.
    pause
)
