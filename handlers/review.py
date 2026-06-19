from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

import database as db
from config import ADMIN_IDS
from keyboards import cancel_kb, main_menu_kb

router = Router()


class ReviewForm(StatesGroup):
    name = State()
    text = State()


@router.message(F.text == "Оставить отзыв")
async def start_review(message: Message, state: FSMContext):
    await message.answer(
        "📝 1. Напишите ваше имя",
        reply_markup=cancel_kb(),
    )
    await state.set_state(ReviewForm.name)


@router.message(ReviewForm.name, F.text == "❌ Отмена")
@router.message(ReviewForm.text, F.text == "❌ Отмена")
async def cancel_review(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_kb())


@router.message(ReviewForm.name)
async def process_review_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Пожалуйста, введите ваше имя:")
        return
    await state.update_data(name=name)
    await message.answer("📝 2. Напишите ваш отзыв")
    await state.set_state(ReviewForm.text)


@router.message(ReviewForm.text)
async def process_review_text(message: Message, state: FSMContext, bot: Bot):
    text = message.text.strip()
    if len(text) < 5:
        await message.answer("Отзыв слишком короткий. Напишите чуть подробнее:")
        return

    data = await state.get_data()
    user = db.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    review_id = db.create_review(user["id"], data["name"], text)

    await message.answer(
        "🙏 Спасибо за ваш отзыв! Он уже ушёл напрямую директору компании.",
        reply_markup=main_menu_kb(),
    )
    await state.clear()

    admin_text = (
        f"⭐ <b>Новый отзыв #{review_id}</b>\n\n"
        f"👤 {data['name']}\n"
        f"🆔 @{message.from_user.username or message.from_user.id}\n\n"
        f"{text}"
    )
    for admin_id in set(ADMIN_IDS + db.get_admin_ids()):
        try:
            await bot.send_message(admin_id, admin_text, parse_mode="HTML")
        except Exception:
            pass
