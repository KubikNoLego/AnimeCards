from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from db.models import Profile, User

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

    async def create_or_update_user(self, id: int,
                                    username: str | None,
                                    name: str,
                                    describe: str):
        """Создаёт пользователя, если нет, иначе обновляет поля."""
        from app.func import MSK_TIMEZONE
        now = datetime.now(MSK_TIMEZONE)
        try:
            user = await self.get_user(id)
            if user is None:
                user = User(
                    id=id,
                    username=username,
                    name=name,
                    last_open=now - timedelta(hours=3),
                )
                user.profile = Profile(user_id=id, describe=describe, joined=now)
                self.session.add(user)
                action = True
            else:
                user.username = username
                user.name = name
                action = False
            await self.session.commit()
            return (user, action) # возвращает пользователя и True если он создан, False - обновлён
        except Exception as exc:
            logger.exception(f"Ошибка при сохранении пользователя id={id}: {exc}")
            return None
    
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