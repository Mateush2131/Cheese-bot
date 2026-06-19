from aiogram import F, Router
from aiogram.types import Message

from config import COMPANY_TEXT
from keyboards import catalog_webapp_kb, channel_kb

router = Router()


@router.message(F.text == "О компании")
async def about_company(message: Message):
    await message.answer(
        COMPANY_TEXT,
        reply_markup=channel_kb(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@router.message(F.text == "Сделать заказ")
async def make_order(message: Message):
    await message.answer(
        "По кнопке ниже вы можете ознакомиться с каталогом:",
        reply_markup=catalog_webapp_kb(),
    )
