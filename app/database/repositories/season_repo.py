from datetime import date

from loguru import logger

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import literal, select, func, exists

from app.database.models import Season, UserSeason


class SeasonRepo:
    

    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_active_season(self) -> Season | None:
        today = date.today()

        return await self.session.scalar(
            select(Season).where(
                Season.started_at <= today, 
                Season.ended_at >= today
            ))


    async def get_user_season(self, user_id: int) -> UserSeason:
        today = date.today()

        userseason = await self.session.scalar(
            select(UserSeason)
            .join(UserSeason.season)
            .where(
                UserSeason.user_id == user_id,
                Season.started_at <= today, 
                Season.ended_at >= today))

        if not userseason:
            return await self.create_user_season(user_id)
        return userseason


    async def create_user_season(self, user_id: int) -> UserSeason:
        season = await self.get_active_season()
        userseason = UserSeason(user_id = user_id, season_id = season.id)
        self.session.add(userseason)
        await self.session.commit()
        return userseason
