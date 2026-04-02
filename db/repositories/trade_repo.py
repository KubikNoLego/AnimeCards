from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from db.models import Trade, User, Card

class TradeRepo:

    
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_trade(self, user_id:int, card_id:int):
        trade = Trade(user_id=user_id,card_id=card_id)

        self.session.add(trade)
        await self.session.commit()

        return trade

    async def get_trade(self,user_id:int) -> Trade | None:
        return await self.session.scalar(select(Trade).filter_by(
                            user_id=user_id))

    async def delete_trade(self, user_id: int):
        await self.session.delete(await self.get_trade(user_id))
        await self.session.commit()
    
    async def complete_trade(self, trade: Trade):
        try:
            user1 = await self.session.scalar(select(User).filter_by(id=trade.user_id))
            user2 = await self.session.scalar(select(User).filter_by(id=trade.partner_id))
            
            card1 = await self.session.scalar(select(Card).filter_by(id=trade.card_id))
            card2 = await self.session.scalar(select(Card).filter_by(id=trade.partner_card))

            # Проверяем, что обе карты существуют
            if not card1 or not card2:
                return False

            # Проверяем, что карты есть в инвентаре пользователей
            if card1 not in user1.inventory or card2 not in user2.inventory:
                return False

            # Удаляем карты из инвентаря
            user1.inventory.remove(card1)
            user2.inventory.remove(card2)
            
            # Добавляем карты в инвентарь
            user1.inventory.append(card2)
            user2.inventory.append(card1)

            try:
                await self.session.commit()
            except IntegrityError:
                await self.session.rollback()
                return False
            await self.delete_trade(trade.user_id)
            return True

        except Exception as exc:
            logger.exception(f"Ошибка при завершении трейда: {exc}")
            return False
