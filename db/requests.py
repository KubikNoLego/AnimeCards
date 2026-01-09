# Стандартные библиотеки
import random
from datetime import datetime, timedelta, timezone

# Сторонние библиотеки
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Локальные импорты
from db.models import Card, User, Profile, Verse, Referrals

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
        # logger.info(f"Пользователь id={id} {action} username={username}")
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
    # logger.info(f"Пользователь id={getattr(user, 'id', None)} занимает место: {place}")
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

        # logger.info(f"Пользователь id={getattr(user, 'id', None)} имеет {collections} собранных коллекций")
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
        # logger.info(f"Получено {len(top_players)} игроков в топе по балансу")
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
            # logger.info(f"Получена случайная вселенная: {random_verse.id}")
            return random_verse
        logger.warning("Нет доступных вселенных в базе данных")
        return None
    except Exception as exc:
        logger.exception(f"Ошибка при получении случайной вселенной: {exc}")
        return None

async def get_daily_shop_items(session: AsyncSession) -> list[Card]:
    """Возвращает список карточек для ежедневного магазина с использованием системы вероятностей.

    Args:
        session: Асинхронная сессия базы данных

    Returns:
        Список карточек для ежедневного магазина или пустой список в случае ошибки
    """
    try:
        # Локальный импорт для избежания циклических зависимостей
        from app.func import random_card

        # Используем random_card для генерации карточек с учетом вероятностей
        # Используем фиксированное значение pity=100 для магазина (максимальный шанс)
        daily_cards = []
        attempts = 0
        max_attempts = 100

        while len(daily_cards) < 6 and attempts < max_attempts:
            attempts += 1
            try:
                card = await random_card(session, pity=100)  # Используем максимальный pity для лучших шансов

                # Проверяем, что карта не является shiny (для магазина shiny карты не подходят)
                if not card.shiny and card not in daily_cards:
                    daily_cards.append(card)
            except Exception as e:
                logger.warning(f"Не удалось сгенерировать карточку (попытка {attempts}): {str(e)}")
                continue

        if len(daily_cards) >= 6:
            # logger.info(f"Получено {len(daily_cards)} карточек для ежедневного магазина с использованием random_card")
            return daily_cards
        else:
            logger.warning(f"Не удалось получить достаточно карточек после {attempts} попыток, используем резервный метод")

            # Резервный метод: случайный выбор, если random_card не сработал
            # Гарантированно выбираем только не-shiny карты
            cards = await session.scalars(select(Card).filter_by(shiny=False))
            cards = cards.all()

            if len(cards) >= 6:
                daily_cards = random.sample(cards, 6)
                # logger.info(f"Получено {len(daily_cards)} карточек для ежедневного магазина (резервный метод)")
                return daily_cards
            else:
                logger.warning("Недостаточно карточек в базе данных для ежедневного магазина")
                return []

    except Exception as exc:
        logger.exception(f"Ошибка при получении карточек для ежедневного магазина: {exc}")
        return []

async def add_referral(session:AsyncSession, referral_id: int, referrer_id: int) -> bool:
    if referral_id != referrer_id:
        referrer = await session.scalar(select(User).filter_by(id=referrer_id))
        if referral_id not in referrer.referrals:
                refferal_alredy = await session.scalar(select(Referrals).filter_by(referral_id=referral_id))
                if refferal_alredy:
                    referral_object = Referrals(
                        user_id=referrer_id,
                        referral_id = referral_id
                    )
                    session.add(referral_object)
                    session.commit()
                    return referral_object
    return None

async def get_award(session:AsyncSession, referral_object:Referrals ,award:int):
    try:
        user = await session.scalar(select(User).filter_by(id=referral_object.user_id))
        user.yens+=award
        referral_object.referrer_reward = award
        await session.commit()
    except:
        pass

class RedisRequests:
    
    
    async def daily_verse() -> int:
        session = Redis()
        verse = await session.get('daily_verse')
        await session.aclose()
        if verse:
            return int(verse.decode('utf-8'))
        return None

    async def daily_items() -> str:
        session = Redis()
        items = await session.get('shop_items') or None
        await session.aclose()
        return items
