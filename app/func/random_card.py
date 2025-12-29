import random

from sqlalchemy import select

from db.models import Card
from sqlalchemy.ext.asyncio import AsyncSession
RARITIES = [1,2,3,4,5]
CHANCES = [55,27,12,4.5,1]

SHINY_CHANCE = 0.05


async def random_card(session:AsyncSession,pity:int):
    random_rarity = random.choices(RARITIES,CHANCES,k=1)[0] if pity > 0 else 1
    is_shiny = random.random() < SHINY_CHANCE
    cards_result = await session.scalars(select(Card).where(Card.shiny == is_shiny,Card.can_drop == True, Card.rarity.has(id = random_rarity ) ))
    cards = cards_result.all()
    return random.choice(cards)