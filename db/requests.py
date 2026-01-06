import random
from loguru import logger
from redis.asyncio import Redis
from db.models import Card, User, Profile, Verse

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
    return place

async def get_user_collections_count(session: AsyncSession, user: User) -> int:
    """Возвращает количество полностью собранных коллекций (вселенных) пользователя.

    Коллекция считается собранной, если у пользователя есть все карты из данной вселенной.

    Args:
        session: Асинхронная сессия базы данных
        user: Объект пользователя

    Returns:
        Количество полностью собранных коллекций
    """
    try:
        from sqlalchemy.orm import selectinload

        # Загружаем пользователя с инвентарем, вселенными и картами вселенных
        user_with_data = await session.scalar(
            select(User)
            .filter_by(id=user.id)
            .options(
                selectinload(User.inventory).selectinload(Card.verse).selectinload(Verse.cards)
            )
        )

        collections = 0
        verses = []
        cards_id = []

        # Собираем все уникальные вселенные и ID карт из инвентаря пользователя
        for card in user_with_data.inventory:
            verses.append(card.verse)
            cards_id.append(card.id)

        # Убираем дубликаты вселенных
        verses = list(set(verses))

        # Для каждой вселенной проверяем, собрана ли она полностью
        for verse in verses:
            # Проверяем, есть ли у пользователя все карты этой вселенной
            if all(card.id in cards_id for card in verse.cards):
                collections += 1

        return collections
    except Exception as exc:
        logger.exception(f"Ошибка при подсчёте коллекций для пользователя id={getattr(user, 'id', None)}: {exc}")
        return 0

async def get_top_players_by_balance(session: AsyncSession, limit: int = 10) -> list[User]:
    """Возвращает топ игроков по балансу yens.

    Args:
        session: Асинхронная сессия базы данных
        limit: Максимальное количество игроков в топе (по умолчанию 10)

    Returns:
        Список пользователей, отсортированных по убыванию баланса
    """
    try:
        stmt = select(User).order_by(User.yens.desc()).limit(limit)
        result = await session.execute(stmt)
        top_players = result.scalars().all()
        return top_players
    except Exception as exc:
        logger.exception(f"Ошибка при получении топ игроков по балансу: {exc}")
        return []

async def get_random_verse(session: AsyncSession) -> Verse:
    """Возвращает случайную вселенную (verse) из базы данных.

    Args:
        session: Асинхронная сессия базы данных

    Returns:
        Случайный объект Verse или None в случае ошибки
    """
    try:
        verses = await session.scalars(select(Verse))
        verses = verses.all()
        if verses:
            random_verse = random.choice(verses)
            return random_verse
        return None
    except Exception as exc:
        logger.exception(f"Ошибка при получении случайной вселенной: {exc}")
        return None


class RedisRequests:
    async def daily_verse() -> int:
        session = Redis()
        verse = await session.get('verse') or None
        await session.aclose()
        return verse
