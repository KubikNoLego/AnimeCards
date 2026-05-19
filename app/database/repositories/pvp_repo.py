from typing import Optional, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.models import User, BattleInventory, Card, PvPSearchQueue


class PVPRepo:


    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_battle_inventory(self, user: User) -> BattleInventory:
        
        battle_inventory = BattleInventory(user_id=user.id)
        
        self.session.add(battle_inventory)

        user.battle_inventory = battle_inventory

        await self.session.commit()

        return battle_inventory

    async def set_card_to_slot(self, user: User, card: Card, slot: str) -> Optional[BattleInventory]:
        
        if not user.battle_inventory:
            await self.create_battle_inventory(user)
        
        battle_inv = user.battle_inventory
        
        # Проверяем, что карта принадлежит пользователю
        if card not in user.inventory:
            return None
        
        # Словарь для сопоставления слотов и атрибутов
        slot_to_attr = {
            "common": "common_id",
            "uncommon": "uncommon_id",
            "mythic": "mythic_id",
            "legend": "legend_id",
            "hrono": "hrono_id"
        }
        
        if slot not in slot_to_attr:
            return None
        
        # Устанавливаем карту в слот
        setattr(battle_inv, slot_to_attr[slot], card.id)
        
        await self.session.commit()
        await self.session.refresh(battle_inv)
        
        return battle_inv

    async def get_battle_inventory(self, user_id: int) -> Optional[BattleInventory]:
        """Получить battle_inventory пользователя."""
        result = await self.session.execute(
            select(BattleInventory).where(BattleInventory.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def find_opponents(
        self, 
        user_id: int, 
        min_value: float, 
        max_value: float
    ) -> List[Tuple[User, BattleInventory, int]]:
        """
        Найти соперников с стоимостью колоды в диапазоне [min_value, max_value].
        Возвращает список кортежей (User, BattleInventory, total_value).
        """
        # Находим всех пользователей с battle_inventory, у которых стоимость колоды в диапазоне
        # Нам нужно вычислить стоимость каждой колоды
        result = await self.session.execute(
            select(BattleInventory).where(
                BattleInventory.user_id != user_id
            )
        )
        battle_inventories = result.scalars().all()
        
        opponents = []
        for battle_inv in battle_inventories:
            # Вычисляем стоимость колоды
            total_value = await self._calculate_deck_value(battle_inv)
            if min_value <= total_value <= max_value:
                opponents.append((battle_inv.user, battle_inv, total_value))
        
        return opponents

    async def _calculate_deck_value(self, battle_inv: BattleInventory) -> int:
        """
        Вычислить общую стоимость колоды.
        Для лимитированных карт используется максимальное значение редкости слота.
        """
        total = 0
        slot_max_values = {
            "common": 5,
            "uncommon": 20,
            "mythic": 50,
            "legend": 80,
            "hrono": 200
        }
        
        for slot_name, max_value in slot_max_values.items():
            card = getattr(battle_inv, slot_name, None)
            if card:
                if card.rarity.name == "Лимитированный":
                    total += max_value
                else:
                    total += card.value
        
        return total

    async def add_to_search_queue(self, user: User, deck_value: int) -> bool:
        """
        Добавить пользователя в очередь поиска соперника.
        Возвращает True, если пользователь успешно добавлен.
        Возвращает False, если пользователь уже в очереди.
        """
        # Проверяем, есть ли уже пользователь в очереди
        existing = await self.get_search_queue_entry(user.id)
        if existing:
            return False
        
        entry = PvPSearchQueue(user_id=user.id, deck_value=deck_value)
        self.session.add(entry)
        await self.session.commit()
        return True

    async def remove_from_search_queue(self, user_id: int) -> bool:
        """
        Удалить пользователя из очереди поиска.
        Возвращает True, если пользователь был в очереди и удален.
        """
        entry = await self.get_search_queue_entry(user_id)
        if not entry:
            return False
        
        await self.session.delete(entry)
        await self.session.commit()
        return True

    async def get_search_queue_entry(self, user_id: int) -> Optional[PvPSearchQueue]:
        """
        Получить запись пользователя в очереди поиска.
        """
        result = await self.session.execute(
            select(PvPSearchQueue).where(PvPSearchQueue.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def find_opponent_in_queue(self, user_id: int, deck_value: int) -> Optional[Tuple[User, BattleInventory, int]]:
        """
        Найти соперника в очереди поиска с стоимостью колоды ±20%.
        Возвращает кортеж (User, BattleInventory, deck_value) соперника или None.
        """
        min_value = deck_value * 0.8
        max_value = deck_value * 1.2
        
        # Находим всех пользователей в очереди, кроме текущего
        result = await self.session.execute(
            select(PvPSearchQueue).where(
                PvPSearchQueue.user_id != user_id,
                PvPSearchQueue.deck_value >= min_value,
                PvPSearchQueue.deck_value <= max_value
            )
        )
        queue_entries = result.scalars().all()
        
        if not queue_entries:
            return None
        
        # Выбираем случайного соперника
        import random
        chosen_entry = random.choice(queue_entries)
        
        # Получаем battle_inventory соперника
        battle_inv = chosen_entry.user.battle_inventory
        if not battle_inv:
            # Если у соперника нет колоды, удаляем его из очереди
            await self.remove_from_search_queue(chosen_entry.user_id)
            return None
        
        return (chosen_entry.user, battle_inv, chosen_entry.deck_value)

    async def get_queue_count(self) -> int:
        """
        Получить количество пользователей в очереди поиска.
        """
        result = await self.session.execute(select(PvPSearchQueue))
        return len(result.scalars().all())
