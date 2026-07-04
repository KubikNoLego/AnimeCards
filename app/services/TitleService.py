import random
from datetime import datetime
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Title, Rarity, User, UserTitle
from app.database import DB
from app.utils.constants import TITLE_SPIN_PRICE


class TitleService:

    
    def format_buffs(title: Title) -> str:
        mapping = {
            'yen_boost': '💰 +{}% к йенам',
            'luck_boost': '🍀 +{}% к удаче',
            'time_skip': '⏳ -{} мин к кулдауну'
        }

        ordered = []
        for buff_key, buff_value in title.buffs.items():
            if buff_key in mapping:
                ordered.append(mapping[buff_key].format(buff_value))

        return '\n'.join(ordered)

    @classmethod
    async def random_title(cls, session: AsyncSession, user: User) -> Title:
        try:
            titles_result = await session.scalars(
                select(Title).join(Rarity).where(Title.droppable==True)
            )
            titles = titles_result.all()

            if not titles:
                logger.error("Нет доступных титулов в базе данных")
                raise SyntaxError("Не найдено титулов в БД")

            weights = []
            for title in titles:
                weights.append(title.rarity.drop_rate)

            selected_title = random.choices(titles, weights=weights, k=1)[0]

            logger.info(f"Пользователь ({user.id}) получил титул: {selected_title.title}")
            return selected_title

        except Exception as e:
            logger.exception(f"Ошибка при выборе случайного титула: {e}")
            raise ValueError("❌ Ошибка при открытии титула. Обратитесь в поддержку")

    @classmethod
    async def open_title(cls, session: AsyncSession, user_id: int) -> Title:
        db = DB(session)
        user = await db.user.get_user(user_id)

        if not user:
            raise ValueError("❌ Вы не зарегистрированы")

        if user.balance < TITLE_SPIN_PRICE:
            raise ValueError(f"❌ Недостаточно йен (нужно {TITLE_SPIN_PRICE} ¥)")

        try:
            user.balance -= TITLE_SPIN_PRICE

            title = await cls.random_title(session, user)

            if title not in user.unlocked_titles:
                user_title = UserTitle(user_id=user.id, title_id=title.id)
                session.add(user_title)
            user.profile.title_id = title.id

            await session.commit()

            logger.success(f"Пользователь {user_id} выбил титул: {title.title}")
            return title

        except Exception as e:
            logger.exception(f"Ошибка при открытии титула для пользователя ({user_id}): {e}")
            await session.rollback()
            raise ValueError("❌ Ошибка при открытии титула. Обратитесь в поддержку")

    @classmethod
    async def update_user_title(cls, session: AsyncSession,user_id: int, 
                                title_id: int):
        user = await DB(session).user.get_user(user_id)

        has_title = any([title.id == title_id for title in user.unlocked_titles])

        if not has_title:
            raise ValueError("У вас отсутствует этот титул")
        
        user.profile.title_id = title_id

        logger.info(f"Пользователь ({user.id}) установил титул ({title_id})")
        await session.commit()