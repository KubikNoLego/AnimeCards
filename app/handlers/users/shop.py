from aiogram import Router,F
from aiogram.types import Message,CallbackQuery, FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.filters import Private
from app.keyboards import shop_keyboard, ShopItemCallback
from app.messages import MText
from app.database import DB, RedisRequests, Card
from app.services.random_card import random_hrono
from app.services.shop import delete_item
from app.utils.card_formater import format_buyed_card
from app.utils.enums.shop import ShopEnum


router = Router()


@router.message(F.text == "🛒 Магазин",Private())
async def _(message:Message,session:AsyncSession):
    db = DB(session)
    user = await db.user.get_user(message.from_user.id)
    if not user:
        return
    items = await RedisRequests().get_user_items(user)
    keyboard = await shop_keyboard(items)
    await message.answer(MText.get("daily_shop"), reply_markup=keyboard)


@router.callback_query(ShopItemCallback.filter())
async def shop_item_callback(callback: CallbackQuery,
                    callback_data: ShopItemCallback, session: AsyncSession):
    """Обработчик callback для покупки карточки из магазина."""
    item = callback_data.item
    db = DB(session)
    user = await db.user.get_user(callback.from_user.id)

    match item:
        case "add_pity":
            if user.balance < 80:
                await callback.answer(MText.get("not_enough_yens"))
                return
            user.pity += 5
            user.balance -= 80
            await session.commit()
            await callback.message.answer(MText.get("add_pity_message").format(
                                                            pity = user.pity))
            await delete_item(user, ShopEnum.ADD_PITY)
            await callback.message.delete()
        case "free_open":
            if user.balance < 18:
                await callback.answer(MText.get("not_enough_yens"))
                return
            user.free_open += 1
            user.balance -= 18
            await session.commit()
            await callback.message.answer(MText.get("free_open_message").format(
                                                    free_opens = user.free_open))
            await delete_item(user, ShopEnum.FREE_OPEN)
            await callback.message.delete()
        case "random_hrono":
            if user.balance < 200:
                await callback.answer(MText.get("not_enough_yens"))
                return
            user.balance -= 200
            card = await random_hrono(session)
            if card not in user.inventory:
                user.inventory.append(card)
                await session.commit()
            user.balance += int(card.value*0.8)
            await callback.message.reply_photo(
            photo=FSInputFile(path=f"app/assets/cards/{card.verse.name}/{card.icon}"),
            caption=format_buyed_card(card)
                )
            await delete_item(user, ShopEnum.RANDOM_HRONO)
            await callback.message.delete()
        case "boost":
            if user.balance < 35:
                await callback.answer(MText.get("not_enough_yens"))
                return
            user.balance -= 35
            await RedisRequests().add_luck_boost(user.id)
            boosts = await RedisRequests().luck_boosts(user.id)
            await callback.message.answer(MText.get("boost_message").format(
                                                    boosts = boosts))
            await delete_item(user, ShopEnum.BOOST)
            await callback.message.delete()
        case "yens_boost":
            if user.balance < 35:
                await callback.answer(MText.get("not_enough_yens"))
                return
            user.balance -= 35
            await RedisRequests().add_yens_boost(user.id)
            boosts = await RedisRequests().yens_boosts(user.id)
            await callback.message.answer(MText.get("boost_message").format(
                                                    boosts = boosts))
            await delete_item(user, ShopEnum.YENS_BOOST)
            await callback.message.delete()