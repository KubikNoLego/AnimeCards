from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, InputMediaVideo
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select
from loguru import logger

from app.keyboards import (back_to_sort, sort_inventory_kb,
                    verse_filter_pagination_keyboard, pagination_keyboard,
                    rarity_filter_pagination_keyboard,trade_action_kb,
                    TradeVerseFilter, TradePagination,
                    TradeVerseFilterPagination,
                    TradeRarityFilter, TradeRarityFilterPagination,
                    SelectedCard)
from app.messages import MText
from db import DB, Card, Verse, Rarity, UserCards, User, Trade


router = Router()


@router.callback_query(F.data == "accept_trade")
async def selected_card_callback(callback: CallbackQuery,
                                session: AsyncSession):
    db = DB(session)
    
    
    trade = await db.get_trade(callback.from_user.id)
    
    if not trade:
        return
    
    is_complete = await db.complete_trade(trade)
    
    if not is_complete:
        await callback.answer(MText.get("error_completing"))
        return

    await callback.message.answer(MText.get("trade_succes"))
    await callback.bot.send_message(trade.partner_id, MText.get("trade_succes"))
    
    await callback.message.delete()

@router.callback_query(F.data == "reject_trade")
async def selected_card_callback(callback: CallbackQuery,
                                session: AsyncSession):
    db = DB(session)
    
    trade = await db.get_trade(callback.from_user.id)
    
    if not trade:
        return

    await callback.message.answer(MText.get("u_reject_trade"))
    await callback.bot.send_message(trade.partner_id, MText.get("user_reject_your_offer"))
    
    trade.partner_card = None
    trade.partner_id = None
    trade.partner_added_at = None
    
    await callback.message.delete()

@router.callback_query(SelectedCard.filter())
async def selected_card_callback(callback: CallbackQuery,
                callback_data: SelectedCard, session: AsyncSession):
    db = DB(session)
    user = await db.get_user(callback.from_user.id)
    
    # Проверяем, является ли пользователь партнером другого игрока
    trade = await session.scalar(select(Trade).filter_by(
        partner_id=user.id))
    
    if trade:
        # Проверяем, что выбранная карта доступна для обмена
        partner = await db.get_user(trade.user_id)
        if partner:
            partner_card_ids = [card.id for card in partner.inventory]
            if callback_data.card_id in partner_card_ids:
                await callback.message.answer("Эту карту нельзя выбрать, так как она уже есть у вашего партнера.")
                return

        # Пользователь является партнером, отправляем карту владельцу трейда
        card = await db.get_card(callback_data.card_id)

        await callback.message.answer(MText.get("send_message"))
        await callback.message.delete()

        card_info = MText.get("card").format(name=card.name,
                                                    verse=card.verse_name,
                                                    rarity=card.rarity_name,
                                                    value=card.value)
        card_info = card_info + ("\n\n✨ Shiny" if card.shiny else "")

        await callback.bot.send_photo(trade.user_id, photo=FSInputFile(
                    path=f"app/icons/{card.verse.name}/{card.icon}"),
                    caption=card_info,
                    reply_markup=await trade_action_kb())
        
        trade.partner_card = card.id
        
        await session.commit()
        
        return

    # Проверяем, есть ли уже активный трейд у пользователя
    existing_trade = await db.get_trade(user.id)

    if existing_trade:
        await callback.message.answer(MText.get("trade_exist"))
        await db.delete_trade(user.id)

    # Создаем новый трейд
    trade = await db.create_trade(user.id, callback_data.card_id)
    bot_info = await callback.message.bot.get_me()
    trade_link = f"https://t.me/{bot_info.username}?start=t_{user.id}"

    await callback.message.answer(MText.get("trade_created").format(
        link=trade_link)
        )
    await callback.message.delete()



@router.callback_query(F.data == "reset_sort_filters_trade")
async def reset_sort_filters_callback(callback: CallbackQuery,
                                    state: FSMContext):
    """Обработчик callback для сброса фильтров сортировки."""
    try:

        # Очищаем данные FSM
        await state.clear()

        builder = await back_to_sort(True)

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

@router.callback_query(F.data == "sort_inventory_trade")
async def sort_inventory_callback(callback: CallbackQuery,
                                session: AsyncSession, state: FSMContext):
    """Обработчик callback для выбора способа сортировки инвентаря."""
    try:
        select_sort_message = MText.get("select_sort")

        # Получаем текущие выбранные значения из FSM
        data = await state.get_data()
        selected_verse_name = data.get('selected_verse_name_trade', None)
        selected_rarity_name = data.get('selected_rarity_name_trade', None)

        kb = await sort_inventory_kb(selected_rarity_name,selected_verse_name,
                                    True)

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

@router.callback_query(TradeVerseFilterPagination.filter())
async def verse_filter_pagination_callback(callback: CallbackQuery,
                callback_data: TradeVerseFilterPagination, session: AsyncSession):
    """Обработчик callback для пагинации фильтра по вселенной."""
    try:

        # Получаем все вселенные, у которых есть хотя бы одна карта в инвентаре пользователя
        user = await DB(session).get_user(callback.from_user.id)
        
        verses = await session.scalars(
            select(Verse).join(Card).join(UserCards).filter(
                UserCards.user_id == user.id
            ).distinct()
        )
        verses = verses.all()
        total_pages = len(verses)
        current_page = callback_data.p

        if 1 <= current_page <= total_pages:
            # Создаем клавиатуру с обновленными кнопками пагинации
            keyboard = await verse_filter_pagination_keyboard(current_page,
                                                            verses=verses,
                                                            trade = True)
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

@router.callback_query(TradeVerseFilter.filter())
async def verse_filter_callback(callback: CallbackQuery,
                        callback_data: TradeVerseFilter, session: AsyncSession,
                        state: FSMContext):
    """Обработчик callback для выбора конкретной вселенной."""
    try:
        # Получаем объект вселенной из базы данных по ID
        verse = await session.get(Verse, callback_data.verse_id)
        if not verse:
            await callback.answer(MText.get("verse_not_found"), show_alert=True)
            return

        # Сохраняем выбранное название вселенной в FSM
        await state.update_data(selected_verse_name_trade=verse.name)

        verse_selected_message = MText.get("verse_selected").format(
            verse_name=verse.name)

        # Создаем клавиатуру для подтверждения выбора
        builder = await back_to_sort(True)

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

@router.callback_query(F.data == "sort_by_rarity_trade")
async def sort_by_rarity_callback(callback: CallbackQuery,
                                session: AsyncSession):
    """Обработчик callback для сортировки по редкости."""
    try:

        # Получаем все редкости из базы данных
        rarities = await session.scalars(select(Rarity))
        rarities = rarities.all()

        # Создаем клавиатуру с первой страницей редкостей
        keyboard = await rarity_filter_pagination_keyboard(1,
                                                        rarities=rarities,
                                                        trade= True)

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

@router.callback_query(TradeRarityFilterPagination.filter())
async def rarity_filter_pagination_callback(callback: CallbackQuery,
                callback_data: TradeRarityFilterPagination, session: AsyncSession):
    """Обработчик callback для пагинации фильтра по редкости."""
    try:

        rarities = await session.scalars(select(Rarity))
        rarities = rarities.all()
        total_pages = len(rarities)
        current_page = callback_data.p

        if 1 <= current_page <= total_pages:
            # Создаем клавиатуру с обновленными кнопками пагинации
            keyboard = await rarity_filter_pagination_keyboard(current_page,
                                                            rarities=rarities,
                                                            trade=True)
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

@router.callback_query(TradeRarityFilter.filter())
async def rarity_filter_callback(callback: CallbackQuery,
                    callback_data: TradeRarityFilter, session: AsyncSession,
                    state: FSMContext):
    """Обработчик callback для выбора конкретной редкости."""
    try:

        # Сохраняем выбранное название редкости в FSM
        await state.update_data(selected_rarity_name_trade=callback_data.rarity_name)

        rarity_selected_message = MText.get("rarity_selected").format(
            rarity_name=callback_data.rarity_name)

        # Создаем клавиатуру для подтверждения выбора
        builder = await back_to_sort(True)

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

@router.callback_query(TradePagination.filter())
async def inventory_pagination_callback(callback: CallbackQuery,
                    callback_data: TradePagination, session: AsyncSession, 
                    state: FSMContext):
    """Обработчик callback для пагинации инвентаря с фильтрацией."""
    try:

        user = await DB(session).get_user(callback.from_user.id)

        if user and user.inventory and len(user.inventory) > 0:
            # Получаем текущие фильтры из FSM
            data = await state.get_data()
            selected_verse_name = data.get('selected_verse_name_trade', None)
            selected_rarity_name = data.get('selected_rarity_name_trade', None)
            
            # Проверяем, является ли пользователь партнером другого игрока
            trade = await session.scalar(select(Trade).filter_by(
                partner_id=user.id))
            
            partner_cards = []
            if trade:
                # Получаем карты партнера
                partner = await DB(session).get_user(trade.user_id)
                if partner:
                    partner_cards = [card.id for card in partner.inventory]
            
            conditions = [UserCards.user_id == user.id]
            if selected_rarity_name:
                conditions.append(Card.rarity_name == selected_rarity_name)
            if selected_verse_name:
                conditions.append(Card.verse_name == selected_verse_name)
            
            stmt = select(Card).join(UserCards).where(and_(*conditions)).order_by(UserCards.id)
            filtered_cards = await session.scalars(stmt)
            filtered_cards = filtered_cards.all()

            # Фильтруем карты, исключая те, которые есть у партнера
            if partner_cards:
                filtered_cards = [card for card in filtered_cards 
                                if card.id not in partner_cards]

            if not filtered_cards:
                # Если нет карт, соответствующих фильтрам
                filter_no_results_message = MText.get("filter_no_results")

                # Проверяем, является ли пользователь партнером
                if trade:
                    # Удаляем partner_id, так как у партнера нет доступных карт
                    trade.partner_id = None
                    await session.commit()
                    
                    # Уведомляем пользователя
                    await callback.message.answer("У вас нет карт для обмена. Партнерство расторгнуто.")
                
                # Создаем клавиатуру с кнопкой возврата к сортировке
                builder = await back_to_sort(True)
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

    keyboard = await pagination_keyboard(card_index + 1, len(cards), True, card.id)

    if card.icon.lower().endswith(".mp4"):
        media = InputMediaVideo(media=FSInputFile(
            path=f"app/icons/{card.verse.name}/{card.icon}"))
    else:
        media = media=InputMediaPhoto(media=FSInputFile(
                path=f"app/icons/{card.verse.name}/{card.icon}"))

    try:
        await callback.message.edit_media(
            media=media,
            reply_markup=keyboard
        )
        await callback.message.edit_caption(
            caption=card_info,
            reply_markup=keyboard
        )

    except Exception as e:
        logger.warning(f"Не удалось отредактировать сообщение: {e}")

