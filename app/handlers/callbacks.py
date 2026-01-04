from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from loguru import logger
from db.models import User
from app.func.utils import _load_messages
from app.keyboards.utils import Pagination, pagination_keyboard

router = Router()

@router.callback_query(Pagination.filter())
async def inventory_pagination_callback(callback: CallbackQuery, callback_data: Pagination, session: AsyncSession):
    """Обработчик callback для пагинации инвентаря."""
    try:
        logger.info(f"Обработка callback пагинации инвентаря для пользователя {callback.from_user.id}, страница {callback_data.p}")

        user = await session.scalar(
            select(User)
            .filter_by(id=callback.from_user.id)
        )

        if user and user.inventory and len(user.inventory) > 0:
            # Преобразование номера страницы (1-based) в индекс массива (0-based)
            card_index = callback_data.p - 1

            # Проверка валидности индекса карты
            if 0 <= card_index < len(user.inventory):
                logger.info(f"Показ карты с индексом {card_index} для пользователя {user.id}")
                await show_inventory_card(callback, user, card_index)
            else:
                logger.warning(f"Неверный индекс карты: {callback_data.p} для пользователя {user.id}")
        else:
            logger.info(f"У пользователя {callback.from_user.id} нет карт в инвентаре")
            messages = _load_messages()
            await callback.message.answer(messages["inventory_empty"])

    except Exception as e:
        logger.error(f"Ошибка при обработке callback пагинации инвентаря: {e}")
        await callback.answer("❌ Произошла ошибка при обработке запроса", show_alert=True)

async def show_inventory_card(callback: CallbackQuery, user: User, card_index: int):
    """Отображение конкретной карты из инвентаря пользователя."""
    card = user.inventory[card_index]
    logger.info(f"Отображение карты {card.name} (ID: {card.id}) для пользователя {user.id}")

    # Форматирование информации о карте
    card_info = f"""
📄 <b>{card.name}</b>
📚 Вселенная: {card.verse.name}
🎨 Редкость: {card.rarity.name}
💰 Ценность: {card.value} ¥
{"✨ Shiny" if card.shiny else ""}
"""

    # Редактирование сообщения с информацией о карте
    if card.icon:
        keyboard = await pagination_keyboard(card_index + 1, len(user.inventory))
        logger.info(f"Редактирование сообщения с картой {card.name} с иконкой")
        try:
            await callback.message.edit_media(
                media=FSInputFile(path=f"app/{card.icon}"),
                reply_markup=keyboard
            )
            await callback.message.edit_caption(
                caption=card_info,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.warning(f"Не удалось отредактировать сообщение, отправляю новое: {e}")
            await callback.message.answer_photo(
                FSInputFile(path=f"app/{card.icon}"),
                caption=card_info,
                reply_markup=keyboard
            )
    else:
        logger.info(f"У карты {card.name} нет иконки, редактирую текст сообщения")
        try:
            await callback.message.edit_text(
                text=card_info
            )
        except Exception as e:
            logger.warning(f"Не удалось отредактировать сообщение, отправляю новое: {e}")
            await callback.message.answer(card_info)
