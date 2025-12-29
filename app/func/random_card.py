import random

from sqlalchemy import select

from db.models import Card
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
RARITIES = [1,2,3,4,5]
CHANCES = [55,27,12,4.5,1]

SHINY_CHANCE = 0.05


async def random_card(session:AsyncSession,pity:int):
    # Выбор редкости: если есть `pity` — используем веса, иначе выдаём самую обычную редкость (1)
    random_rarity = random.choices(RARITIES, CHANCES, k=1)[0] if pity > 0 else 1
    # Определяем, выпала ли shiny-версия
    is_shiny = random.random() < SHINY_CHANCE

    logger.info(f"Выбор карты: rarity={random_rarity}, shiny={is_shiny}, pity={pity}")

    cards_result = await session.scalars(
        select(Card).where(
            Card.shiny == is_shiny,
            Card.can_drop == True,
            Card.rarity.has(id=random_rarity),
        )
    )
    cards = cards_result.all()
    chosen = random.choice(cards)
    logger.info(f"Выдана карта id={getattr(chosen, 'id', None)} name={getattr(chosen, 'name', None)} shiny={chosen.shiny}")
    return chosen