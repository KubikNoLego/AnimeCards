from aiogram import Router, F
from aiogram.types import Message, FSInputFile, InputMediaPhoto, InputMediaVideo, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.filters import Private
from app.keyboards.inline.pvp import (
    pvppagination, selects_card_pvp, back_to_sort, sort_inventory_kb,
    verse_filter_pagination_keyboard, rarity_filter_pagination_keyboard,
    select_slot_keyboard
)
from app.keyboards.inline.callback_datas.pvp_datas import (
    PvPPagination, SelectedCardPvP, PvPVerseFilter, PvPVerseFilterPagination,
    PvPRarityFilter, PvPRarityFilterPagination,
)
from app.messages import MText
from app.database import DB, Verse, RedisRequests, Card, UserCards, Rarity, User
from app.services.inventory import sort_inventory
from app.utils.consts import RARITY_VALUE_RANGES, RARITY_EMOJIES, SLOT_RARITY_MAP
from app.utils.card_formater import format_card, show_inventory_card
import random

from app.utils.pvp_utils import format_inv, calculate_deck_value, battle_decks, format_battle_result
from datetime import datetime, timezone

router = Router()

@router.message(F.text == "⚔️ Дуэли", Private())
async def _(message:Message,session:AsyncSession):
    db = DB(session)
    daily_verse_id = await RedisRequests.daily_verse()
    daily_verse = await session.scalar(select(Verse).filter_by(id=daily_verse_id)) if daily_verse_id else None
    user = await db.user.get_user(message.from_user.id)

    if not user.clan_member:
        await message.answer("user_not_in_clan_pvp")
        return
    
    if not user.battle_inventory:
        await db.pvp.create_battle_inventory(user)

    # Проверяем, есть ли пользователь в очереди
    in_queue = await db.pvp.get_search_queue_entry(user.id) is not None

    await message.answer(await format_inv(user.battle_inventory, daily_verse),
                        reply_markup=await selects_card_pvp(in_queue))


@router.callback_query(PvPPagination.filter())
async def _(callback: CallbackQuery, callback_data: PvPPagination,
            session: AsyncSession, state: FSMContext):
    """Обработчик callback для пагинации инвентаря с фильтрацией."""
    try:

        user = await DB(session).user.get_user(callback.from_user.id)

        if user and user.inventory and len(user.inventory) > 0:
            # Получаем текущие фильтры из FSM
            data = await state.get_data()
            selected_verse_name = data.get('selected_verse_name', None)
            selected_rarity_name = data.get('selected_rarity_name', None)
            
            card, total_cards = await sort_inventory(user.id,
                                        selected_rarity_name, 
                                        selected_verse_name,
                                        callback_data.p - 1, session)

            if not card:
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

            card_index = callback_data.p - 1

            # Проверка валидности индекса карты для отфильтрованного списка
            if 0 <= card_index < total_cards:
                await show_inventory_card(callback, total_cards,
                                        card, card_index, pvppagination)
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


@router.callback_query(F.data == "reset_sort_filters_pvp")
async def reset_sort_filters_callback(callback: CallbackQuery,
                                    state: FSMContext):
    """Обработчик callback для сброса фильтров сортировки."""
    try:
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
            
@router.callback_query(F.data == "sort_inventory_pvp")
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

@router.callback_query(PvPVerseFilterPagination.filter())
async def verse_filter_pagination_callback(callback: CallbackQuery,
                callback_data: PvPVerseFilterPagination, session: AsyncSession):
    """Обработчик callback для пагинации фильтра по вселенной."""
    try:
        # Получаем пользователя
        user = await DB(session).user.get_user(callback.from_user.id)
        
        if not user or not user.inventory:
            await callback.answer(MText.get("inventory_empty"), show_alert=True)
            return
        
        # Получаем уникальные вселенные из карточек пользователя
        user_verses = list({card.verse for card in user.inventory if card.verse})
        # Сортируем по id
        user_verses.sort(key=lambda v: v.id)
        
        if not user_verses:
            await callback.answer(MText.get("inventory_empty"), show_alert=True)
            return
        
        total_pages = (len(user_verses) + 3) // 4  # 4 вселенные на страницу
        current_page = callback_data.p

        if 1 <= current_page <= total_pages:
            # Создаем клавиатуру с обновленными кнопками пагинации
            keyboard = await verse_filter_pagination_keyboard(current_page,
                                                            verses=user_verses)
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


@router.callback_query(PvPVerseFilter.filter())
async def verse_filter_callback(callback: CallbackQuery,
        callback_data: PvPVerseFilter, session: AsyncSession,
        state: FSMContext):
    """Обработчик callback для выбора конкретной вселенной."""
    try:
        # Получаем объект вселенной из базы данных по ID
        verse = await session.get(Verse, callback_data.verse_id)
        if not verse:
            await callback.answer(MText.get("verse_not_found"), show_alert=True)
            return

        # Сохраняем выбранное название вселенной в FSM
        await state.update_data(selected_verse_name=verse.name)

        verse_selected_message = MText.get("verse_selected").format(
            verse_name=verse.name)

        # Создаем клавиатуру для подтверждения выбора
        builder = await back_to_sort()

        # Обновляем сообщение с подтверждением выбора
        await callback.message.edit_text(
            text=verse_selected_message,
            reply_markup=builder
        )
        await callback.answer(MText.get("verse_selected_success").format(
            verse_name=verse.name))
    except Exception as e:
        logger.error(
            f"Ошибка при обработке callback выбора вселенной: {e}")
        await callback.answer(MText.get("processing_error"),
                            show_alert=True)


@router.callback_query(F.data == "sort_by_rarity_pvp")
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


@router.callback_query(PvPRarityFilterPagination.filter())
async def rarity_filter_pagination_callback(callback: CallbackQuery,
        callback_data: PvPRarityFilterPagination, session: AsyncSession):
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


@router.callback_query(PvPRarityFilter.filter())
async def rarity_filter_callback(callback: CallbackQuery,
        callback_data: PvPRarityFilter, session: AsyncSession,
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


@router.callback_query(SelectedCardPvP.filter())
async def selected_card_pvp_callback(callback: CallbackQuery,
        callback_data: SelectedCardPvP, session: AsyncSession,
        state: FSMContext):
    """Обработчик callback для выбора карты для PvP."""
    try:
        user = await DB(session).user.get_user(callback.from_user.id)
        
        if not user or not user.inventory:
            await callback.answer(MText.get("inventory_empty"), show_alert=True)
            return
        
        # Проверяем, находится ли пользователь в очереди поиска
        in_queue = await DB(session).pvp.get_search_queue_entry(user.id) is not None
        if in_queue:
            await callback.answer("⚠️ Нельзя изменять колоду когда вы в очереди поиска!", show_alert=True)
            return
        
        # Получаем текущие фильтры из FSM
        data = await state.get_data()
        selected_verse_name = data.get('selected_verse_name', None)
        selected_rarity_name = data.get('selected_rarity_name', None)
        
        # Получаем отфильтрованные карты
        conditions = [UserCards.user_id == user.id]
        if selected_rarity_name:
            conditions.append(Card.rarity_name == selected_rarity_name)
        if selected_verse_name:
            conditions.append(Card.verse_name == selected_verse_name)
        
        stmt = select(Card).join(UserCards).where(and_(*conditions)).order_by(UserCards.id)
        filtered_cards = await session.scalars(stmt)
        filtered_cards = filtered_cards.all()
        
        if not filtered_cards:
            await callback.answer(MText.get("filter_no_results"), show_alert=True)
            return
        
        # Получаем индекс карты
        card_index = callback_data.c - 1
        if not (0 <= card_index < len(filtered_cards)):
            await callback.answer(MText.get("invalid_page"), show_alert=True)
            return
        
        card = filtered_cards[card_index]
        
        # Сохраняем ID выбранной карты в FSM
        await state.update_data(selected_card_id=card.id)
        
        # Определяем, является ли карта лимитированной
        is_limited = card.rarity_name == "Лимитированный"
        
        # Проверяем, установлена ли карта уже в какой-либо слот
        is_in_slot = False
        current_slot = None
        if user.battle_inventory:
            for slot_name in ["common", "uncommon", "mythic", "legend", "hrono"]:
                slot_card = getattr(user.battle_inventory, slot_name, None)
                if slot_card and slot_card.id == card.id:
                    is_in_slot = True
                    current_slot = slot_name
                    break
        
        card_info = await format_card(card)
        
        # Создаем клавиатуру для выбора слота
        keyboard = await select_slot_keyboard(card.rarity_name, is_limited, is_in_slot, current_slot)
        
        # Отправляем сообщение с картой и кнопкой выбора слота
        file_path = f"app/assets/cards/{card.verse.name}/{card.icon}"
        if card.icon.endswith('.mp4'):
            media = InputMediaVideo(media=FSInputFile(path=file_path))
        else:
            media = InputMediaPhoto(media=FSInputFile(path=file_path))
        
        await callback.message.edit_media(
            media=media,
            reply_markup=keyboard
        )
        await callback.message.edit_caption(
            caption=card_info,
            reply_markup=keyboard
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора карты для PvP: {e}")
        await callback.answer(MText.get("processing_error"), show_alert=True)


@router.callback_query(F.data.startswith("select_slot_"))
async def select_slot_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Обработчик callback для выбора слота для карты."""
    try:
        # Извлекаем название слота из callback_data
        slot = callback.data.split("select_slot_")[1]
        
        # Проверяем валидность слота
        valid_slots = ["common", "uncommon", "mythic", "legend", "hrono"]
        if slot not in valid_slots:
            await callback.answer("Неверный слот", show_alert=True)
            return
        
        user = await DB(session).user.get_user(callback.from_user.id)
        
        # Проверяем, находится ли пользователь в очереди поиска
        in_queue = await DB(session).pvp.get_search_queue_entry(user.id) is not None
        if in_queue:
            await callback.answer("⚠️ Нельзя изменять колоду когда вы в очереди поиска!", show_alert=True)
            return
        if not user:
            await callback.answer(MText.get("user_not_found"), show_alert=True)
            return
        
        # Получаем ID выбранной карты из FSM
        data = await state.get_data()
        card_id = data.get('selected_card_id')
        
        if not card_id:
            await callback.answer("Сначала выберите карту", show_alert=True)
            return
        
        # Получаем карту из базы данных
        card = await session.get(Card, card_id)
        if not card:
            await callback.answer("Карта не найдена", show_alert=True)
            return
        
        # Проверяем, принадлежит ли карта пользователю
        if card not in user.inventory:
            await callback.answer("Эта карта вам не принадлежит", show_alert=True)
            return
        
        # Проверяем, не установлена ли уже эта карта в каком-либо слоте
        if user.battle_inventory:
            current_slot = None
            for slot_name in ["common", "uncommon", "mythic", "legend", "hrono"]:
                slot_card = getattr(user.battle_inventory, slot_name, None)
                if slot_card and slot_card.id == card.id:
                    current_slot = slot_name
                    break
            
            # Если карта уже установлена
            if current_slot:
                # Если карта уже в выбранном слоте - ничего не делаем
                if current_slot == slot:
                    await callback.answer(
                        f"Эта карта уже установлена в слоте '{slot}'",
                        show_alert=True
                    )
                    return
                # Если карта в другом слоте и это лимитированная карта - перемещаем
                elif card.rarity_name == "Лимитированный":
                    # Удаляем карту из старого слота
                    setattr(user.battle_inventory, current_slot, None)
                    await session.commit()
                # Если карта не лимитированная - ошибка
                else:
                    await callback.answer(
                        f"Эта карта уже установлена в слоте '{current_slot}'",
                        show_alert=True
                    )
                    return
        
        # Для не-лимитированных карт проверяем, что слот соответствует редкости
        if card.rarity_name != "Лимитированный":
            expected_slots = [item for item, key in SLOT_RARITY_MAP.items() if key == card.rarity_name]
            if not expected_slots:
                await callback.answer("Неизвестная редкость карты", show_alert=True)
                return
            
            expected_slot = expected_slots[0]
            if expected_slot != slot:
                await callback.answer(
                    f"Карту редкости '{card.rarity_name}' можно поставить только в слот '{expected_slot}'",
                    show_alert=True
                )
                return
        
        # Для лимитированных карт проверяем, что нет другой лимитированной карты в других слотах
        if card.rarity_name == "Лимитированный" and user.battle_inventory:
            for slot_name in ["common", "uncommon", "mythic", "legend", "hrono"]:
                if slot_name != slot:  # Пропускаем текущий слот
                    slot_card = getattr(user.battle_inventory, slot_name, None)
                    if slot_card and slot_card.rarity_name == "Лимитированный":
                        # Удаляем старую лимитированную карту
                        setattr(user.battle_inventory, slot_name, None)
                        await session.commit()
                        break
        
        # Устанавливаем карту в слот
        db = DB(session)
        battle_inv = await db.pvp.set_card_to_slot(user, card, slot)
        
        if not battle_inv:
            await callback.answer("Ошибка при установке карты", show_alert=True)
            return
        
        # Формируем сообщение об успехе
        slot_names = {
            "common": "Обычный",
            "uncommon": "Редкий",
            "mythic": "Мифический",
            "legend": "Легендарный",
            "hrono": "Хроно"
        }
        
        success_message = f"✅ Карта '{card.name}' успешно установлена в слот '{slot_names[slot]}'!"
        
        # Проверяем, была ли в этом слоте другая карта
        old_card = getattr(battle_inv, slot, None)
        if old_card and old_card.id != card.id:
            success_message += f"\n⚠️ Предыдущая карта '{old_card.name}' была заменена."
        
        await callback.answer(success_message, show_alert=True)
        
        # Очищаем состояние FSM
        await state.update_data(selected_card_id=None)
        
        # Возвращаемся к отображению колоды
        await show_battle_inventory(callback.message, user, session)
        
    except Exception as e:
        logger.error(f"Ошибка при установке карты в слот: {e}")
        await callback.answer(MText.get("processing_error"), show_alert=True)


@router.callback_query(F.data.startswith("remove_from_slot_"))
async def remove_from_slot_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Обработчик callback для удаления карты из слота."""
    try:
        # Извлекаем название слота из callback_data
        slot = callback.data.split("remove_from_slot_")[1]
        
        # Проверяем валидность слота
        valid_slots = ["common", "uncommon", "mythic", "legend", "hrono"]
        if slot not in valid_slots:
            await callback.answer("Неверный слот", show_alert=True)
            return
        
        user = await DB(session).user.get_user(callback.from_user.id)
        
        # Проверяем, находится ли пользователь в очереди поиска
        in_queue = await DB(session).pvp.get_search_queue_entry(user.id) is not None
        if in_queue:
            await callback.answer("⚠️ Нельзя изменять колоду когда вы в очереди поиска!", show_alert=True)
            return
        
        if not user:
            await callback.answer(MText.get("user_not_found"), show_alert=True)
            return
        
        # Получаем ID выбранной карты из FSM
        data = await state.get_data()
        card_id = data.get('selected_card_id')
        
        if not card_id:
            await callback.answer("Сначала выберите карту", show_alert=True)
            return
        
        # Получаем карту из базы данных
        card = await session.get(Card, card_id)
        if not card:
            await callback.answer("Карта не найдена", show_alert=True)
            return
        
        # Проверяем, принадлежит ли карта пользователю
        if card not in user.inventory:
            await callback.answer("Эта карта вам не принадлежит", show_alert=True)
            return
        
        # Проверяем, есть ли у пользователя battle_inventory
        if not user.battle_inventory:
            await callback.answer("У вас нет колоды", show_alert=True)
            return
        
        # Проверяем, что карта действительно установлена в этом слоте
        slot_card = getattr(user.battle_inventory, slot, None)
        if not slot_card or slot_card.id != card.id:
            await callback.answer("Эта карта не установлена в этом слоте", show_alert=True)
            return
        
        # Удаляем карту из слота
        setattr(user.battle_inventory, slot, None)
        await session.commit()
        
        # Формируем сообщение об успехе
        slot_names = {
            "common": "Обычный",
            "uncommon": "Редкий",
            "mythic": "Мифический",
            "legend": "Легендарный",
            "hrono": "Хроно"
        }
        
        success_message = f"✅ Карта '{card.name}' успешно убрана из слота '{slot_names[slot]}'!"
        await callback.answer(success_message, show_alert=True)
        
        # Очищаем состояние FSM
        await state.update_data(selected_card_id=None)
        
        # Возвращаемся к отображению колоды
        await show_battle_inventory(callback.message, user, session)
        
    except Exception as e:
        logger.error(f"Ошибка при удалении карты из слота: {e}")
        await callback.answer(MText.get("processing_error"), show_alert=True)


@router.callback_query(F.data == "cancel_slot_selection")
async def cancel_slot_selection_callback(callback: CallbackQuery, session: AsyncSession):
    """Обработчик callback для отмены выбора слота."""
    try:
        user = await DB(session).user.get_user(callback.from_user.id)
        if user:
            await show_battle_inventory(callback.message, user, session)
        else:
            await callback.message.answer(MText.get("user_not_found"))
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при отмене выбора слота: {e}")
        await callback.answer(MText.get("processing_error"), show_alert=True)


@router.callback_query(F.data == "search_opponent")
async def search_opponent_callback(callback: CallbackQuery, session: AsyncSession):
    """Обработчик callback для входа в очередь поиска соперника."""
    try:
        user = await DB(session).user.get_user(callback.from_user.id)
        if not user:
            await callback.answer(MText.get("user_not_found"), show_alert=True)
            return
        
        # Проверяем, есть ли у пользователя battle_inventory
        if not user.battle_inventory:
            await callback.answer("Сначала соберите колоду!", show_alert=True)
            return
        
        # Проверяем, есть ли хотя бы одна карта в колоде
        if user.battle_inventory.total_cards_count == 0:
            await callback.answer("Ваша колода пуста! Установите хотя бы одну карту.", show_alert=True)
            return
        
        db = DB(session)
        
        # Проверяем, есть ли уже пользователь в очереди
        existing = await db.pvp.get_search_queue_entry(user.id)
        if existing:
            await callback.answer("Вы уже в очереди поиска!", show_alert=True)
            return
        
        # Вычисляем стоимость колоды пользователя
        user_deck_value = calculate_deck_value(user.battle_inventory)
        
        # Сначала пытаемся найти соперника в очереди
        opponent_data = await db.pvp.find_opponent_in_queue(user.id, user_deck_value)
        
        if opponent_data:
            # Нашли соперника в очереди!
            opponent_user, opponent_battle_inv, opponent_deck_value = opponent_data
            
            # Удаляем соперника из очереди (он уже нашел бой)
            await db.pvp.remove_from_search_queue(opponent_user.id)
            
            # Проводим бой
            result = await battle_decks(user.battle_inventory, opponent_battle_inv)
            
            # Обновляем счетчик побед
            if result.overall_winner == 1:
                user.pvp_wins += 1
            elif result.overall_winner == 2:
                opponent_user.pvp_wins += 1
            await session.commit()
            
            # Получаем daily verse для бонусов
            daily_verse_id = await RedisRequests.daily_verse()
            daily_verse = await session.scalar(select(Verse).filter_by(id=daily_verse_id)) if daily_verse_id else None
            
            # Форматируем результат
            result_text = format_battle_result(
                result, user, opponent_user,
                user.battle_inventory, opponent_battle_inv,
                daily_verse
            )
            
            # Отправляем результат
            await callback.message.answer(result_text)
            await callback.answer("⚔️ Соперник найден! Бой начинается!")
        else:
            # Не нашли соперника, добавляем пользователя в очередь
            added = await db.pvp.add_to_search_queue(user, user_deck_value)
            
            if added:
                # Получаем количество людей в очереди
                queue_count = await db.pvp.get_queue_count()
                
                await callback.message.answer(
                    f"🔍 Вы в очереди поиска соперника!\n\n"
                    f"💰 Стоимость вашей колоды: {user_deck_value} ¥\n"
                    f"👥 В очереди: {queue_count} игроков\n\n"
                    f"Ожидайте, соперник с подходящей стоимостью колоды (±20%) скоро найдется!"
                )
                await callback.answer("✅ Вы добавлены в очередь поиска!")
            else:
                await callback.answer("Не удалось добавить в очередь. Попробуйте еще раз.", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка при поиске соперника: {e}")
        await callback.answer(MText.get("processing_error"), show_alert=True)


@router.callback_query(F.data == "cancel_search")
async def cancel_search_callback(callback: CallbackQuery, session: AsyncSession):
    """Обработчик callback для выхода из очереди поиска."""
    try:
        user = await DB(session).user.get_user(callback.from_user.id)
        if not user:
            await callback.answer(MText.get("user_not_found"), show_alert=True)
            return
        
        db = DB(session)
        
        # Удаляем пользователя из очереди
        removed = await db.pvp.remove_from_search_queue(user.id)
        
        if removed:
            await callback.answer("❌ Вы вышли из очереди поиска!")
            
            await show_battle_inventory(callback.message, user, session)
        else:
            await callback.answer("Вы не в очереди поиска.", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка при выходе из очереди: {e}")
        await callback.answer(MText.get("processing_error"), show_alert=True)


async def show_battle_inventory(message, user: User, session: AsyncSession):
    """Функция для отображения battle_inventory пользователя."""
    daily_verse_id = await RedisRequests.daily_verse()
    daily_verse = await session.scalar(select(Verse).filter_by(id=daily_verse_id)) if daily_verse_id else None
    
    if not user.battle_inventory:
        db = DB(session)
        await db.pvp.create_battle_inventory(user)
    
    # Проверяем, есть ли пользователь в очереди
    in_queue = await DB(session).pvp.get_search_queue_entry(user.id) is not None
    
    rarity_emojis = {
        "Обычный": "🔵",
        "Редкий": "🟢",
        "Легендарный": "🟡",
        "Мифический": "🟠",
        "Хроно": "🔴",
        "Лимитированный": "🟣"
    }
    
    slot_names = {
        "common": "Обычный",
        "uncommon": "Редкий",
        "mythic": "Мифический",
        "legend": "Легендарный",
        "hrono": "Хроно"
    }
    
    # Функция для получения цены карты с учётом слота для лимитированных карт
    def get_card_value(card, battle_inv):
        if card.rarity_name == "Лимитированный":
            for rarity, slot in SLOT_RARITY_MAP.items():
                slot_card = getattr(battle_inv, slot, None)
                if slot_card and slot_card.id == card.id:
                    max_value = RARITY_VALUE_RANGES.get(rarity, (0, 0))[1]
                    return max_value
            return card.value
        return card.value
    
    # Формируем текст для карт
    cards_list = user.battle_inventory.cards if user.battle_inventory.total_cards_count > 0 else []
    cards_text_parts = []
    for card in cards_list:
        value = get_card_value(card, user.battle_inventory)
        bonus_text = f" (+{int(value*0.2)}) ¥" if daily_verse and card.verse_name == daily_verse.name else ""
        shiny_text = "(Shiny ✨) " if card.shiny else ""
        
        # Определяем слот карты и её редкость
        slot_text = ""
        for slot_name, slot_attr in slot_names.items():
            slot_card = getattr(user.battle_inventory, slot_name, None)
            if slot_card and slot_card.id == card.id:
                # Для лимитированных карт показываем редкость слота
                if card.rarity_name == "Лимитированный":
                    slot_text = f" [{slot_attr}]"
                break
        
        cards_text_parts.append(
            f"{rarity_emojis.get(card.rarity_name, '🟡')} {card.name}{slot_text} {shiny_text}- <b>{value} ¥{bonus_text}</b>"
        )
    
    cards_text = "\n".join(cards_text_parts) if cards_text_parts else "Пусто..."
    
    # Считаем общую стоимость с учётом изменённых цен
    total_value = sum([
        get_card_value(card, user.battle_inventory) 
        if not daily_verse or card.verse_name != daily_verse.name 
        else int(get_card_value(card, user.battle_inventory)*1.2) 
        for card in cards_list
    ])
    cards_text += f"\n\n💰 Общая стоимость: {total_value} ¥"
    
    await message.answer(
        MText.get("duels").format(cards=cards_text),
        reply_markup=await selects_card_pvp(in_queue)
    )
