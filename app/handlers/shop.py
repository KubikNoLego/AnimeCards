from aiogram import Router,F
from aiogram.types import Message,CallbackQuery, FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.filters import Private
from app.keyboards import shop_keyboard, ShopItemCallback, shop_keyboard_choice
from app.messages import MText
from db import DB, RedisRequests, Card


router = Router()


@router.message(F.text == "🛒 Магазин",Private())
async def _(message:Message,session:AsyncSession):
    items = await RedisRequests.daily_items()
    db = DB(session)
    user = await db.get_user(message.from_user.id)
    if items:
        try:
            items = items.decode("utf-8").split(",")
            cards = []

            for item_id in items:
                if item_id.strip():  # Проверяем, что ID не пустой
                    card = await session.scalar(select(Card).filter_by(id=
                                                        int(item_id.strip())))
                    if card:
                        # Применяем 70% надбавку к цене карточки
                        card.value = int(card.value * 1.7)
                        cards.append(card)

            if cards:
                # Создаем клавиатуру с товарами
                keyboard = await shop_keyboard(cards if user.vip else cards[0:3])
                await message.answer(MText.get("daily_shop"), reply_markup=keyboard)
            else:
                await message.answer(MText.get("shop_empty"))
        except Exception as e:
            logger.error(f"Ошибка при обработке магазина: {str(e)}", exc_info=True)
            await message.answer(MText.get("shop_empty"))
    else:
        await message.answer(MText.get("shop_empty"))


@router.callback_query(ShopItemCallback.filter())
async def shop_item_callback(callback: CallbackQuery,
                    callback_data: ShopItemCallback, session: AsyncSession):
    """Обработчик callback для покупки карточки из магазина."""
    try:

        # Получаем карточку из базы данных
        card = await session.scalar(select(Card).filter_by(
            id=callback_data.item_id))

        if not card:
            await callback.answer(MText.get("card_not_found"), show_alert=True)
            return

        # Получаем пользователя
        user = await DB(session).get_user(callback.from_user.id)

        if not user:
            await callback.answer(MText.get("user_not_found_short"),
                                show_alert=True)
            return

        # Проверяем, достаточно ли у пользователя йен
        if user.balance < int(card.value*1.7):
            await callback.answer(MText.get("not_enough_yens"),
                                show_alert=True)
            return

        # Проверяем, есть ли уже эта карточка у пользователя
        if card in user.inventory:
            await callback.answer(MText.get("card_already_owned"),
                                show_alert=True)
            return

        # Форматируем информацию о карточке
        card_info = MText.get("card").format(name=card.name,
                                            verse=card.verse_name,
                                            rarity=card.rarity_name,
                                            value=(str(card.value)) + 
                            f" ¥\n\nЦена покупки: {int(card.value * 1.7)}")
        
        builder = await shop_keyboard_choice(card_id=card.id)

        try:
            await callback.message.answer_photo(
                FSInputFile(path=f"app/icons/{card.verse.name}/{card.icon}"),
                caption=card_info,
                reply_markup=builder
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить фото карточки: {e}")
            await callback.message.answer(
                card_info,
                reply_markup=builder
            )

        await callback.message.delete()
        await callback.answer()

    except Exception as e:
            logger.error(f"Ошибка при обработке покупки карточки: {str(e)}",
                        exc_info=True)
            await callback.answer(MText.get("purchase_error"), show_alert=True)

@router.callback_query(F.data.startswith("buy_card_"))
async def buy_card_callback(callback: CallbackQuery, session: AsyncSession):
    """Обработчик callback для подтверждения покупки карточки."""
    try:
        current_items = await RedisRequests.daily_items()

        # Проверяем, что current_items не None и не пустой
        if not current_items:
            await callback.message.answer(MText.get("shop_items_changed"))
            return

        current_items = current_items.decode("utf-8").split(",")
        current_items = list(map(int, current_items))
        # Извлекаем ID карточки из callback данных
        card_id = int(callback.data.split("_")[-1])

        if card_id in current_items:
            # Получаем карточку и пользователя
            card = await session.scalar(select(Card).filter_by(id=card_id))
            user = await DB(session).get_user(callback.from_user.id)

            if not card or not user:
                await callback.answer(MText.get("card_not_found"),
                                    show_alert=True)
                return

            # Проверяем, достаточно ли у пользователя йен
            if user.balance < int(card.value*1.7):
                await callback.answer(MText.get("not_enough_yens"),
                                    show_alert=True)
                return

            # Проверяем, есть ли уже эта карточка у пользователя
            if card in user.inventory:
                await callback.answer(MText.get("card_already_owned"),
                                    show_alert=True)
                return

            # Выполняем покупку
            user.balance -= int(card.value*1.7)
            user.inventory.append(card)

            await session.commit()

            # Удаляем сообщение с предложением покупки
            try:
                await callback.message.delete()
            except Exception as delete_error:
                logger.warning(
f"Не удалось удалить сообщение с предложением покупки: {str(delete_error)}")

            # Отправляем подтверждение о покупке
            await callback.message.answer(MText.get("purchase_success").format(
                card_name=card.name, price=int(card.value*1.7)))
        else:
            await callback.message.answer(MText.get("shop_items_changed"))

        await callback.answer()

    except Exception as e:
            logger.error(f"Ошибка при покупке карточки: {str(e)}", 
                        exc_info=True)
            await callback.answer(MText.get("purchase_error"), show_alert=True)

@router.callback_query(F.data == "cancel_buy")
async def cancel_buy_callback(callback: CallbackQuery):
    """Обработчик callback для отмены покупки."""
    try:
        # Удаляем сообщение с предложением покупки
        try:
            await callback.message.delete()
        except Exception as delete_error:
            logger.warning(
f"Не удалось удалить сообщение с предложением покупки: {str(delete_error)}")

        # Отправляем сообщение об отмене
        await callback.message.answer(MText.get("purchase_cancelled"))
        await callback.answer(MText.get("purchase_cancelled"))
    except Exception as e:
            logger.error(f"Ошибка при отмене покупки: {str(e)}")
            await callback.answer(MText.get("cancel_error"), show_alert=True)