from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from config import TELEGRAM_CHANNEL_URL, WEBAPP_URL


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="О компании"), KeyboardButton(text="Сделать заказ")],
            [KeyboardButton(text="Оставить отзыв")],
        ],
        resize_keyboard=True,
    )


def client_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Уже клиент", callback_data="client:yes"),
                InlineKeyboardButton(text="Планирую первый заказ", callback_data="client:no"),
            ]
        ]
    )


def catalog_webapp_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛍️ Открыть каталог",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        ]
    )


def channel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Наш Telegram-канал", url=TELEGRAM_CHANNEL_URL)]
        ]
    )


def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
            [InlineKeyboardButton(text="📦 Заказы", callback_data="admin:orders")],
            [InlineKeyboardButton(text="⭐ Отзывы", callback_data="admin:reviews")],
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users")],
            [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin:broadcast")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin:settings")],
        ]
    )


def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin:back")]
        ]
    )


def admin_orders_kb(orders: list) -> InlineKeyboardMarkup:
    buttons = []
    for o in orders[:20]:
        status_icon = {
            "new": "🆕",
            "processing": "⏳",
            "shipped": "🚚",
            "delivered": "✅",
            "cancelled": "❌",
        }.get(o["status"], "❓")
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{status_icon} #{o['id']} — {o['total']:.0f} ₽",
                    callback_data=f"admin:order:{o['id']}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_order_status_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🆕 Новый", callback_data=f"admin:status:{order_id}:new"
                ),
                InlineKeyboardButton(
                    text="⏳ В обработке", callback_data=f"admin:status:{order_id}:processing"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🚚 Отправлен", callback_data=f"admin:status:{order_id}:shipped"
                ),
                InlineKeyboardButton(
                    text="✅ Доставлен", callback_data=f"admin:status:{order_id}:delivered"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменён", callback_data=f"admin:status:{order_id}:cancelled"
                ),
            ],
            [InlineKeyboardButton(text="◀️ К заказам", callback_data="admin:orders")],
        ]
    )


def admin_reviews_kb(reviews: list) -> InlineKeyboardMarkup:
    buttons = []
    for r in reviews[:20]:
        preview = r["text"][:30] + "..." if len(r["text"]) > 30 else r["text"]
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"#{r['id']} {r['author_name']}: {preview}",
                    callback_data=f"admin:review:{r['id']}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_review_reply_kb(review_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Ответить", callback_data=f"admin:reply:{review_id}"
                )
            ],
            [InlineKeyboardButton(text="◀️ К отзывам", callback_data="admin:reviews")],
        ]
    )


def admin_settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎁 Промокод", callback_data="admin:set:promo_code"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 Скидка (%)", callback_data="admin:set:promo_discount"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💳 Реквизиты", callback_data="admin:set:payment_details"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Добавить админа", callback_data="admin:set:add_admin"
                )
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin:back")],
        ]
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )
