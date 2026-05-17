import random
from datetime import datetime
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Title, Rarity, User
from app.database import DB
from app.utils.consts import MSK_TIMEZONE
from app.utils.enums.title_enums import TitleOpen

async def random_title(session: AsyncSession, user: User) -> Title | TitleOpen:
    """
    Выбирает случайный титул для пользователя.

    Args:
        session: Асинхронная сессия базы данных
        user: Объект пользователя

    Returns:
        Случайный титул или TitleOpen.ERROR в случае ошибки
    """
    try:
        titles_result = await session.scalars(
            select(Title).join(Rarity).where(Title.droppable==True)
        )
        titles = titles_result.all()

        if not titles:
            logger.error("Нет доступных титулов в базе данных")
            return TitleOpen.ERROR

        weights = []
        for title in titles:
            if title.rarity.id == 1:
                weights.append(0.55)
            elif title.rarity.id == 2:
                weights.append(0.27)
            elif title.rarity.id == 3:
                weights.append(0.12)
            elif title.rarity.id == 4:
                weights.append(0.045)
            elif title.rarity.id == 5:
                weights.append(0.015)

        selected_title = random.choices(titles, weights=weights, k=1)[0]

        logger.success(f"Пользователь {user.id} получил титул: {selected_title.title}")
        return selected_title

    except Exception as e:
        logger.exception(f"Ошибка при выборе случайного титула: {e}")
        return TitleOpen.ERROR

async def open_title(session: AsyncSession, user_id: int) -> Title | TitleOpen:
    """
    Открывает случайный титул для пользователя за 250 йен.

    Args:
        session: Асинхронная сессия базы данных
        user_id: ID пользователя

    Returns:
        Полученный титул или код ошибки
    """
    try:
        db = DB(session)
        user = await db.user.get_user(user_id)

        if not user:
            return TitleOpen.NOT_REGISTERED

        if user.balance < 100:
            return TitleOpen.NOT_ENOUGH_YENS

        user.balance -= 100

        title = await random_title(session, user)

        if isinstance(title, TitleOpen):
            return title

        user.profile.title = title
        user.profile.title_id = title.id

        await session.commit()

        logger.success(f"Пользователь {user_id} открыл титул: {title.title}")
        return title

    except Exception as e:
        logger.exception(f"Ошибка при открытии титула для пользователя {user_id}: {e}")
        await session.rollback()
        return TitleOpen.ERROR
