from datetime import datetime, timedelta
import random

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import DailyShopPurchase, ShopItems, User, UserCards
from app.database.requests import DB
from app.messages.MessageControl import MText
from app.utils.constants import LUCK_BOOST, SHOP_ITEMS, SHOP_ITEMS_PRICES, YEN_BOOST

class ShopService:

    @classmethod
    def get_time_until_next_update(cls) -> str:
        """Рассчитывает время до следующего обновления магазина (до полуночи по МСК)."""
        from app.utils.constants import MSK_TIMEZONE
        now = datetime.now(MSK_TIMEZONE)

        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

        time_until_update = midnight - now
        total_seconds = int(time_until_update.total_seconds())

        if total_seconds < 0:
            return "0 часов 0 минут"

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        return f"{hours} часов {minutes} минут"

    @classmethod
    def shop_message(cls, user: User):

        time_until_update = cls.get_time_until_next_update()
        return MText.get("shop").format(
            time = time_until_update,
            standard_spin_price = SHOP_ITEMS_PRICES['standard_spin'],
            luck_boost_price = SHOP_ITEMS_PRICES['luck_boost'],
            yen_boost_price = SHOP_ITEMS_PRICES['yen_boost'],
            mystery_box_price = SHOP_ITEMS_PRICES['mystery_box'],
            duplicator_price = SHOP_ITEMS_PRICES['duplicator'],
            standard_spins = user.free_standard_opens,
            season_spins = user.free_season_opens,
            luck_boosts = user.luck_boosts,
            yen_boosts = user.yen_boosts,
            duplicators = user.duplicators,
            luck_boost = int(LUCK_BOOST*100),
            yen_boost = int(YEN_BOOST*100)
        )

    @classmethod
    async def add_item(cls, item: str, user_id: int, session: AsyncSession):
        db = DB(session)
        user = await db.user.get_user(user_id)

        item = ShopItems(item)

        if item in user.today_shop_purchases:
            logger.error(f"Пользователь {user.id} уже покупал {item}")
            raise ValueError("Этот предмет уже был куплен вами")

        price = SHOP_ITEMS_PRICES[item.value]

        if user.balance < price:
            raise ValueError(MText.get("not_enough_yens"))

        user.balance -= price

        result = None
        match item:
            case ShopItems.STANDARD_SPIN:
                user.free_standard_opens += 1
                result = MText.get("successful").format(item=SHOP_ITEMS[item][0])
            case ShopItems.LUCK_BOOST:
                user.luck_boosts += 1
                result = MText.get("successful").format(item=SHOP_ITEMS[item][0])
            case ShopItems.YEN_BOOST:
                user.yen_boosts += 1
                result = MText.get("successful").format(item=SHOP_ITEMS[item][0])
            case ShopItems.DUPLICATOR:
                user.duplicators += 1
                result = MText.get("successful").format(item=SHOP_ITEMS[item][0])
            case ShopItems.MYSTERY_BOX:
                result = await cls.add_mystery_box(user, session)

        user.daily_shop_purchases.append(
            DailyShopPurchase(
                user_id = user.id,
                shop_date = datetime.today().date(),
                item = item
            )
        )
        
        logger.info(f"Пользователь ({user.id}) купил {item}")

        await session.commit()
        return result

    @classmethod
    async def add_mystery_box(cls, user: User, session: AsyncSession):
        """Обработка открытия таинственного ящика."""
        rewards = []

        # Шанс на лимитированную карту (1%)
        if random.random() < 0.01:
            from app.database.repositories.card_repo import CardRepo
            card_repo = CardRepo(session)
            card = await card_repo.get_card(361)
            if card:
                existing_card = await session.scalar(
                    select(UserCards).where(
                        UserCards.user_id == user.id,
                        UserCards.card_id == card.id,
                        UserCards.shiny == False
                    )
                )
                if not existing_card:
                    user.inventory.append(UserCards(
                        user_id=user.id,
                        card_id=card.id,
                        shiny=False,
                        level=1
                    ))
                    rewards.append(f"🎉 ЛИМИТИРОВАННАЯ КАРТА: {card.name}!")
                else:
                    extra_yen = random.randint(100, 300)
                    user.balance += extra_yen
                    rewards.append(f"🎉 ЛИМИТИРОВАННАЯ КАРТА: <b>{card.name}</b> (уже есть)")
                    rewards.append(f"💰 <b>{extra_yen}</b> ¥ <i>(компенсация)</i>")

        # Шанс на дополнительные йены (70%)
        if random.random() < 1:
            extra_yen = random.randint(10, 80)
            user.balance += extra_yen
            rewards.append(f"💰 <b>{extra_yen}</b> ¥")

        # Шанс на бусты удачи (50%)
        if random.random() < 0.5:
            boost_amount = random.randint(1, 3)
            user.luck_boosts += boost_amount
            rewards.append(f"🍀 <b>{boost_amount}</b> бустов удачи")

        # Шанс на бусты йен (30%)
        if random.random() < 0.3:
            boost_amount = random.randint(1, 3)
            user.yen_boosts += boost_amount
            rewards.append(f"💰 <b>{boost_amount}</b> бустов йен")

        # Шанс на бесплатные сезонные крутки (10%)
        if random.random() < 0.1:
            free_season_spins = random.randint(1, 2)
            user.free_season_opens += free_season_spins
            rewards.append(f"🎟️ <b>{free_season_spins}</b> бесплатных <b>сезонных</b> круток")

        logger.info(f"Пользователь ({user.id}) получил награды с таинственного ящика\n{rewards}")
        return "📦 Таинственный ящик открыт!\n\n" + "\n".join(rewards)
