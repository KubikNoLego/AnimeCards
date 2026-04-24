from aiogram import Router,F
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters import Private
from app.messages import MText
from app.database import DB
from app.utils.top_utils import top_players_by_balance_formatter, top_players_by_wins_formatter


router = Router()


@router.message(F.text == "🏆 Топ игроков", Private())
async def _(message: Message, session: AsyncSession):
    db = DB(session)
    user = await db.user.get_user(message.from_user.id)
    if user:
        top_players_balance = await db.user.get_top_players_by_balance(15
        )
        text_balance = await top_players_by_balance_formatter(top_players_balance,
                                                user.id)
        
        await message.answer(text_balance, disable_notification=True,
                            disable_web_page_preview=True)
    else:
        text = MText.get("not_user").format(name=message.from_user.full_name)
        await message.reply(text)

@router.message(Command("top"))
async def _(message: Message, session: AsyncSession):
    db = DB(session)
    user = await db.user.get_user(message.from_user.id)
    if user:
        top_players_balance = await db.user.get_top_players_by_balance(15)
        text_balance = await top_players_by_balance_formatter(top_players_balance,
                                                user.id)

        await message.answer(text_balance, disable_notification=True,
                            disable_web_page_preview=True)
    else:
        text = MText.get("not_user").format(name=message.from_user.full_name)
        await message.reply(text)


@router.message(Command("top_pvp"))
async def top_pvp_command(message: Message, session: AsyncSession):
    """Обработчик команды /top_pvp для отображения топа игроков по победам в PvP."""
    db = DB(session)
    user = await db.user.get_user(message.from_user.id)
    if user:
        # Получаем топ игроков по количеству побед в PvP
        top_players_pvp = await db.user.get_top_players_by_pvp_wins()
        
        # Используем общий форматтер как у топа по балансу
        text = await top_players_by_wins_formatter(top_players_pvp, user.id)
        
        await message.answer(text, disable_notification=True,
                            disable_web_page_preview=True)
    else:
        text = MText.get("not_user").format(name=message.from_user.full_name)
        await message.reply(text)
