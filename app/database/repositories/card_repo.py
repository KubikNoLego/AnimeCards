import random

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.database.models import Card, Verse, Rarity
# Импортируем random_card внутри метода, чтобы избежать циклической зависимости

class CardRepo:

    
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_random_verse(self) -> Verse:
        """Возвращает случайную вселенную, в которой есть хотя бы одна карта, которая может выпадать"""
        try:
            valid_verse_names_subquery = (
                select(Card.verse_name)
                .where(Card.can_drop == True)
                .distinct()
            )
            
            verses = await self.session.scalars(
                select(Verse).where(Verse.name.in_(valid_verse_names_subquery))
            )
            verses = verses.all()

            if not verses:
                logger.warning("Нет доступных вселенных в базе данных")
                return None

            return random.choice(verses)
        except Exception as exc:
            logger.exception(f"Ошибка при получении случайной вселенной: {exc}")
            return None
    
    async def get_verse(self, verse_id: int) -> Verse | None:
        """Возвращает вселенную по ID"""
        try:
            return await self.session.scalar(select(Verse).filter_by(id=verse_id))
        except Exception as exc:
            logger.exception(f"Ошибка при получении вселенной id={verse_id}: {exc}")
            return None
        
    async def get_card(self, card_id: int):
        try:
            return await self.session.scalar(select(Card).filter_by(
                id=card_id))
        except Exception as exc:
            logger.exception(f"Ошибка получения карты: {exc}")
            return None

    async def get_daily_shop_items(self) -> list[Card]:
        """Возвращает карточки для магазина"""
        # Импортируем внутри метода, чтобы избежать циклической зависимости
        from app.services.random_card import random_card
        
        try:
            daily_cards = []
            attempts = 0
            max_attempts = 100

            while len(daily_cards) < 4 and attempts < max_attempts:
                attempts += 1
                try:
                    card = await random_card(self.session, pity=100)

                    # Проверяем, что карта не является shiny, не имеет редкость 6 (Лимитированный) и уникальна
                    if not card.shiny and card.rarity.id != 6 and not any(c.id == card.id for c in daily_cards):
                        daily_cards.append(card)
                except Exception as e:
                    logger.warning(
                        f"Не удалось сгенерировать карточку (попытка {attempts}): {str(e)}")
                    continue

            if len(daily_cards) >= 4:
                return daily_cards
            else:
                logger.warning(
                    f"Не удалось получить достаточно карточек после {attempts} попыток, используем резервный метод")

                # Резервный метод: случайный выбор, если random_card не сработал
                # Гарантированно выбираем только не-shiny карты и исключаем редкость 6 (Лимитированный)
                cards = await self.session.scalars(
                    select(Card)
                    .filter(Card.shiny == False, Card.rarity.id != 6)
                )
                cards = cards.all()

                if len(cards) >= 4:
                    # Используем множество для отслеживания уникальных карт
                    unique_cards = []
                    used_ids = set()
                    for card in cards:
                        if card.id not in used_ids:
                            unique_cards.append(card)
                            used_ids.add(card.id)
                            if len(unique_cards) >= 4:
                                break
                    return unique_cards[:4]
                else:
                    logger.warning(
                        "Недостаточно карточек в базе данных для ежедневного магазина")
                    return []

        except Exception as exc:
            logger.exception(
                f"Ошибка при получении карточек для ежедневного магазина: {exc}")
            return []
