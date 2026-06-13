import asyncio
import time
from collections import Counter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database.models import Banner, CardType, User, Card
from app.utils.multiopen_utils import generate_cards_image
from app.services.GachaService import GachaService, LuckService

class Message:
    class from_user:
        id = 8494031501

async def main():
    DATABASE_URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/animecards"

    engine = create_async_engine(DATABASE_URL)

    Session = async_sessionmaker(
    engine,
    expire_on_commit=False)

    cards_standart = [0,0,0,0,0]
    verse_count1 = 0
    verse_cards = []
    season_cards_count = 0
    season_cards = Counter()
    cards_season = [0,0,0,0,0]
    season_cards_count_1 = 0
    season_cards_1 = Counter()
    verse_cards_1 = []
    verse_count2 = 0

    async with Session() as session:
        
        ...

asyncio.run(main())
