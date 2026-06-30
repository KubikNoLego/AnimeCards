from aiogram import Router,F
from aiogram.types import Message,CallbackQuery, InputRichMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters import Private
from app.keyboards import shop_keyboard, ShopItemCallback
from app.keyboards.inline.shop_kb import premium_keyboard, shop
from app.messages import MText
from app.database import DB
from app.services.ShopService import ShopService


router = Router()


@router.message(F.text == "🛒 Магазин", Private())
async def _(message: Message, session: AsyncSession):
    await message.answer(MText.get("common_shop"), reply_markup=shop())

@router.callback_query(F.data == "daily_shop")
async def _(callback: CallbackQuery, session:AsyncSession):
    db = DB(session)
    user = await db.user.get_user(callback.from_user.id)
    if not user:
        return

    items = user.today_shop_purchases
    keyboard = shop_keyboard(items, user.vip)

    await callback.message.answer_rich(InputRichMessage(
                            html=ShopService.shop_message(user)),
                            reply_markup=keyboard)
    
    await callback.message.delete()


@router.callback_query(ShopItemCallback.filter())
async def shop_item_callback(callback: CallbackQuery,
                    callback_data: ShopItemCallback, session: AsyncSession):
    """Обработчик callback для покупки карточки из магазина."""

    item = callback_data.item

    try:
        text = await ShopService.add_item(item, callback.from_user.id, session)
        await callback.message.answer(text)
        await callback.message.delete()
    
    except ValueError as _e:
        await callback.answer(str(_e), show_alert=True)

@router.callback_query(F.data == "premium_shop")
async def _(callback: CallbackQuery, session: AsyncSession):
    await callback.message.answer_rich(InputRichMessage(
        html=MText.get("premium_shop")
    ), reply_markup=premium_keyboard())
    await callback.message.delete()