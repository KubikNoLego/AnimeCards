from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select
from loguru import logger

from app.keyboards import (back_to_sort, sort_inventory_kb,
                    verse_filter_pagination_keyboard, pagination_keyboard,
                    rarity_filter_pagination_keyboard, VerseFilter, Pagination,
                    VerseFilterPagination,RarityFilter, RarityFilterPagination)
from app.messages import MText
from db import DB, Card, Verse, Rarity, UserCards, User


router = Router()


@router.callback_query(F.data == "reset_sort_filters")
async def reset_sort_filters_callback(callback: CallbackQuery,
                                    state: FSMContext):
    """Обработчик callback для сброса фильтров сортировки."""
    try:

        # Очищаем данные FSM
        await state.clear()

        builder = await back_to_sort()

        # Обновляем сообщение с подтверждением сброса
        await callback.message.edit_text(
            text=MText.get("filters_reset_success"),
            reply_markup=builder
        )
        await callback.answer(MText.get("filters_reset_success"))
    except Exception as e:
            logger.error(f"Ошибка при сбросе фильтров сортировки: {e}")
            await callback.answer(MText.get("filters_reset_error"),
                                show_alert=True)

@router.callback_query(F.data == "sort_inventory")
async def sort_inventory_callback(callback: CallbackQuery,
                                session: AsyncSession, state: FSMContext):
    """Обработчик callback для выбора способа сортировки инвентаря."""
    try:
        select_sort_message = MText.get("select_sort")

        # Получаем текущие выбранные значения из FSM
        data = await state.get_data()
        selected_verse_name = data.get('selected_verse_name', None)
        selected_rarity_name = data.get('selected_rarity_name', None)

        kb = await sort_inventory_kb(selected_rarity_name,selected_verse_name)

        # Проверяем, есть ли фото в текущем сообщении
        if callback.message.photo or callback.message.media_group_id:
            # Если есть фото, удаляем сообщение и отправляем новое
            try:
                await callback.message.delete()
                await callback.message.answer(
                    text=select_sort_message,
                    reply_markup=kb
                )
            except Exception as delete_error:
                logger.warning(
f"Не удалось удалить сообщение с фото, используем edit_text: {delete_error}")
                # Если не удалось удалить, используем edit_text как резервный вариант
                await callback.message.edit_text(
                    text=select_sort_message,
                    reply_markup=kb
                )
        else:
            # Если нет фото, используем стандартный edit_text
            await callback.message.edit_text(
                text=select_sort_message,
                reply_markup=kb
            )
        await callback.answer()
    except Exception as e:
            logger.error(
    f"Ошибка при обработке callback выбора способа сортировки инвентаря: {e}")
            await callback.answer(MText.get("processing_error"), show_alert=True)

@router.callback_query(VerseFilterPagination.filter())
async def verse_filter_pagination_callback(callback: CallbackQuery,
                callback_data: VerseFilterPagination, session: AsyncSession):
    """Обработчик callback для пагинации фильтра по вселенной."""
    try:

        verses = await session.scalars(select(Verse))
        verses = verses.all()
        total_pages = len(verses)
        current_page = callback_data.p

        if 1 <= current_page <= total_pages:
            # Создаем клавиатуру с обновленными кнопками пагинации
            keyboard = await verse_filter_pagination_keyboard(current_page,
                                                            verses=verses)
            # Получаем сообщение из messages.json
            select_universe_message = MText.get("select_universe")

            # Обновляем сообщение с новой клавиатурой, но сохраняем тот же текст
            await callback.message.edit_text(
                text=select_universe_message,
                reply_markup=keyboard
            )
            await callback.answer()
        else:
            await callback.answer(MText.get("invalid_page"), show_alert=True)
    except Exception as e:
            logger.error(
        f"Ошибка при обработке callback пагинации фильтра по вселенной: {e}")
            await callback.answer(MText.get("processing_error"),
                                show_alert=True)

@router.callback_query(VerseFilter.filter())
async def verse_filter_callback(callback: CallbackQuery,
                        callback_data: VerseFilter, session: AsyncSession,
                        state: FSMContext):
    """Обработчик callback для выбора конкретной вселенной."""
    try:

        # Сохраняем выбранное название вселенной в FSM
        await state.update_data(selected_verse_name=callback_data.verse_name)

        verse_selected_message = MText.get("verse_selected").format(
            verse_name=callback_data.verse_name)

        # Создаем клавиатуру для подтверждения выбора
        builder = await back_to_sort()

        # Обновляем сообщение с подтверждением выбора
        await callback.message.edit_text(
            text=verse_selected_message,
            reply_markup=builder
        )
        await callback.answer(MText.get("verse_selected_success").format(
            verse_name=callback_data.verse_name))
    except Exception as e:
            logger.error(
                f"Ошибка при обработке callback выбора вселенной: {e}")
            await callback.answer(MText.get("processing_error"),
                                show_alert=True)

@router.callback_query(F.data == "sort_by_rarity")
async def sort_by_rarity_callback(callback: CallbackQuery,
                                session: AsyncSession):
    """Обработчик callback для сортировки по редкости."""
    try:

        # Получаем все редкости из базы данных
        rarities = await session.scalars(select(Rarity))
        rarities = rarities.all()

        # Создаем клавиатуру с первой страницей редкостей
        keyboard = await rarity_filter_pagination_keyboard(1,
                                                        rarities=rarities)

        select_rarity_message = MText.get("select_rarity")

        # Обновляем сообщение с новой клавиатурой
        await callback.message.edit_text(
            text=select_rarity_message,
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
            logger.error(
                f"Ошибка при обработке callback сортировки по редкости: {e}")
            await callback.answer(MText.get("processing_error"),
                                show_alert=True)

@router.callback_query(RarityFilterPagination.filter())
async def rarity_filter_pagination_callback(callback: CallbackQuery,
                callback_data: RarityFilterPagination, session: AsyncSession):
    """Обработчик callback для пагинации фильтра по редкости."""
    try:

        rarities = await session.scalars(select(Rarity))
        rarities = rarities.all()
        total_pages = len(rarities)
        current_page = callback_data.p

        if 1 <= current_page <= total_pages:
            # Создаем клавиатуру с обновленными кнопками пагинации
            keyboard = await rarity_filter_pagination_keyboard(current_page,
                                                            rarities=rarities)
            select_rarity_message = MText.get("select_rarity")

            # Обновляем сообщение с новой клавиатурой, но сохраняем тот же текст
            await callback.message.edit_text(
                text=select_rarity_message,
                reply_markup=keyboard
            )
            await callback.answer()
        else:
            await callback.answer(MText.get("invalid_page"), show_alert=True)
    except Exception as e:
            logger.error(
        f"Ошибка при обработке callback пагинации фильтра по редкости: {e}")
            await callback.answer(MText.get("processing_error"),
                                show_alert=True)

@router.callback_query(RarityFilter.filter())
async def rarity_filter_callback(callback: CallbackQuery,
                    callback_data: RarityFilter, session: AsyncSession,
                    state: FSMContext):
    """Обработчик callback для выбора конкретной редкости."""
    try:

        # Сохраняем выбранное название редкости в FSM
        await state.update_data(selected_rarity_name=callback_data.rarity_name)

        rarity_selected_message = MText.get("rarity_selected").format(
            rarity_name=callback_data.rarity_name)

        # Создаем клавиатуру для подтверждения выбора
        builder = await back_to_sort()

        # Обновляем сообщение с подтверждением выбора
        await callback.message.edit_text(
            text=rarity_selected_message,
            reply_markup=builder
        )
        await callback.answer(MText.get("rarity_selected_success").format(
            rarity_name=callback_data.rarity_name))
    except Exception as e:
            logger.error(f"Ошибка при обработке callback выбора редкости: {e}")
            await callback.answer(MText.get("processing_error"),
                                show_alert=True)

@router.callback_query(Pagination.filter())
async def inventory_pagination_callback(callback: CallbackQuery,
                    callback_data: Pagination, session: AsyncSession, 
                    state: FSMContext):
    """Обработчик callback для пагинации инвентаря с фильтрацией."""
    try:

        user = await DB(session).get_user(callback.from_user.id)

        if user and user.inventory and len(user.inventory) > 0:
            # Получаем текущие фильтры из FSM
            data = await state.get_data()
            selected_verse_name = data.get('selected_verse_name', None)
            selected_rarity_name = data.get('selected_rarity_name', None)
            
            conditions = [UserCards.user_id == user.id]
            if selected_rarity_name:
                conditions.append(Card.rarity_name == selected_rarity_name)
            if selected_verse_name:
                conditions.append(Card.verse_name == selected_verse_name)
            
            stmt = select(Card).join(UserCards).where(and_(*conditions))
            filtered_cards = await session.scalars(stmt)
            filtered_cards = filtered_cards.all()

            if not filtered_cards:
                # Если нет карт, соответствующих фильтрам
                filter_no_results_message = MText.get("filter_no_results")

                # Создаем клавиатуру с кнопкой возврата к сортировке
                builder = await back_to_sort()
                # Очищаем данные FSM
                await state.clear()

                await callback.message.edit_text(
                    text=filter_no_results_message,
                    reply_markup=builder
                )
                return

            # Преобразование номера страницы (1-based) в индекс массива (0-based)
            card_index = callback_data.p - 1

            # Проверка валидности индекса карты для отфильтрованного списка
            if 0 <= card_index < len(filtered_cards):
                await show_inventory_card(callback, user, card_index,
                                        filtered_cards)
            else:
                logger.warning(
        f"Неверный индекс карты: {callback_data.p} для пользователя {user.id}")
                await callback.message.answer(MText.get("inventory_empty"))
        else:
            await callback.message.answer(MText.get("inventory_empty"))

    except Exception as e:
            logger.error(
                f"Ошибка при обработке callback пагинации инвентаря: {e}")
            await callback.answer(MText.get("processing_error"),
                                show_alert=True)

async def show_inventory_card(callback: CallbackQuery, user: User,
                            card_index: int, filtered_cards: list = None):
    """Отображение конкретной карты из инвентаря пользователя."""
    # Используем отфильтрованный список или полный инвентарь
    cards = filtered_cards if filtered_cards is not None else user.inventory
    card = cards[card_index]

    # Форматирование информации о карте
    card_info = MText.get("card").format(name=card.name,
                                            verse=card.verse_name,
                                            rarity=card.rarity_name,
                                            value=card.value)
    card_info = card_info + ("\n\n✨ Shiny" if card.shiny else "")

    keyboard = await pagination_keyboard(card_index + 1, len(cards))
    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(media=FSInputFile(
                path=f"app/icons/{card.verse.name}/{card.icon}")),
            reply_markup=keyboard
        )
        await callback.message.edit_caption(
            caption=card_info,
            reply_markup=keyboard
        )

    except Exception as e:
        logger.warning(f"Не удалось отредактировать сообщение: {e}")