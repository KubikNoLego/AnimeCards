from aiogram import Router,F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.filters import Private
from app.keyboards import shop_keyboard
from app.messages import MText
from db import DB, RedisRequests, Card


router = Router()


@router.message(F.text == "🛒 Магазин",Private())
async def _(message:Message,session:AsyncSession):
    items = await RedisRequests.daily_items()
    db = DB(session)
    user = await db.get_user(message.from_user.id)
    if items:
        try:
            items = items.decode("utf-8").split(",")
            cards = []

            for item_id in items:
                if item_id.strip():  # Проверяем, что ID не пустой
                    card = await session.scalar(select(Card).filter_by(id=
                                                        int(item_id.strip())))
                    if card:
                        # Применяем 70% надбавку к цене карточки
                        card.value = int(card.value * 1.7)
                        cards.append(card)

            if cards:
                # Создаем клавиатуру с товарами
                keyboard = await shop_keyboard(cards if user.vip else cards[0:3])
                await message.answer(MText.get("daily_shop"), reply_markup=keyboard)
            else:
                await message.answer(MText.get("shop_empty"))
        except Exception as e:
            logger.error(f"Ошибка при обработке магазина: {str(e)}", exc_info=True)
            await message.answer(MText.get("shop_empty"))
    else:
        await message.answer(MText.get("shop_empty"))