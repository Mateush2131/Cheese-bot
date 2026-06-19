import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "8922217599:AAGJxdPuLakZFSRKJOSH1IPMma9uCKTWj8Q")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6033527749"))
ADMIN_IDS = [ADMIN_ID] + [
    int(x.strip())
    for x in os.getenv("EXTRA_ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
]

# Канал компании
TELEGRAM_CHANNEL = "@cheessecom"
TELEGRAM_CHANNEL_URL = "https://t.me/cheessecom"

# Web App & API
WEBAPP_URL = os.getenv(
    "WEBAPP_URL",
    "https://gentleman-assembled-msgid-driver.trycloudflare.com/webapp",
)
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_BASE_URL = os.getenv("API_BASE_URL", f"http://localhost:{API_PORT}")

# Database
DATABASE_PATH = BASE_DIR / "data" / "shop.db"

# Defaults (overridable via admin settings)
DEFAULT_PROMO_CODE = "КОНТРАБАНДА1"
DEFAULT_PROMO_DISCOUNT = 5  # percent
DEFAULT_PAYMENT_DETAILS = (
    "💳 Реквизиты для оплаты:\n"
    "Номер карты: 0000 0000 0000 0000\n"
    "СБП: +7 (999) 000-00-00\n"
    "Получатель: Сырком\n"
    "Назначение: Оплата заказа №{order_id}"
)

# Rate limiting for broadcasts (messages per second)
BROADCAST_RATE_LIMIT = 30

# Company info
COMPANY_NAME = "Сырком"

COMPANY_TEXT = (
    "🧀 <b>Сырком</b>\n\n"
    "Привозим лучшие твёрдые и выдержанные сыры со всего мира 🌍\n"
    "— о вкусе времени, традициях и редких сортах\n"
    "— новости, акции и доставка гурманских находок прямо к вам\n\n"
    "📢 Подписывайтесь на наш канал: <a href=\"https://t.me/cheessecom\">@cheessecom</a>"
)

PROMO_TEXT = (
    "🎉 Кстати, на первый заказ через бот действует промокод "
    f"<b>{DEFAULT_PROMO_CODE}</b>, который даёт скидку {DEFAULT_PROMO_DISCOUNT}%. "
    "Действует на всё, кроме наборов.\n\n"
    "Просто введите его в комментариях при оформлении заказа "
    "в разделе «Наш каталог».\n\n"
    "📋 Главное меню открыто. Вы можете оформить заказ по кнопке ниже."
)
