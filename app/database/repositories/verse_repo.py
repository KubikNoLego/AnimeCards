from loguru import logger

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, exists

from app.database.models import Verse, Card, Banner, Season
from app.database.repositories.season_repo import SeasonRepo

class VerseRepo:
    

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

            if last_daily_verse is not None:
                last_daily_verse.daily = False

            # Находим текущий активный сезон, чтобы исключить его вселенную
            current_season = await SeasonRepo(self.session).get_active_season()
            season_banner_verse_id = None

            # Если есть активный сезон, получаем его баннер и вселенную
            if current_season is not None:
                season_banner = await self.session.get(Banner, current_season.banner_id)
                if season_banner is not None:
                    season_banner_verse_id = season_banner.verse_id

            # Формируем запрос с исключением вселенной из сезонного баннера
            # и проверкой наличия карт всех редкостей 1-5
            base_query = (
                select(Verse).where(
                    exists().where((Card.verse_id == Verse.id)
                        & (Card.droppable == True) & (Verse.daily == False)),
                    # Проверяем, что во вселенной есть карты всех редкостей 1-5
                    exists().where((Card.verse_id == Verse.id) & (Card.rarity_id == 1)),
                    exists().where((Card.verse_id == Verse.id) & (Card.rarity_id == 2)),
                    exists().where((Card.verse_id == Verse.id) & (Card.rarity_id == 3)),
                    exists().where((Card.verse_id == Verse.id) & (Card.rarity_id == 4)),
                    exists().where((Card.verse_id == Verse.id) & (Card.rarity_id == 5))
                )
            )

            # Добавляем условие исключения вселенной из сезонного баннера
            if season_banner_verse_id is not None:
                base_query = base_query.where(Verse.id != season_banner_verse_id)

            stmt = base_query.order_by(func.random()).limit(1)

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