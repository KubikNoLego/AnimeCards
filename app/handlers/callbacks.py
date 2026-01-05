from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from loguru import logger
from db.models import User, Verse, Rarity
from app.func.utils import _load_messages
from app.keyboards.utils import Pagination, VerseFilterPagination, VerseFilter, RarityFilterPagination, RarityFilter, pagination_keyboard, verse_filter_pagination_keyboard, rarity_filter_pagination_keyboard
from app.StateGroups.states import ChangeDescribe

router = Router()


@router.callback_query(F.data == "delete_describe")
async def delete_describe_user(callback: CallbackQuery,session : AsyncSession, state:FSMContext):
    messages = _load_messages()
    await callback.message.answer(messages["describe_updated_empty"])
    user = await session.scalar(select(User).filter_by(id=callback.from_user.id))
    user.profile.describe = ""
    await session.commit()

@router.callback_query(F.data == "change_describe")
async def change_describe_user(callback: CallbackQuery, session: AsyncSession, state:FSMContext):
    await state.set_state(ChangeDescribe.text)
    messages = _load_messages()
    await callback.message.answer(messages['change_describe_prompt'])

@router.callback_query(F.data == "sort_inventory")
async def sort_inventory_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Обработчик callback для выбора способа сортировки инвентаря."""
    try:
        logger.info(f"Обработка callback выбора способа сортировки инвентаря для пользователя {callback.from_user.id}")

        messages = _load_messages()
        select_sort_message = messages["select_sort"]

        # Создаем клавиатуру для выбора способа сортировки
        builder = InlineKeyboardBuilder()
        # Получаем текущие выбранные значения из FSM
        data = await state.get_data()
        selected_verse_name = data.get('selected_verse_name', None)
        selected_rarity_name = data.get('selected_rarity_name', None)

        if selected_rarity_name:
            builder.button(text=f"📊 По редкости ({selected_rarity_name})", callback_data="sort_by_rarity")
        else:
            builder.button(text="📊 По редкости", callback_data="sort_by_rarity")

        if selected_verse_name:
            builder.button(text=f"🌌 По вселенной ({selected_verse_name})", callback_data=VerseFilterPagination(p=1).pack())
        else:
            builder.button(text="🌌 По вселенной", callback_data=VerseFilterPagination(p=1).pack())

        # Add Apply button
        builder.button(text="✅ Применить фильтры", callback_data=Pagination(p=1).pack())
        builder.adjust(2, 1)

        # Проверяем, есть ли фото в текущем сообщении
        if callback.message.photo or callback.message.media_group_id:
            # Если есть фото, удаляем сообщение и отправляем новое
            try:
                await callback.message.delete()
                await callback.message.answer(
                    text=select_sort_message,
                    reply_markup=builder.as_markup()
                )
            except Exception as delete_error:
                logger.warning(f"Не удалось удалить сообщение с фото, используем edit_text: {delete_error}")
                # Если не удалось удалить, используем edit_text как резервный вариант
                await callback.message.edit_text(
                    text=select_sort_message,
                    reply_markup=builder.as_markup()
                )
        else:
            # Если нет фото, используем стандартный edit_text
            await callback.message.edit_text(
                text=select_sort_message,
                reply_markup=builder.as_markup()
            )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при обработке callback выбора способа сортировки инвентаря: {e}")
        await callback.answer("❌ Произошла ошибка при обработке запроса", show_alert=True)

@router.callback_query(VerseFilterPagination.filter())
async def verse_filter_pagination_callback(callback: CallbackQuery, callback_data: VerseFilterPagination, session: AsyncSession):
    """Обработчик callback для пагинации фильтра по вселенной."""
    try:
        logger.info(f"Обработка callback пагинации фильтра по вселенной для пользователя {callback.from_user.id}, страница {callback_data.p}")

        verses = await session.scalars(select(Verse))
        verses = verses.all()
        total_pages = len(verses)
        current_page = callback_data.p

        if 1 <= current_page <= total_pages:
            # Создаем клавиатуру с обновленными кнопками пагинации
            keyboard = await verse_filter_pagination_keyboard(current_page,verses=verses)
            # Получаем сообщение из messages.json
            messages = _load_messages()
            select_universe_message = messages["select_universe"]

            # Обновляем сообщение с новой клавиатурой, но сохраняем тот же текст
            await callback.message.edit_text(
                text=select_universe_message,
                reply_markup=keyboard
            )
            await callback.answer()
        else:
            await callback.answer("❌ Неверная страница", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при обработке callback пагинации фильтра по вселенной: {e}")
        await callback.answer("❌ Произошла ошибка при обработке запроса", show_alert=True)

@router.callback_query(VerseFilter.filter())
async def verse_filter_callback(callback: CallbackQuery, callback_data: VerseFilter, session: AsyncSession, state: FSMContext):
    """Обработчик callback для выбора конкретной вселенной."""
    try:
        logger.info(f"Обработка callback выбора вселенной {callback_data.verse_name} для пользователя {callback.from_user.id}")

        # Сохраняем выбранное название вселенной в FSM
        await state.update_data(selected_verse_name=callback_data.verse_name)

        # Получаем сообщение из messages.json
        messages = _load_messages()
        verse_selected_message = messages["verse_selected"].format(verse_name=callback_data.verse_name)

        # Создаем клавиатуру для подтверждения выбора
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад к сортировке", callback_data="sort_inventory")
        builder.adjust(1)

        # Обновляем сообщение с подтверждением выбора
        await callback.message.edit_text(
            text=verse_selected_message,
            reply_markup=builder.as_markup()
        )
        await callback.answer(f"✅ Выбрана вселенная: {callback_data.verse_name}")
    except Exception as e:
        logger.error(f"Ошибка при обработке callback выбора вселенной: {e}")
        await callback.answer("❌ Произошла ошибка при обработке запроса", show_alert=True)

@router.callback_query(F.data == "sort_by_rarity")
async def sort_by_rarity_callback(callback: CallbackQuery, session: AsyncSession):
    """Обработчик callback для сортировки по редкости."""
    try:
        logger.info(f"Обработка callback сортировки по редкости для пользователя {callback.from_user.id}")

        # Получаем все редкости из базы данных
        rarities = await session.scalars(select(Rarity))
        rarities = rarities.all()

        # Создаем клавиатуру с первой страницей редкостей
        keyboard = await rarity_filter_pagination_keyboard(1, rarities=rarities)

        # Получаем сообщение из messages.json
        messages = _load_messages()
        select_rarity_message = messages["select_rarity"]

        # Обновляем сообщение с новой клавиатурой
        await callback.message.edit_text(
            text=select_rarity_message,
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при обработке callback сортировки по редкости: {e}")
        await callback.answer("❌ Произошла ошибка при обработке запроса", show_alert=True)

@router.callback_query(RarityFilterPagination.filter())
async def rarity_filter_pagination_callback(callback: CallbackQuery, callback_data: RarityFilterPagination, session: AsyncSession):
    """Обработчик callback для пагинации фильтра по редкости."""
    try:
        logger.info(f"Обработка callback пагинации фильтра по редкости для пользователя {callback.from_user.id}, страница {callback_data.p}")

        rarities = await session.scalars(select(Rarity))
        rarities = rarities.all()
        total_pages = len(rarities)
        current_page = callback_data.p

        if 1 <= current_page <= total_pages:
            # Создаем клавиатуру с обновленными кнопками пагинации
            keyboard = await rarity_filter_pagination_keyboard(current_page, rarities=rarities)
            # Получаем сообщение из messages.json
            messages = _load_messages()
            select_rarity_message = messages["select_rarity"]

            # Обновляем сообщение с новой клавиатурой, но сохраняем тот же текст
            await callback.message.edit_text(
                text=select_rarity_message,
                reply_markup=keyboard
            )
            await callback.answer()
        else:
            await callback.answer("❌ Неверная страница", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при обработке callback пагинации фильтра по редкости: {e}")
        await callback.answer("❌ Произошла ошибка при обработке запроса", show_alert=True)

@router.callback_query(RarityFilter.filter())
async def rarity_filter_callback(callback: CallbackQuery, callback_data: RarityFilter, session: AsyncSession, state: FSMContext):
    """Обработчик callback для выбора конкретной редкости."""
    try:
        logger.info(f"Обработка callback выбора редкости {callback_data.rarity_name} для пользователя {callback.from_user.id}")

        # Сохраняем выбранное название редкости в FSM
        await state.update_data(selected_rarity_name=callback_data.rarity_name)

        # Получаем сообщение из messages.json
        messages = _load_messages()
        rarity_selected_message = messages["rarity_selected"].format(rarity_name=callback_data.rarity_name)

        # Создаем клавиатуру для подтверждения выбора
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад к сортировке", callback_data="sort_inventory")
        builder.adjust(1)

        # Обновляем сообщение с подтверждением выбора
        await callback.message.edit_text(
            text=rarity_selected_message,
            reply_markup=builder.as_markup()
        )
        await callback.answer(f"✅ Выбрана редкость: {callback_data.rarity_name}")
    except Exception as e:
        logger.error(f"Ошибка при обработке callback выбора редкости: {e}")
        await callback.answer("❌ Произошла ошибка при обработке запроса", show_alert=True)

@router.callback_query(Pagination.filter())
async def inventory_pagination_callback(callback: CallbackQuery, callback_data: Pagination, session: AsyncSession, state: FSMContext):
    """Обработчик callback для пагинации инвентаря с фильтрацией."""
    try:
        logger.info(f"Обработка callback пагинации инвентаря для пользователя {callback.from_user.id}, страница {callback_data.p}")

        user = await session.scalar(
            select(User)
            .filter_by(id=callback.from_user.id)
        )

        if user and user.inventory and len(user.inventory) > 0:
            # Получаем текущие фильтры из FSM
            data = await state.get_data()
            selected_verse_name = data.get('selected_verse_name', None)
            selected_rarity_name = data.get('selected_rarity_name', None)

            # Фильтруем карты по выбранным фильтрам
            filtered_cards = []
            for card in user.inventory:
                # Проверяем фильтр по вселенной
                verse_match = not selected_verse_name or card.verse.name == selected_verse_name
                # Проверяем фильтр по редкости
                rarity_match = not selected_rarity_name or card.rarity.name == selected_rarity_name

                if verse_match and rarity_match:
                    filtered_cards.append(card)

            if not filtered_cards:
                # Если нет карт, соответствующих фильтрам
                messages = _load_messages()
                filter_no_results_message = messages["filter_no_results"]

                # Создаем клавиатуру с кнопкой возврата к сортировке
                builder = InlineKeyboardBuilder()
                builder.button(text="🔙 Назад к сортировке", callback_data="sort_inventory")
                builder.adjust(1)

                # Очищаем данные FSM
                await state.clear()

                await callback.message.edit_text(
                    text=filter_no_results_message,
                    reply_markup=builder.as_markup()
                )
                return

            # Преобразование номера страницы (1-based) в индекс массива (0-based)
            card_index = callback_data.p - 1

            # Проверка валидности индекса карты для отфильтрованного списка
            if 0 <= card_index < len(filtered_cards):
                logger.info(f"Показ карты с индексом {card_index} для пользователя {user.id} (отфильтрованный список)")
                await show_inventory_card(callback, user, card_index, filtered_cards)
            else:
                logger.warning(f"Неверный индекс карты: {callback_data.p} для пользователя {user.id}")
        else:
            logger.info(f"У пользователя {callback.from_user.id} нет карт в инвентаре")
            messages = _load_messages()
            await callback.message.answer(messages["inventory_empty"])

    except Exception as e:
        logger.error(f"Ошибка при обработке callback пагинации инвентаря: {e}")
        await callback.answer("❌ Произошла ошибка при обработке запроса", show_alert=True)

async def show_inventory_card(callback: CallbackQuery, user: User, card_index: int, filtered_cards: list = None):
    """Отображение конкретной карты из инвентаря пользователя."""
    # Используем отфильтрованный список или полный инвентарь
    cards = filtered_cards if filtered_cards is not None else user.inventory
    card = cards[card_index]
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
        keyboard = await pagination_keyboard(card_index + 1, len(cards))
        logger.info(f"Редактирование сообщения с картой {card.name} с иконкой")
        try:
            await callback.message.edit_media(
                media=InputMediaPhoto(media=FSInputFile(path=f"app/icons/{card.verse.name}/{card.icon}")),
                reply_markup=keyboard
            )
            await callback.message.edit_caption(
                caption=card_info,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.warning(f"Не удалось отредактировать сообщение, отправляю новое: {e}")
            await callback.message.answer_photo(
                FSInputFile(path=f"app/icons/{card.verse.name}/{card.icon}"),
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
