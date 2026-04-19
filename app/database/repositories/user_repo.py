from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from loguru import logger

from app.database.models import Profile, User

class UserRepo:
    

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user(self,user_id: int) -> User | None:
        """Получает пользователя из БД, если он есть"""
        try:
            return await self.session.scalar(select(User)
                                            .filter_by(id=user_id))
        except Exception as exc:
            logger.exception(
                f"Ошибка при получении пользователя id={user_id}: {exc}")
            return None

    async def create_or_update_user(self, id: int, username: str | None,
                                    name: str,describe: str):
        from app.utils import MSK_TIMEZONE

        now = datetime.now(MSK_TIMEZONE)

        if not isinstance(id, int) or id < 0 or id > 2**63 - 1:
            raise ValueError(f"Invalid user id: {id}")

        try:
            stmt = insert(User).values(
                id=id,
                username=username,
                name=name,
                last_open=now - timedelta(hours=3)
            ).on_conflict_do_update(
                index_elements=[User.id],
                set_={
                    "username": username,
                    "name": name,
                    "last_open": now - timedelta(hours=3)
                }
            ).returning(User)

            result = await self.session.execute(stmt)
            user = result.scalar_one()

            profile_exists = await self.session.scalar(
                select(Profile.user_id).where(Profile.user_id == id)
            )

            if not profile_exists:
                profile_stmt = insert(Profile).values(
                    user_id=id,
                    describe=describe or '',
                    joined=now).on_conflict_do_nothing()

                await self.session.execute(profile_stmt)

            await self.session.commit()

            action = result.rowcount == 1

            return user, action

        except Exception as exc:
            await self.session.rollback()
            logger.exception(f"Ошибка создания пользователя: {exc}")
            return user, False
    
    async def get_user_place_on_top(self,user: User):
        """Возвращает место пользователя в топе по `yens` (1 — наилучшее)."""
        stmt = select(func.count(User.id)).where(User.balance > user.balance)
        result = await self.session.execute(stmt)
        count_higher = result.scalar()

        place = (count_higher or 0) + 1
        return place
    
    async def get_top_players_by_balance(self,
                                        limit: int = 10) -> list[User]:
        """Возвращает топ юзеров по балансу"""
        try:
            stmt = select(User).order_by(User.balance.desc()).limit(limit)
            result = await self.session.execute(stmt)
            top_players = result.scalars().all()
            return top_players
        except Exception as exc:
            logger.exception(f"Ошибка при получении топ игроков по балансу: {exc}")
            return []

    async def get_top_players_by_pvp_wins(self,
                                        limit: int = 10) -> list[User]:
        """Возвращает топ юзеров по количеству побед в PvP"""
        try:
            stmt = select(User).order_by(User.pvp_wins.desc()).limit(limit)
            result = await self.session.execute(stmt)
            top_players = result.scalars().all()
            return top_players
        except Exception as exc:
            logger.exception(f"Ошибка при получении топ игроков по победам PvP: {exc}")
            return []
