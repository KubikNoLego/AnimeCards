from aiogram import Router,F
from aiogram.filters import Command
from aiogram.types import Message,CallbackQuery, FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.filters import Private
from app.keyboards import shop_keyboard, ShopItemCallback
from app.messages import MText
from app.database import DB, RedisRequests, Card, get_redis
from app.services.random_card import random_hrono
from app.services.shop import delete_item
from app.utils.card_formater import format_buyed_card
from app.utils.enums.shop import ShopEnum


router = Router()


@router.message(Command("daily"))
async def _(message: Message, session: AsyncSession):
    verse = await DB(session).card.get_verse(await RedisRequests(get_redis()).daily_verse())
    await message.reply(MText.get("daily_verse").format(verse=verse.name))