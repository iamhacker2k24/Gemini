@echo off
title Remove .env from Git Repository
echo ========================================================
echo   Removing .env and database from Git tracking...
echo ========================================================
cd /d "%~dp0"

echo 1. Untracking .env files...
git rm --cached telegram_bot/.env 2>nul
git rm --cached .env 2>nul
git rm --cached telegram_bot/bot_database.db 2>nul
git rm --cached bot_database.db 2>nul

echo.
echo 2. Committing changes...
git add .gitignore telegram_bot/.gitignore
git commit -m "Security: Untrack .env and database files from GitHub"

echo.
echo 3. Pushing to GitHub...
git push origin main

echo.
echo ========================================================
echo   DONE! Check GitHub now - .env is no longer on GitHub!
echo ========================================================
pause
