from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import database as db
from config import ADMIN_IDS, BROADCAST_RATE_LIMIT
from keyboards import (
    admin_back_kb,
    admin_main_kb,
    admin_order_status_kb,
    admin_orders_kb,
    admin_review_reply_kb,
    admin_reviews_kb,
    admin_settings_kb,
    cancel_kb,
    main_menu_kb,
)

router = Router()

ORDER_STATUS_LABELS = {
    "new": "🆕 Новый",
    "processing": "⏳ В обработке",
    "shipped": "🚚 Отправлен",
    "delivered": "✅ Доставлен",
    "cancelled": "❌ Отменён",
}


class AdminBroadcast(StatesGroup):
    text = State()


class AdminSetting(StatesGroup):
    value = State()


class AdminReply(StatesGroup):
    text = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS or user_id in db.get_admin_ids()


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    await message.answer(
        "🔐 <b>Админ-панель</b>\n\nВыберите раздел:",
        reply_markup=admin_main_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(
        "🔐 <b>Админ-панель</b>\n\nВыберите раздел:",
        reply_markup=admin_main_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    stats = db.get_stats()
    text = (
        "📊 <b>СТАТИСТИКА МАГАЗИНА</b>\n\n"
        f"👥 Всего пользователей: <b>{stats['users']}</b>\n"
        f"🆕 Новых за сегодня: <b>{stats['users_today']}</b>\n"
        f"📦 Всего заказов: <b>{stats['orders']}</b>\n"
        f"💰 Общая выручка: <b>{stats['revenue']:,.0f} ₽</b>\n"
        f"📈 Средний чек: <b>{stats['avg_check']:,.0f} ₽</b>\n"
        f"🔄 Конверсия (клиенты/все): <b>{stats['conversion']}%</b>\n\n"
        f"🕐 За неделю: <b>{stats['orders_week']}</b> заказов\n"
        f"🕐 За месяц: <b>{stats['orders_month']}</b> заказов\n"
        f"⭐ Отзывов: <b>{stats['reviews']}</b>"
    )
    await callback.message.edit_text(text, reply_markup=admin_back_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:orders")
async def admin_orders(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    orders = db.get_all_orders(limit=20)
    if not orders:
        await callback.message.edit_text(
            "📦 Заказов пока нет.", reply_markup=admin_back_kb()
        )
    else:
        await callback.message.edit_text(
            "📦 <b>Заказы</b> (последние 20):",
            reply_markup=admin_orders_kb(orders),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:order:"))
async def admin_order_detail(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    order_id = int(callback.data.split(":")[2])
    order = db.get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    items = db.get_order_items(order_id)
    items_text = "\n".join(
        f"  • {i['product_name']} × {i['quantity']} — {i['price'] * i['quantity']:.0f} ₽"
        for i in items
    )
    status = ORDER_STATUS_LABELS.get(order["status"], order["status"])
    text = (
        f"📦 <b>Заказ #{order_id}</b>\n\n"
        f"Статус: {status}\n"
        f"👤 {order['customer_name']}\n"
        f"📞 {order['phone']}\n"
        f"📍 {order['address']}\n"
        f"💬 {order['comment'] or '—'}\n"
        f"🎁 Промокод: {order['promo_code'] or '—'}\n\n"
        f"<b>Товары:</b>\n{items_text}\n\n"
        f"💰 <b>Итого: {order['total']:.0f} ₽</b>\n"
        f"📅 {order['created_at'][:19]}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=admin_order_status_kb(order_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:status:"))
async def admin_change_status(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    parts = callback.data.split(":")
    order_id = int(parts[2])
    new_status = parts[3]
    db.update_order_status(order_id, new_status)
    await callback.answer(f"Статус изменён: {ORDER_STATUS_LABELS.get(new_status, new_status)}")

    order = db.get_order(order_id)
    if order and new_status in ("processing", "shipped", "delivered", "cancelled"):
        status_msg = {
            "processing": "⏳ Ваш заказ принят в обработку.",
            "shipped": "🚚 Ваш заказ отправлен!",
            "delivered": "✅ Ваш заказ доставлен! Спасибо за покупку.",
            "cancelled": "❌ Ваш заказ был отменён. Свяжитесь с нами для уточнения.",
        }
        try:
            await bot.send_message(
                order["telegram_id"],
                f"📦 Заказ #{order_id}\n{status_msg[new_status]}",
            )
        except Exception:
            pass

    order = db.get_order(order_id)
    if order:
        items = db.get_order_items(order_id)
        items_text = "\n".join(
            f"  • {i['product_name']} × {i['quantity']} — {i['price'] * i['quantity']:.0f} ₽"
            for i in items
        )
        status = ORDER_STATUS_LABELS.get(order["status"], order["status"])
        text = (
            f"📦 <b>Заказ #{order_id}</b>\n\n"
            f"Статус: {status}\n"
            f"👤 {order['customer_name']}\n"
            f"📞 {order['phone']}\n"
            f"📍 {order['address']}\n"
            f"💬 {order['comment'] or '—'}\n"
            f"🎁 Промокод: {order['promo_code'] or '—'}\n\n"
            f"<b>Товары:</b>\n{items_text}\n\n"
            f"💰 <b>Итого: {order['total']:.0f} ₽</b>\n"
            f"📅 {order['created_at'][:19]}"
        )
        await callback.message.edit_text(
            text,
            reply_markup=admin_order_status_kb(order_id),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "admin:reviews")
async def admin_reviews(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    reviews = db.get_reviews(limit=20)
    if not reviews:
        await callback.message.edit_text(
            "⭐ Отзывов пока нет.", reply_markup=admin_back_kb()
        )
    else:
        await callback.message.edit_text(
            "⭐ <b>Отзывы</b>:", reply_markup=admin_reviews_kb(reviews), parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:review:"))
async def admin_review_detail(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    review_id = int(callback.data.split(":")[2])
    review = db.get_review(review_id)
    if not review:
        await callback.answer("Отзыв не найден", show_alert=True)
        return
    reply_text = f"\n\n💬 <b>Ответ:</b> {review['admin_reply']}" if review["admin_reply"] else ""
    text = (
        f"⭐ <b>Отзыв #{review_id}</b>\n\n"
        f"👤 {review['author_name']}\n"
        f"🆔 @{review['username'] or review['telegram_id']}\n\n"
        f"{review['text']}"
        f"{reply_text}\n\n"
        f"📅 {review['created_at'][:19]}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=admin_review_reply_kb(review_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:reply:"))
async def admin_start_reply(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    review_id = int(callback.data.split(":")[2])
    await state.update_data(review_id=review_id)
    await state.set_state(AdminReply.text)
    await callback.message.answer(
        "✍️ Введите ответ пользователю:", reply_markup=cancel_kb()
    )
    await callback.answer()


@router.message(AdminReply.text, F.text == "❌ Отмена")
async def cancel_admin_reply(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_kb())


@router.message(AdminReply.text)
async def process_admin_reply(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    review_id = data["review_id"]
    reply_text = message.text.strip()
    db.set_review_reply(review_id, reply_text)
    review = db.get_review(review_id)
    await message.answer("✅ Ответ сохранён и отправлен пользователю.", reply_markup=main_menu_kb())
    await state.clear()

    if review:
        try:
            await bot.send_message(
                review["telegram_id"],
                f"💬 Ответ на ваш отзыв:\n\n{reply_text}",
            )
        except Exception:
            pass


@router.callback_query(F.data == "admin:users")
async def admin_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    users = db.get_all_users(limit=30)
    lines = []
    for u in users:
        city = u.get("city") or "—"
        client = "✅" if u.get("is_client") == "yes" else "🆕"
        name = u.get("first_name") or u.get("username") or str(u["telegram_id"])
        lines.append(f"{client} {name} | {city}")
    text = "👥 <b>Пользователи</b> (последние 30):\n\n" + "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n..."
    await callback.message.edit_text(text, reply_markup=admin_back_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminBroadcast.text)
    await callback.message.answer(
        "📢 Введите текст рассылки для всех пользователей:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(AdminBroadcast.text, F.text == "❌ Отмена")
async def cancel_broadcast(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Рассылка отменена.", reply_markup=main_menu_kb())


@router.message(AdminBroadcast.text)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    text = message.text.strip()
    ids = db.get_all_telegram_ids()
    sent = 0
    failed = 0
    import asyncio

    for i, tg_id in enumerate(ids):
        try:
            await bot.send_message(tg_id, text)
            sent += 1
        except Exception:
            failed += 1
        if (i + 1) % BROADCAST_RATE_LIMIT == 0:
            await asyncio.sleep(1)

    await message.answer(
        f"📢 Рассылка завершена.\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}",
        reply_markup=main_menu_kb(),
    )
    await state.clear()


@router.callback_query(F.data == "admin:settings")
async def admin_settings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    promo = db.get_setting("promo_code")
    discount = db.get_setting("promo_discount")
    text = (
        "⚙️ <b>Настройки</b>\n\n"
        f"🎁 Промокод: <code>{promo}</code>\n"
        f"💰 Скидка: <code>{discount}%</code>\n"
        f"👤 Админы: {', '.join(str(a) for a in set(ADMIN_IDS + db.get_admin_ids()))}"
    )
    await callback.message.edit_text(
        text, reply_markup=admin_settings_kb(), parse_mode="HTML"
    )
    await callback.answer()


SETTING_LABELS = {
    "promo_code": "промокод",
    "promo_discount": "скидку в процентах",
    "payment_details": "реквизиты для оплаты",
    "add_admin": "Telegram ID нового админа",
}


@router.callback_query(F.data.startswith("admin:set:"))
async def admin_set_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    key = callback.data.split(":")[2]
    label = SETTING_LABELS.get(key, key)
    await state.update_data(setting_key=key)
    await state.set_state(AdminSetting.value)
    await callback.message.answer(
        f"✏️ Введите новое значение для: <b>{label}</b>",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminSetting.value, F.text == "❌ Отмена")
async def cancel_setting(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_kb())


@router.message(AdminSetting.value)
async def process_setting(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    key = data["setting_key"]
    value = message.text.strip()

    if key == "add_admin":
        if not value.isdigit():
            await message.answer("Введите числовой Telegram ID:")
            return
        db.add_admin_id(int(value))
        await message.answer(f"✅ Админ {value} добавлен.", reply_markup=main_menu_kb())
    elif key == "promo_discount":
        if not value.isdigit():
            await message.answer("Введите число (процент скидки):")
            return
        db.set_setting(key, value)
        await message.answer(f"✅ Скидка обновлена: {value}%", reply_markup=main_menu_kb())
    else:
        db.set_setting(key, value)
        await message.answer(f"✅ Настройка «{key}» обновлена.", reply_markup=main_menu_kb())

    await state.clear()
