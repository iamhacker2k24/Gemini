@echo off
title Setup Telegram Bot Dependencies
echo ========================================================
echo        Installing Telegram Bot Dependencies...
echo ========================================================
cd /d "%~dp0"

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found or not in PATH!
    echo Please install Python 3.9+ from https://www.python.org/
    pause
    exit /b
)

echo Installing required packages...
pip install -r requirements.txt

echo.
echo ========================================================
echo  Installation Completed!
echo  Next: Edit .env to set your BOT_TOKEN and ADMIN_IDS
echo  Then double-click run.bat to start your bot!
echo ========================================================
pause
