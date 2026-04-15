from datetime import datetime, timedelta
import math
import random

from aiogram.types import FSInputFile
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.random_card import roll_rarity, choose_card

from ..utils.consts import(SHINY_CHANCE, MSK_TIMEZONE, COOLDOWN)
from ..utils.enums.open_card_enums import CardOpen
from app.database import User, DB, Card, Clan, RedisRequests, Rarity


@logger.catch()
async def random_hrono(session: AsyncSession):

    cards_result = await session.scalars(
        select(Card).join(Rarity).where(
            Card.shiny == False,
            Card.can_drop == True,
            Rarity.id == 5, 
        )
    )
    cards = cards_result.all()

    daily_verse = await RedisRequests.daily_verse()

    return choose_card(cards,daily_verse)

@logger.catch()
async def random_card(session: AsyncSession, pity: int, user_id: int):
    """Выбрать случайную карту"""

    boost = True if await RedisRequests().luck_boosts(user_id) else False

    random_rarity = roll_rarity(pity, boost)
    is_shiny = random.random() < SHINY_CHANCE

    daily_verse_task = RedisRequests.daily_verse()

    cards_result = await session.scalars(
        select(Card).join(Rarity).where(
            Card.shiny == is_shiny,
            Card.can_drop == True,
            Rarity.id == random_rarity, 
        )
    )
    cards = cards_result.all()

    if not cards:
        raise ValueError(
        f"Нет доступных карт с редкостью {random_rarity} и shiny={is_shiny}"
        )

    daily_verse = await daily_verse_task

    return choose_card(cards,daily_verse)

@logger.catch()
async def open_card(session: AsyncSession, user_id):
    """Открывает случайную карту для пользователя."""
    try:
        db = DB(session)
        
        user = await db.user.get_user(user_id)
        if not user:
            return CardOpen.NOT_REGISTERED
        
        now = datetime.now(MSK_TIMEZONE)
        last_open = (user.last_open.astimezone(MSK_TIMEZONE) if 
                        user.last_open.tzinfo is None else user.last_open)
        cooldown_hours = COOLDOWN - (1 if now.weekday() >= 5 else 0)
        
        if not (user.free_open or last_open + timedelta(hours=cooldown_hours)
                                                                <= now):
            return CardOpen.NOT_TIME
        
        card = await random_card(session, user.pity, user.id)
        if card not in user.inventory:
            user.inventory.append(card)
        
        if card.rarity.id == 5: user.pity = 0
        else: user.pity = user.pity + 1 if user.pity < 100 else 0
        
        bonus = int(card.value * 0.1) if user.vip else 0
        daily_bonus = (int(card.value * 0.2) if (card.verse.id ==
                                        await RedisRequests.daily_verse())
                                        else 0)
        yens_boost = int(card.value * 0.3) if await RedisRequests().yens_boosts(user.id) > 0 else 0


        added_sum = card.value + bonus + daily_bonus + yens_boost
        user.balance += added_sum
        
        await RedisRequests().remove_yens_boost(user.id)

        if user.clan_member:
            clan_bonus = int(added_sum * 0.3)
            user.clan_member.contribution += clan_bonus
            user.clan_member.clan.balance += clan_bonus
        
        await RedisRequests().remove_luck_boost(user.id)
        await session.commit()

        logger.info("Получена карта {id} для {user_id}", user_id=user_id, id=card.id)
        return card
    
    except Exception as e:
        logger.exception("Ошибка при открытии карт {id}: {error}", id=user_id, error=str(e))
        return CardOpen.ERROR
