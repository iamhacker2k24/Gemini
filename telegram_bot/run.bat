@echo off
title Google Gemini Claimer - Telegram Bot
echo ========================================================
echo       Google Gemini 12-Month Trial Telegram Bot
echo ========================================================
cd /d "%~dp0"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found or not in PATH!
    pause
    exit /b
)

echo Starting Bot...
:loop
python bot.py
echo.
echo [!] Bot process stopped or crashed. Restarting in 5 seconds...
echo (Press Ctrl+C to close)
timeout /t 5
goto loop
