#!/bin/bash
# HTTPS-туннель для Telegram Web App (нужен публичный HTTPS-URL)
# Запускайте ПОСЛЕ uvicorn: python -m uvicorn api:app --host 0.0.0.0 --port 8000

echo "Запуск cloudflared-туннеля на порт 8000..."
echo "Скопируйте URL вида https://xxxx.trycloudflare.com"
echo "и пропишите в config.py: WEBAPP_URL = \"https://xxxx.trycloudflare.com/webapp\""
echo "Затем перезапустите bot.py"
echo ""

cloudflared tunnel --url http://127.0.0.1:8000
