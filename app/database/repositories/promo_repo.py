from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database.models import Promo, PromoUsers
from app.utils.consts import MSK_TIMEZONE

class PromoRepo:

    
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_promo(self, promocode: str) -> Promo | None:

        promo = await self.session.scalar(select(Promo).filter_by(promocode=promocode))

        # Проверяем, что промокод не истёк
        if promo and promo.expire_at < datetime.now(MSK_TIMEZONE):
            return None  # Промокод истёк

        return promo  # Промокод действующий

    async def create_promo(self, promocode: str, reward: int, days_until_expire: int) -> Promo | None:
        """Создаёт новый промокод"""
        from app.utils import MSK_TIMEZONE
        from datetime import datetime, timedelta

        try:
            # Проверяем, что промокод с таким кодом не существует
            existing_promo = await self.get_promo(promocode)
            if existing_promo:
                return None  # Промокод с таким кодом уже существует

            # Вычисляем дату истечения
            expire_at = datetime.now(MSK_TIMEZONE) + timedelta(days=days_until_expire)

            # Создаём промокод
            promo = Promo(
                promocode=promocode,
                reward=reward,
                expire_at=expire_at
            )

            self.session.add(promo)
            await self.session.commit()

            return promo

        except Exception as exc:
            logger.exception(f"Ошибка при создании промокода: {exc}")
            return None