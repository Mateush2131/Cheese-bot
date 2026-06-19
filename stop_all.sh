#!/bin/bash
echo "→ Останавливаю все сервисы Сырком..."
pkill -f "uvicorn api:app" 2>/dev/null || true
pkill -f "python bot.py" 2>/dev/null || true
pkill -f "cloudflared tunnel --url" 2>/dev/null || true
echo "✅ Остановлено"
