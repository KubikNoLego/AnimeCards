from datetime import datetime, timedelta
import math
import random

from aiogram.types import FSInputFile
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .consts import(RARITIES,SHINY_CHANCE,CHANCES, MSK_TIMEZONE,
        COOLDOWN
    )
from .Enums.open_card_enums import CardOpen
from db import User, DB, Card, Clan

@logger.catch()
async def random_card(session: AsyncSession, pity: int):
    """Выбрать случайную карту"""
    from db import Card, RedisRequests, Rarity

    random_rarity = random.choices(RARITIES, CHANCES, k=1)[0] if pity > 0 else 5
    # Определяем, выпала ли shiny-версия
    is_shiny = random.random() < SHINY_CHANCE

    # Оптимизация: получаем daily_verse параллельно с запросом к базе данных
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

    if daily_verse:
        boosted_cards = [card for card in cards if card.verse.id == daily_verse]
        normal_cards = [card for card in cards if card.verse.id != daily_verse]

        # Увеличиваем шанс на 25% для карт из ежедневной вселенной
        if boosted_cards:
            cards = random.choices(
                population=boosted_cards + normal_cards,
                weights=[1.25] * len(boosted_cards) + [1.0] * len(normal_cards),
                k=1
            )
            return cards[0]

    return random.choice(cards) if cards else None

async def open_card(session: AsyncSession, user_id):
    """
    Открывает случайную карту для пользователя.
    
    Args:
        session (AsyncSession): Асинхронная сессия базы данных
        user_id: Идентификатор пользователя
        
    Returns:
        int: Код результата операции
            0 - пользователь не найден
            1 - еще не прошло время для открытия карты
            2 - карта успешно открыта
            3 - произошла ошибка
    """
    try:
        db = DB(session)
        user = await db.get_user(user_id)
            
        if not user:
            return CardOpen.NOT_REGISTERED
        
        last_open = user.last_open

        if last_open.tzinfo is None:
            last_open = last_open.astimezone(MSK_TIMEZONE)
            
        hour = COOLDOWN-1 if datetime.now(MSK_TIMEZONE).weekday() >= 5 else COOLDOWN

        if ((last_open + timedelta(hours=hour) <= datetime.now(MSK_TIMEZONE))
                                                        or user.free_open):
            
            card = await random_card(session,user.pity)
            
            if card not in user.inventory:
                user.inventory.append(card)
            
            user.pity -= 1

            if user.pity < 0:
                user.pity = 100

            if user.free_open:
                user.free_open -= 1

            else:
                user.last_open = datetime.now(MSK_TIMEZONE)

            added_sum = int(card.value + (math.ceil(card.value * 0.1) 
                                        if user.vip else 0))
            
            user.balance += added_sum

            if user.clan_member:
                user.clan_member.contribution += int(added_sum*0.3)
                user.clan_member.clan.balance += int(added_sum*0.3)

            await session.commit()

            logger.info("Получена карта {id} для {user_id}", user_id = user_id, id = card.id)

            return card


        else:
            return CardOpen.NOT_TIME
    except Exception as e:
        logger.exception("Ошибка при открытии карт {id}: {error}", id=user_id, error=str(e))
        return CardOpen.ERROR
