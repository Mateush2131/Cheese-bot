#!/bin/bash
set -e
cd "$(dirname "$0")"

PORT=8000
VENV="./venv/bin/python"

echo "=== Сырком: запуск всех сервисов ==="

# Остановить старые процессы на этом порту / боте
echo "→ Останавливаю старые процессы..."
pkill -f "uvicorn api:app" 2>/dev/null || true
pkill -f "python bot.py" 2>/dev/null || true
pkill -f "cloudflared tunnel --url http://127.0.0.1:${PORT}" 2>/dev/null || true
sleep 1

# 1. API
echo "→ Запуск API (uvicorn)..."
$VENV -m uvicorn api:app --host 0.0.0.0 --port $PORT &
API_PID=$!
sleep 2

if ! curl -s "http://127.0.0.1:${PORT}/api/health" | grep -q ok; then
  echo "❌ API не запустился"
  exit 1
fi
echo "✅ API работает на порту $PORT"

# 2. HTTPS-туннель
echo "→ Запуск cloudflared-туннеля..."
TUNNEL_LOG=$(mktemp)
cloudflared tunnel --url "http://127.0.0.1:${PORT}" > "$TUNNEL_LOG" 2>&1 &
TUNNEL_PID=$!

TUNNEL_URL=""
for i in $(seq 1 20); do
  TUNNEL_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$TUNNEL_LOG" | head -1)
  if [ -n "$TUNNEL_URL" ]; then break; fi
  sleep 1
done

if [ -z "$TUNNEL_URL" ]; then
  echo "❌ Не удалось получить URL туннеля"
  cat "$TUNNEL_LOG"
  exit 1
fi

WEBAPP_URL="${TUNNEL_URL}/webapp"
echo "✅ Туннель: $TUNNEL_URL"

# Обновить config.py
sed -i '' "s|\"https://[^\"]*trycloudflare.com/webapp\"|\"${WEBAPP_URL}\"|" config.py
echo "✅ config.py обновлён: $WEBAPP_URL"

# 3. Бот
echo "→ Запуск Telegram-бота..."
$VENV bot.py &
BOT_PID=$!
sleep 2

echo ""
echo "=========================================="
echo "  ✅ Всё запущено!"
echo "  API:     http://127.0.0.1:${PORT}"
echo "  Web App: $WEBAPP_URL"
echo "  Bot PID: $BOT_PID"
echo "=========================================="
echo ""
echo "Откройте бота → Сделать заказ → Открыть каталог"
echo "Для остановки: ./stop_all.sh"
echo ""

# Держим скрипт живым, чтобы дочерние процессы не умерли
wait
