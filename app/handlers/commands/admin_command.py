from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards import admin_kb
from app.filters import Private


ADMIN_ID = 5027089008
router = Router()


@router.message(Command("admin"), Private())
async def admin_panel(message: Message, session: AsyncSession):
    """Главное меню админ-панели"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа к админ-панели")
        return
    
    await message.answer(
        "👋 <b>Добро пожаловать в админ-панель AnimeCards!</b>\n\n"
        "Выберите действие из меню ниже:",
        reply_markup=await admin_kb()
    )
