from datetime import date
import random

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.database.models import Banner, Card, Season

class CardRepo:

    
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def get_card(self, card_id: int):
        try:
            return await self.session.scalar(select(Card).filter_by(
                id=card_id))
        except Exception as exc:
            logger.exception(f"Ошибка получения карты: {exc}")
            return None
        
    async def get_banner(self, banner_id: int):
        try:
            return await self.session.scalar(select(Banner).where(
                                                    Banner.id == banner_id))
        except Exception as _ex:
            logger.exception(f"Ошибка при получении баннера: {_ex}")
            return None
    
    async def get_season_banner(self):
        try:
            from sqlalchemy.orm import joinedload
            season = await self.session.scalar(
                select(Season).where(
                    Season.started_at <= date.today(),
                    Season.ended_at >= date.today()
                ).options(joinedload(Season.banner))
            )
            return season.banner if season else None
        except Exception as _ex:
            logger.exception(f"Ошибка при получении баннера: {_ex}")
            return None
