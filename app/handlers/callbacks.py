# Стандартные библиотеки

# Сторонние библиотеки
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

# Локальные импорты
from db.models import Card, User, Verse, Rarity
from app.func import _load_messages
from app.keyboards import Pagination, ShopItemCallback, VerseFilterPagination, VerseFilter, RarityFilter, RarityFilterPagination, pagination_keyboard, verse_filter_pagination_keyboard, rarity_filter_pagination_keyboard
from app.StateGroups.states import ChangeDescribe
from db.requests import RedisRequests, get_user

router = Router()


@router.callback_query(F.data == "delete_describe")
async def delete_describe_user(callback: CallbackQuery,session : AsyncSession, state:FSMContext):
    messages = _load_messages()
    await callback.message.answer(messages["describe_updated_empty"])
    user = await get_user(session, callback.from_user.id)
    user.profile.describe = ""
    await session.commit()

@router.callback_query(F.data == "change_describe")
async def change_describe_user(callback: CallbackQuery, session: AsyncSession, state:FSMContext):
    await state.set_state(ChangeDescribe.text)
    messages = _load_messages()
    await callback.message.answer(messages['change_describe_prompt'])

@router.callback_query(F.data == "reset_sort_filters")
async def reset_sort_filters_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик callback для сброса фильтров сортировки."""
    try:
        # logger.info(f"Сброс фильтров сортировки для пользователя {callback.from_user.id}")

        # Очищаем данные FSM
        await state.clear()

        # Получаем сообщение из messages.json
        messages = _load_messages()

        # Создаем клавиатуру для подтверждения сброса
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад к сортировке", callback_data="sort_inventory")
        builder.adjust(1)

        # Обновляем сообщение с подтверждением сброса
        await callback.message.edit_text(
            text=messages["filters_reset_success"],
            reply_markup=builder.as_markup()
        )
        await callback.answer(messages["filters_reset_success"])
    except Exception as e:
            logger.error(f"Ошибка при сбросе фильтров сортировки: {e}")
            messages = _load_messages()
            await callback.answer(messages["filters_reset_error"], show_alert=True)

@router.callback_query(F.data == "sort_inventory")
async def sort_inventory_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Обработчик callback для выбора способа сортировки инвентаря."""
    try:
        # logger.info(f"Обработка callback выбора способа сортировки инвентаря для пользователя {callback.from_user.id}")

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

        # Add Reset button
        builder.button(text="🔄 Сбросить фильтры", callback_data="reset_sort_filters")
        # Add Apply button
        builder.button(text="✅ Применить фильтры", callback_data=Pagination(p=1).pack())
        builder.adjust(2, 1, 1)

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
            messages = _load_messages()
            await callback.answer(messages["processing_error"], show_alert=True)

@router.callback_query(ShopItemCallback.filter())
async def shop_item_callback(callback: CallbackQuery, callback_data: ShopItemCallback, session: AsyncSession):
    """Обработчик callback для покупки карточки из магазина."""
    try:
        # logger.info(f"Обработка callback покупки карточки {callback_data.item_id} для пользователя {callback.from_user.id}")

        # Получаем карточку из базы данных
        card = await session.scalar(select(Card).filter_by(id=callback_data.item_id))

        if not card:
            messages = _load_messages()
            await callback.answer(messages["card_not_found"], show_alert=True)
            return

        # Получаем пользователя
        user = await get_user(session, callback.from_user.id)

        if not user:
            messages = _load_messages()
            await callback.answer(messages["user_not_found_short"], show_alert=True)
            return

        # Проверяем, достаточно ли у пользователя йен
        if user.yens < int(card.value*1.7):
            messages = _load_messages()
            await callback.answer(messages["not_enough_yens"], show_alert=True)
            return

        # Проверяем, есть ли уже эта карточка у пользователя
        if card in user.inventory:
            messages = _load_messages()
            await callback.answer(messages["card_already_owned"], show_alert=True)
            return

        # Создаем клавиатуру с подтверждением покупки
        builder = InlineKeyboardBuilder()
        builder.button(text="💰 Купить", callback_data=f"buy_card_{card.id}")
        builder.button(text="🔙 Отмена", callback_data="cancel_buy")
        builder.adjust(2)

        # Форматируем информацию о карточке
        card_info = f"""
🛒 <b>{card.name}</b>
🌌 Вселенная: {card.verse.name}
🎨 Редкость: {card.rarity.name}
💰 Цена: {int(card.value*1.7)} ¥

<i>Подтвердите покупку:</i>
"""

        # Отображаем карточку с клавиатурой подтверждения
        if card.icon:
            try:
                await callback.message.answer_photo(
                    FSInputFile(path=f"app/icons/{card.verse.name}/{card.icon}"),
                    caption=card_info,
                    reply_markup=builder.as_markup()
                )
            except Exception as e:
                logger.warning(f"Не удалось отправить фото карточки: {e}")
                await callback.message.answer(
                    card_info,
                    reply_markup=builder.as_markup()
                )
        else:
            await callback.message.answer(
                card_info,
                reply_markup=builder.as_markup()
            )

        await callback.message.delete()
        await callback.answer()

    except Exception as e:
            logger.error(f"Ошибка при обработке покупки карточки: {str(e)}", exc_info=True)
            messages = _load_messages()
            await callback.answer(messages["purchase_error"], show_alert=True)

@router.callback_query(F.data.startswith("buy_card_"))
async def buy_card_callback(callback: CallbackQuery, session: AsyncSession):
    """Обработчик callback для подтверждения покупки карточки."""
    try:
        # logger.info(f"Обработка подтверждения покупки карточки для пользователя {callback.from_user.id}")
        current_items = await RedisRequests.daily_items()

        # Проверяем, что current_items не None и не пустой
        if not current_items:
            messages = _load_messages()
            await callback.message.answer(messages['shop_items_changed'])
            return

        current_items = current_items.decode("utf-8").split(",")
        current_items = list(map(int, current_items))
        # Извлекаем ID карточки из callback данных
        card_id = int(callback.data.split("_")[-1])

        # Добавляем отладочный вывод для проверки
        # logger.info(f"Текущие товары в магазине: {current_items}")
        # logger.info(f"Покупаемая карточка ID: {card_id}")
        # logger.info(f"Карточка в текущем ассортименте: {card_id in current_items}")

        if card_id in current_items:
            # Получаем карточку и пользователя
            card = await session.scalar(select(Card).filter_by(id=card_id))
            user = await get_user(session, callback.from_user.id)

            if not card or not user:
                messages = _load_messages()
                await callback.answer(messages["card_not_found"], show_alert=True)
                return

            # Проверяем, достаточно ли у пользователя йен
            if user.yens < card.value:
                messages = _load_messages()
                await callback.answer(messages["not_enough_yens"], show_alert=True)
                return

            # Проверяем, есть ли уже эта карточка у пользователя
            if card in user.inventory:
                messages = _load_messages()
                await callback.answer(messages["card_already_owned"], show_alert=True)
                return

            # Выполняем покупку
            user.yens -= int(card.value*1.7)
            user.inventory.append(card)

            await session.commit()

            # Удаляем сообщение с предложением покупки
            try:
                await callback.message.delete()
            except Exception as delete_error:
                logger.warning(f"Не удалось удалить сообщение с предложением покупки: {str(delete_error)}")

            # Отправляем подтверждение о покупке
            messages = _load_messages()
            await callback.message.answer(messages["purchase_success"].format(card_name=card.name, price=int(card.value*1.7)))

            await callback.answer(messages["purchase_success"].split('\n')[0])
        else:
            messages = _load_messages()
            await callback.message.answer(messages['shop_items_changed'])

    except Exception as e:
            logger.error(f"Ошибка при покупке карточки: {str(e)}", exc_info=True)
            messages = _load_messages()
            await callback.answer(messages["purchase_error"], show_alert=True)

@router.callback_query(F.data == "cancel_buy")
async def cancel_buy_callback(callback: CallbackQuery):
    """Обработчик callback для отмены покупки."""
    try:
        # Удаляем сообщение с предложением покупки
        try:
            await callback.message.delete()
        except Exception as delete_error:
            logger.warning(f"Не удалось удалить сообщение с предложением покупки: {str(delete_error)}")

        # Отправляем сообщение об отмене
        messages = _load_messages()
        await callback.message.answer(messages["purchase_cancelled"])
        await callback.answer(messages["purchase_cancelled"])
    except Exception as e:
            logger.error(f"Ошибка при отмене покупки: {str(e)}")
            messages = _load_messages()
            await callback.answer(messages["cancel_error"], show_alert=True)

@router.callback_query(VerseFilterPagination.filter())
async def verse_filter_pagination_callback(callback: CallbackQuery, callback_data: VerseFilterPagination, session: AsyncSession):
    """Обработчик callback для пагинации фильтра по вселенной."""
    try:
        # logger.info(f"Обработка callback пагинации фильтра по вселенной для пользователя {callback.from_user.id}, страница {callback_data.p}")

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
            messages = _load_messages()
            await callback.answer(messages["invalid_page"], show_alert=True)
    except Exception as e:
            logger.error(f"Ошибка при обработке callback пагинации фильтра по вселенной: {e}")
            messages = _load_messages()
            await callback.answer(messages["processing_error"], show_alert=True)

@router.callback_query(VerseFilter.filter())
async def verse_filter_callback(callback: CallbackQuery, callback_data: VerseFilter, session: AsyncSession, state: FSMContext):
    """Обработчик callback для выбора конкретной вселенной."""
    try:
        # logger.info(f"Обработка callback выбора вселенной {callback_data.verse_name} для пользователя {callback.from_user.id}")

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
        await callback.answer(messages["verse_selected_success"].format(verse_name=callback_data.verse_name))
    except Exception as e:
            logger.error(f"Ошибка при обработке callback выбора вселенной: {e}")
            messages = _load_messages()
            await callback.answer(messages["processing_error"], show_alert=True)

@router.callback_query(F.data == "sort_by_rarity")
async def sort_by_rarity_callback(callback: CallbackQuery, session: AsyncSession):
    """Обработчик callback для сортировки по редкости."""
    try:
        # logger.info(f"Обработка callback сортировки по редкости для пользователя {callback.from_user.id}")

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
            messages = _load_messages()
            await callback.answer(messages["processing_error"], show_alert=True)

@router.callback_query(RarityFilterPagination.filter())
async def rarity_filter_pagination_callback(callback: CallbackQuery, callback_data: RarityFilterPagination, session: AsyncSession):
    """Обработчик callback для пагинации фильтра по редкости."""
    try:
        # logger.info(f"Обработка callback пагинации фильтра по редкости для пользователя {callback.from_user.id}, страница {callback_data.p}")

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
            messages = _load_messages()
            await callback.answer(messages["invalid_page"], show_alert=True)
    except Exception as e:
            logger.error(f"Ошибка при обработке callback пагинации фильтра по редкости: {e}")
            messages = _load_messages()
            await callback.answer(messages["processing_error"], show_alert=True)

@router.callback_query(RarityFilter.filter())
async def rarity_filter_callback(callback: CallbackQuery, callback_data: RarityFilter, session: AsyncSession, state: FSMContext):
    """Обработчик callback для выбора конкретной редкости."""
    try:
        # logger.info(f"Обработка callback выбора редкости {callback_data.rarity_name} для пользователя {callback.from_user.id}")

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
        await callback.answer(messages["rarity_selected_success"].format(rarity_name=callback_data.rarity_name))
    except Exception as e:
            logger.error(f"Ошибка при обработке callback выбора редкости: {e}")
            messages = _load_messages()
            await callback.answer(messages["processing_error"], show_alert=True)

@router.callback_query(Pagination.filter())
async def inventory_pagination_callback(callback: CallbackQuery, callback_data: Pagination, session: AsyncSession, state: FSMContext):
    """Обработчик callback для пагинации инвентаря с фильтрацией."""
    try:
        # logger.info(f"Обработка callback пагинации инвентаря для пользователя {callback.from_user.id}, страница {callback_data.p}")

        user = await get_user(session, callback.from_user.id)

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
                # logger.info(f"Показ карты с индексом {card_index} для пользователя {user.id} (отфильтрованный список)")
                await show_inventory_card(callback, user, card_index, filtered_cards)
            else:
                logger.warning(f"Неверный индекс карты: {callback_data.p} для пользователя {user.id}")
                messages = _load_messages()
                await callback.message.answer(messages["inventory_empty"])
        else:
            # logger.info(f"У пользователя {callback.from_user.id} нет карт в инвентаре")
            messages = _load_messages()
            await callback.message.answer(messages["inventory_empty"])

    except Exception as e:
            logger.error(f"Ошибка при обработке callback пагинации инвентаря: {e}")
            messages = _load_messages()
            await callback.answer(messages["processing_error"], show_alert=True)

async def show_inventory_card(callback: CallbackQuery, user: User, card_index: int, filtered_cards: list = None):
    """Отображение конкретной карты из инвентаря пользователя."""
    # Используем отфильтрованный список или полный инвентарь
    cards = filtered_cards if filtered_cards is not None else user.inventory
    card = cards[card_index]
    # logger.info(f"Отображение карты {card.name} (ID: {card.id}) для пользователя {user.id}")

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
        # logger.info(f"Редактирование сообщения с картой {card.name} с иконкой")
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
            logger.warning(f"Не удалось отредактировать сообщение: {e}")
    else:
        # logger.info(f"У карты {card.name} нет иконки, редактирую текст сообщения")
        try:
            await callback.message.edit_text(
                text=card_info
            )
        except Exception as e:
            # logger.warning(f"Не удалось отредактировать сообщение, отправляю новое: {e}")
            await callback.message.answer(card_info)
