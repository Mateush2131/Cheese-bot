from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import database as db
from config import COMPANY_NAME, PROMO_TEXT
from keyboards import client_type_kb, main_menu_kb

router = Router()


class Onboarding(StatesGroup):
    city = State()
    client_type = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    db.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    user = db.get_user_by_telegram_id(message.from_user.id)
    if user and user.get("city") and user.get("is_client"):
        await message.answer(
            f"С возвращением в <b>{COMPANY_NAME}</b>, "
            f"{message.from_user.first_name or 'друг'}! 🧀\n"
            "Выберите действие в меню:",
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
        return

    await message.answer(
        "🤖 Приветствуем вас в нашем боте!\n"
        "Перед тем, как открыть главное меню, ответьте, пожалуйста, "
        "на несколько вопросов!\n\n"
        "📍 <b>Из какого вы города?</b>",
        parse_mode="HTML",
    )
    await state.set_state(Onboarding.city)


@router.message(Onboarding.city)
async def process_city(message: Message, state: FSMContext):
    city = message.text.strip()
    if len(city) < 2:
        await message.answer("Пожалуйста, введите название города:")
        return
    db.update_user(message.from_user.id, city=city)
    await message.answer(
        "✅ Спасибо за ответ!\n\n"
        "❓ И второй вопрос: вы уже являетесь нашим клиентом "
        "или только планируете сделать первый заказ?",
        reply_markup=client_type_kb(),
        parse_mode="HTML",
    )
    await state.set_state(Onboarding.client_type)


@router.callback_query(F.data.startswith("client:"), Onboarding.client_type)
async def process_client_type(callback: CallbackQuery, state: FSMContext):
    is_client = callback.data.split(":")[1]
    db.update_user(
        callback.from_user.id,
        is_client="yes" if is_client == "yes" else "no",
    )
    await callback.message.edit_reply_markup(reply_markup=None)

    if is_client == "no":
        await callback.message.answer(PROMO_TEXT, parse_mode="HTML")
    else:
        await callback.message.answer(
            "📋 Главное меню открыто. Вы можете оформить заказ по кнопке ниже.",
        )

    await callback.message.answer(
        "Выберите действие 👇",
        reply_markup=main_menu_kb(),
    )
    await state.clear()
    await callback.answer()
