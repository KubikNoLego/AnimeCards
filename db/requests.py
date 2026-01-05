from loguru import logger
from db.models import User, Profile

from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

async def create_or_update_user(id: int,
                                username: str | None,
                                name: str,
                                describe: str,
                                session: AsyncSession):
    """Создаёт пользователя, если нет, иначе обновляет поля.

    Лёгкое упрощение: используем одну метку времени `now` для полей.
    """
    now = datetime.now(timezone.utc)
    try:
        user = await session.scalar(select(User).filter_by(id=id))
        if user is None:
            user = User(
                id=id,
                username=username,
                name=name,
                # локальная корректировка времени:
                last_open=now - timedelta(hours=3),
                joined=now,
            )
            user.profile = Profile(user_id=id, describe=describe)
            session.add(user)
            action = "создан"
        else:
            user.username = username
            user.name = name
            action = "обновлён"

        await session.commit()
        logger.info(f"Пользователь id={id} {action} username={username}")
        return user
    except Exception as exc:
        # Логируем исключение с трассировкой на русском
        logger.exception(f"Ошибка при сохранении пользователя id={id}: {exc}")


async def get_user_place_on_top(session: AsyncSession, user: User):
    """Возвращает место пользователя в топе по `yens` (1 — наилучшее)."""
    stmt = select(func.count(User.id)).where(User.yens > user.yens)
    result = await session.execute(stmt)
    count_higher = result.scalar()

    place = (count_higher or 0) + 1
    logger.info(f"Пользователь id={getattr(user, 'id', None)} занимает место: {place}")
    return place