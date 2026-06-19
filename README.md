# 🧀 Сырком — Telegram-бот с Web App

Магазин сыров и деликатесов: Telegram-бот на **aiogram 3.x** + мини-приложение (Web App) на **FastAPI**.

Канал: [@cheessecom](https://t.me/cheessecom)

## Возможности

### Бот
- Онбординг: город, тип клиента, промокод **КОНТРАБАНДА1**
- Главное меню: О компании / Сделать заказ / Оставить отзыв
- Админ-панель (`/admin`): статистика, заказы, отзывы, пользователи, рассылка, настройки

### Web App
- Каталог по 9 странам (58 товаров)
- Поиск, фильтры, карточки товаров
- Корзина с оформлением заказа
- Профиль: заказы, избранное, акции

## Быстрый старт

### 1. Установка

```bash
cd cheese_bot
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Настройка

Отредактируйте `config.py` или задайте переменные окружения:

```bash
export BOT_TOKEN="123456:ABC-DEF..."
export ADMIN_ID="your_telegram_id"
export WEBAPP_URL="https://your-domain.com/webapp"
```

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен бота от [@BotFather](https://t.me/BotFather) |
| `ADMIN_ID` | Ваш Telegram ID (узнать: [@userinfobot](https://t.me/userinfobot)) |
| `WEBAPP_URL` | Публичный HTTPS-URL Web App |
| `API_PORT` | Порт API (по умолчанию 8000) |

### 3. Настройка Web App в BotFather

```
/mybots → ваш бот → Bot Settings → Menu Button → Configure menu button
URL: https://your-domain.com/webapp
```

### 4. Запуск

**Терминал 1 — API + Web App:**
```bash
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

**Терминал 2 — Telegram-бот:**
```bash
python bot.py
```

### 5. Локальная разработка (ngrok)

Telegram Web App требует HTTPS. Для локальной разработки:

```bash
ngrok http 8000
```

Скопируйте HTTPS-URL в `WEBAPP_URL` и перезапустите бота.

## Структура проекта

```
cheese_bot/
├── bot.py              # Запуск Telegram-бота
├── api.py              # FastAPI: API + раздача Web App
├── config.py           # Настройки
├── database.py         # SQLite, миграции, seed товаров
├── keyboards.py        # Клавиатуры бота
├── handlers/
│   ├── start.py        # /start, онбординг
│   ├── menu.py         # Главное меню
│   ├── review.py       # Отзывы
│   └── admin.py        # Админ-панель
├── webapp/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── data/               # SQLite БД (создаётся автоматически)
├── requirements.txt
└── README.md
```

## Админ-панель

Команда `/admin` (доступна только ADMIN_ID и добавленным админам):

| Раздел | Описание |
|---|---|
| 📊 Статистика | Пользователи, заказы, выручка, конверсия |
| 📦 Заказы | Список, детали, смена статуса |
| ⭐ Отзывы | Просмотр и ответ пользователю |
| 👥 Пользователи | Список последних 30 |
| 📢 Рассылка | Сообщение всем (rate limit 25/сек) |
| ⚙️ Настройки | Промокод, скидка, реквизиты, админы |

## Каталог товаров

При первом запуске в БД загружается **58 товаров** из 9 стран:
Россия, Италия, Голландия, Испания, Германия, Англия, Франция, Норвегия, Польша.

Категории: Сыры, Мясные деликатесы, Колбасы, Морепродукты, Рыба, Икра, Паштеты, Соусы и масла, Сладости.

## Лицензия

MIT
