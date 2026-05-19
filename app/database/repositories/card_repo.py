import random

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import exists, func, select
from loguru import logger

from app.database.models import Banner, Card, Verse
# Импортируем random_card внутри метода, чтобы избежать циклической зависимости

class CardRepo:

    
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_daily_verse(self) -> Verse | None:
        """Возвращает ежедневную вселенную"""

        try:
            verse = await self.session.scalar(select(Verse).where(Verse.daily == True))
            return verse
        except Exception as ex:
            logger.exception("Ошибка при получении ежедневной вселенной")
            return None

    async def update_daily_verse(self) -> Verse:
        """Обновляет ежедневную вселенную"""
        try:

            last_daily_verse = await self.session.scalar(select(Verse).where(
                Verse.daily == True
            ))

            last_daily_verse.daily = False
        
            stmt = (
                select(Verse).where(exists().where((Card.verse_id == Verse.id)
                    & (Card.droppable == True) & (Verse.daily == False)))
                    .order_by(func.random()).limit(1)
            )
            
            verse = await self.session.scalar(stmt)

            if verse is None:
                logger.warning("Нет доступных вселенных в базе данных")

            verse.daily = True

            banner = await self.session.scalar(select(Banner).where(Banner.id==1))
            banner.verse_id = verse.id

            await self.session.commit()

            return verse

        except Exception as exc:
            logger.exception(f"Ошибка при получении случайной вселенной")
            return None
    
    async def get_verse(self, verse_id: int) -> Verse | None:
        """Возвращает вселенную по ID"""
        try:
            return await self.session.scalar(select(Verse).filter_by(id=verse_id))
        except Exception as exc:
            logger.exception(f"Ошибка при получении вселенной id={verse_id}: {exc}")
            return None
        
    async def get_card(self, card_id: int):
        try:
            return await self.session.scalar(select(Card).filter_by(
                id=card_id))
        except Exception as exc:
            logger.exception(f"Ошибка получения карты: {exc}")
            return None