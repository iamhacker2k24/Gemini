#!/bin/bash
echo "========================================================"
echo "      Google Gemini 12-Month Trial Telegram Bot"
echo "========================================================"
cd "$(dirname "$0")"

pip install -r requirements.txt

while true; do
    echo "Starting Bot..."
    python3 bot.py
    echo "[!] Bot stopped. Restarting in 5 seconds..."
    sleep 5
done
