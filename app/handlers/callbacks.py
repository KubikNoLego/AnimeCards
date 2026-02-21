# Стандартные библиотеки
from datetime import timedelta,timezone

MSK_TIMEZONE = timezone(timedelta(hours=3))

# Сторонние библиотеки
from html import escape
import random
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from loguru import logger

# Локальные импорты
from app.keyboards.utils import clan_create_exit, member_pagination_keyboard, sort_inventory_kb
from db import Card, User, Verse, Rarity,RedisRequests,DB, UserCards
from app.messages import MText
from app.keyboards import Pagination, ClanInvite,MemberPagination, ShopItemCallback, VerseFilterPagination, VerseFilter, RarityFilter, RarityFilterPagination, pagination_keyboard, verse_filter_pagination_keyboard, rarity_filter_pagination_keyboard
from app.StateGroups.states import ChangeDescribe,CreateClan,ClanLeader


router = Router()

@router.callback_query(F.data.startswith("delete_clan"))
async def _(callback:CallbackQuery, session: AsyncSession, state: FSMContext):
    db = DB(session)
    user = await db.get_user(callback.from_user.id)
    if user.clan_member.is_leader:
        await db.delete_clan(user.clan_member.clan_id)
        
        await callback.message.delete()
        await callback.answer("Вы удалили клан")

@router.callback_query(F.data == "change_desc_clan")
async def _(callback:CallbackQuery, session: AsyncSession, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(MText.get("clan_change_desc"))
    await state.set_state(ClanLeader.desc)

@router.callback_query(F.data.startswith("leave_clan"))
async def _(callback:CallbackQuery, session: AsyncSession, state: FSMContext):
    db = DB(session)
    user = await db.get_user(callback.from_user.id)
    if user.clan_member and user.clan_member.is_leader:
        clan = await db.get_clan(user.clan_member.clan_id)
        
        await db.delete_member(user.id)
        
        new_leader = random.choice(clan.members)
        new_leader.is_leader = True
        clan.leader_id = new_leader.user_id

        await session.commit()

        await callback.message.delete()
    elif user.clan_member:
        await db.delete_member(user.id)
        await callback.message.delete()
    await callback.answer("Вы покинули клан")


@router.callback_query(F.data.startswith("kick_"))
async def _(callback:CallbackQuery, session: AsyncSession, state: FSMContext):
    user_id = int(callback.data.split("_")[1])
    
    db = DB(session)
    user = await db.get_user(user_id)

    moder = await db.get_user(callback.from_user.id)
    clan = await db.get_clan(moder.clan_member.clan_id)

    if user.clan_member not in clan.members:
        return

    await db.delete_member(user.id)
    await callback.message.delete()
    await callback.answer("Вы успешно выгнали пользователя")
    await callback.message.bot.send_message(user_id,MText.get("u_have_been_kicked"))


@router.callback_query(MemberPagination.filter())
async def _(callback:CallbackQuery,callback_data: MemberPagination, session: AsyncSession, state: FSMContext):
    page = callback_data.p

    db = DB(session)

    user = await db.get_user(callback.from_user.id)

    if not user:
        return

    clan = await db.get_clan(user.clan_member.clan_id)

    clan_members = clan.members
    clan_members.remove(user.clan_member)

    # Проверяем, есть ли участники в клане (кроме лидера)
    if not clan_members:
        await callback.message.edit_text(text=MText.get("clan_no_members"))
        return

    current_member = (clan_members[page-1].user, clan_members[page-1])

    # Форматируем информацию об участнике
    member_info = MText.get("clan_member_info").format(
        member_name=escape(current_member[0].name),
        join_date=current_member[1].joined_at.astimezone(MSK_TIMEZONE).strftime('%d.%m.%Y %H:%M'),
        contribution=current_member[1].contribution
    )

    profile_photos = await callback.message.bot.get_user_profile_photos(current_member[0].id, limit=1)
    photo = profile_photos.photos[0][-1].file_id if profile_photos and len(profile_photos.photos) > 0 else None

    if photo:
        await callback.message.edit_media(media=InputMediaPhoto(media=photo), reply_markup=await member_pagination_keyboard(page, len(clan_members), current_member[0].id,user.clan_member.is_leader))
        await callback.message.edit_caption(caption=member_info, reply_markup=await member_pagination_keyboard(page, len(clan_members), current_member[0].id,user.clan_member.is_leader))
    else:
        await callback.message.edit_text(text=member_info, reply_markup=await member_pagination_keyboard(page, len(clan_members), current_member[0].id,user.clan_member.is_leader))

@router.callback_query(ClanInvite.filter())
async def _(callback:CallbackQuery,callback_data: ClanInvite, session: AsyncSession, state: FSMContext):
    clan_id,action = callback_data.clan_id,callback_data.act

    db = DB(session)

    match action:
        case 1:
            member = await db.create_clan_member(callback.from_user.id, clan_id)

            await callback.message.delete()
            await callback.message.answer("Приглашение принято")

            invite = await db.get_clan_invitation(clan_id,callback.from_user.id)

            await session.delete(invite)
            await session.commit()


        case 0:
            invite = await db.get_clan_invitation(clan_id,callback.from_user.id)

            await session.delete(invite)
            await session.commit()

            await callback.message.delete()
            await callback.answer("Приглашение отклонено")

@router.callback_query(F.data == "accept_create_clan")
async def _(callback:CallbackQuery, session: AsyncSession, state: FSMContext):
    db = DB(session)
    user = await db.get_user(callback.from_user.id)

    # Проверяем, достаточно ли у пользователя йен для создания клана
    clan_creation_cost = 1000
    if user.balance < clan_creation_cost:
        await callback.answer(MText.get("not_enough_yens_clan"), show_alert=True)
        return

    data = await state.get_data()

    # Списываем йены за создание клана
    user.balance -= clan_creation_cost
    await session.commit()

    await db.create_clan(data['name'],data['tag'],data['description'],callback.from_user.id)
    await callback.message.delete()
    await callback.answer(f"Клан успешно создан! Списано {clan_creation_cost} ¥")
    # Очищаем состояние пользователя после создания клана, не затрагивая другие состояния
    await state.clear()

@router.callback_query(F.data == "cancel_create_clan")
async def _(callback:CallbackQuery, session: AsyncSession, state: FSMContext):
    """Обработчик кнопки отмены создания клана"""
    # Очищаем состояние пользователя
    await state.clear()
    await callback.message.delete()
    await callback.answer("Создание клана отменено")

@router.callback_query(F.data == "create_clan")
async def _(callback:CallbackQuery, session: AsyncSession, state: FSMContext):
    db = DB(session)
    user = await db.get_user(callback.from_user.id)

    # Проверяем баланс пользователя перед созданием клана
    clan_creation_cost = 1000
    if user.balance < clan_creation_cost:
        await callback.answer(MText.get("not_enough_yens_clan"), show_alert=True)
        return

    await state.set_state(CreateClan.name)
    await callback.message.answer(MText.get("clan_name_prompt"), reply_markup=await clan_create_exit())

@router.callback_query(F.data == "delete_describe")
async def delete_describe_user(callback: CallbackQuery,session : AsyncSession, state:FSMContext):
    await callback.message.answer(MText.get("describe_updated_empty"))
    user = await DB(session).get_user(callback.from_user.id)
    user.profile.describe = ""
    await session.commit()

@router.callback_query(F.data == "change_describe")
async def change_describe_user(callback: CallbackQuery, session: AsyncSession, state:FSMContext):
    await state.set_state(ChangeDescribe.text)
    await callback.message.answer(MText.get("change_describe_prompt"))

@router.callback_query(F.data == "reset_sort_filters")
async def reset_sort_filters_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик callback для сброса фильтров сортировки."""
    try:

        # Очищаем данные FSM
        await state.clear()

        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад к сортировке", callback_data="sort_inventory")
        builder.adjust(1)

        # Обновляем сообщение с подтверждением сброса
        await callback.message.edit_text(
            text=MText.get("filters_reset_success"),
            reply_markup=builder.as_markup()
        )
        await callback.answer(MText.get("filters_reset_success"))
    except Exception as e:
            logger.error(f"Ошибка при сбросе фильтров сортировки: {e}")
            await callback.answer(MText.get("filters_reset_error"), show_alert=True)

@router.callback_query(F.data == "sort_inventory")
async def sort_inventory_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
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
                logger.warning(f"Не удалось удалить сообщение с фото, используем edit_text: {delete_error}")
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
            logger.error(f"Ошибка при обработке callback выбора способа сортировки инвентаря: {e}")
            await callback.answer(MText.get("select_sort"), show_alert=True)

@router.callback_query(ShopItemCallback.filter())
async def shop_item_callback(callback: CallbackQuery, callback_data: ShopItemCallback, session: AsyncSession):
    """Обработчик callback для покупки карточки из магазина."""
    try:

        # Получаем карточку из базы данных
        card = await session.scalar(select(Card).filter_by(id=callback_data.item_id))

        if not card:
            await callback.answer(MText.get("card_not_found"), show_alert=True)
            return

        # Получаем пользователя
        user = await DB(session).get_user(callback.from_user.id)

        if not user:
            await callback.answer(MText.get("user_not_found_short"), show_alert=True)
            return

        # Проверяем, достаточно ли у пользователя йен
        if user.balance < int(card.value*1.7):
            await callback.answer(MText.get("not_enough_yens"), show_alert=True)
            return

        # Проверяем, есть ли уже эта карточка у пользователя
        if card in user.inventory:
            await callback.answer(MText.get("card_already_owned"), show_alert=True)
            return

        # Создаем клавиатуру с подтверждением покупки
        builder = InlineKeyboardBuilder()
        builder.button(text="💰 Купить", callback_data=f"buy_card_{card.id}")
        builder.button(text="🔙 Отмена", callback_data="cancel_buy")
        builder.adjust(2)

        # Форматируем информацию о карточке
        card_info = MText.get("card").format(name=card.name,
                                            verse=card.verse_name,
                                            rarity=card.rarity_name,
                                            value=str(card.value)) + f"\n\nЦена покупки: {int(card.value * 1.7)} ¥"

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

        await callback.message.delete()
        await callback.answer()

    except Exception as e:
            logger.error(f"Ошибка при обработке покупки карточки: {str(e)}", exc_info=True)
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
                await callback.answer(MText.get("card_not_found"), show_alert=True)
                return

            # Проверяем, достаточно ли у пользователя йен
            if user.balance < int(card.value*1.7):
                await callback.answer(MText.get("not_enough_yens"), show_alert=True)
                return

            # Проверяем, есть ли уже эта карточка у пользователя
            if card in user.inventory:
                await callback.answer(MText.get("card_already_owned"), show_alert=True)
                return

            # Выполняем покупку
            user.balance -= int(card.value*1.7)
            user.inventory.append(card)

            await session.commit()

            # Удаляем сообщение с предложением покупки
            try:
                await callback.message.delete()
            except Exception as delete_error:
                logger.warning(f"Не удалось удалить сообщение с предложением покупки: {str(delete_error)}")

            # Отправляем подтверждение о покупке
            await callback.message.answer(MText.get("purchase_success").format(card_name=card.name, price=int(card.value*1.7)))

            await callback.answer(MText.get("purchase_success").split('\n')[0])
        else:
            await callback.message.answer(MText.get("shop_items_changed"))

    except Exception as e:
            logger.error(f"Ошибка при покупке карточки: {str(e)}", exc_info=True)
            await callback.answer(MText.get("purchase_error"), show_alert=True)

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
        await callback.message.answer(MText.get("purchase_cancelled"))
        await callback.answer(MText.get("purchase_cancelled"))
    except Exception as e:
            logger.error(f"Ошибка при отмене покупки: {str(e)}")
            await callback.answer(MText.get("cancel_error"), show_alert=True)

@router.callback_query(VerseFilterPagination.filter())
async def verse_filter_pagination_callback(callback: CallbackQuery, callback_data: VerseFilterPagination, session: AsyncSession):
    """Обработчик callback для пагинации фильтра по вселенной."""
    try:

        verses = await session.scalars(select(Verse))
        verses = verses.all()
        total_pages = len(verses)
        current_page = callback_data.p

        if 1 <= current_page <= total_pages:
            # Создаем клавиатуру с обновленными кнопками пагинации
            keyboard = await verse_filter_pagination_keyboard(current_page,verses=verses)
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
            logger.error(f"Ошибка при обработке callback пагинации фильтра по вселенной: {e}")
            await callback.answer(MText.get("processing_error"), show_alert=True)

@router.callback_query(VerseFilter.filter())
async def verse_filter_callback(callback: CallbackQuery, callback_data: VerseFilter, session: AsyncSession, state: FSMContext):
    """Обработчик callback для выбора конкретной вселенной."""
    try:

        # Сохраняем выбранное название вселенной в FSM
        await state.update_data(selected_verse_name=callback_data.verse_name)

        verse_selected_message = MText.get("verse_selected").format(verse_name=callback_data.verse_name)

        # Создаем клавиатуру для подтверждения выбора
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад к сортировке", callback_data="sort_inventory")
        builder.adjust(1)

        # Обновляем сообщение с подтверждением выбора
        await callback.message.edit_text(
            text=verse_selected_message,
            reply_markup=builder.as_markup()
        )
        await callback.answer(MText.get("verse_selected_success").format(verse_name=callback_data.verse_name))
    except Exception as e:
            logger.error(f"Ошибка при обработке callback выбора вселенной: {e}")
            await callback.answer(MText.get("processing_error"), show_alert=True)

@router.callback_query(F.data == "sort_by_rarity")
async def sort_by_rarity_callback(callback: CallbackQuery, session: AsyncSession):
    """Обработчик callback для сортировки по редкости."""
    try:

        # Получаем все редкости из базы данных
        rarities = await session.scalars(select(Rarity))
        rarities = rarities.all()

        # Создаем клавиатуру с первой страницей редкостей
        keyboard = await rarity_filter_pagination_keyboard(1, rarities=rarities)

        select_rarity_message = MText.get("select_rarity")

        # Обновляем сообщение с новой клавиатурой
        await callback.message.edit_text(
            text=select_rarity_message,
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
            logger.error(f"Ошибка при обработке callback сортировки по редкости: {e}")
            await callback.answer(MText.get("processing_error"), show_alert=True)

@router.callback_query(RarityFilterPagination.filter())
async def rarity_filter_pagination_callback(callback: CallbackQuery, callback_data: RarityFilterPagination, session: AsyncSession):
    """Обработчик callback для пагинации фильтра по редкости."""
    try:

        rarities = await session.scalars(select(Rarity))
        rarities = rarities.all()
        total_pages = len(rarities)
        current_page = callback_data.p

        if 1 <= current_page <= total_pages:
            # Создаем клавиатуру с обновленными кнопками пагинации
            keyboard = await rarity_filter_pagination_keyboard(current_page, rarities=rarities)
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
            logger.error(f"Ошибка при обработке callback пагинации фильтра по редкости: {e}")
            await callback.answer(MText.get("processing_error"), show_alert=True)

@router.callback_query(RarityFilter.filter())
async def rarity_filter_callback(callback: CallbackQuery, callback_data: RarityFilter, session: AsyncSession, state: FSMContext):
    """Обработчик callback для выбора конкретной редкости."""
    try:

        # Сохраняем выбранное название редкости в FSM
        await state.update_data(selected_rarity_name=callback_data.rarity_name)

        rarity_selected_message = MText.get("rarity_selected").format(rarity_name=callback_data.rarity_name)

        # Создаем клавиатуру для подтверждения выбора
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад к сортировке", callback_data="sort_inventory")
        builder.adjust(1)

        # Обновляем сообщение с подтверждением выбора
        await callback.message.edit_text(
            text=rarity_selected_message,
            reply_markup=builder.as_markup()
        )
        await callback.answer(MText.get("rarity_selected_success").format(rarity_name=callback_data.rarity_name))
    except Exception as e:
            logger.error(f"Ошибка при обработке callback выбора редкости: {e}")
            await callback.answer(MText.get("processing_error"), show_alert=True)

@router.callback_query(Pagination.filter())
async def inventory_pagination_callback(callback: CallbackQuery, callback_data: Pagination, session: AsyncSession, state: FSMContext):
    """Обработчик callback для пагинации инвентаря с фильтрацией."""
    try:

        db = DB(session)

        user = await db.get_user(callback.from_user.id)



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

                conditions.append(Card.shiny == False)
            
            stmt = select(Card).join(UserCards).where(and_(*conditions))
            filtered_cards = await session.scalars(stmt)
            if callback_data.m == 2:
                filtered_cards = await db.get_missing_shiny_cards(user.id)

            filtered_cards = filtered_cards.all()

            if not filtered_cards:
                # Если нет карт, соответствующих фильтрам
                filter_no_results_message = MText.get("filter_no_results")

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
                await show_inventory_card(callback, user, card_index, filtered_cards,callback_data.m)
            else:
                logger.warning(f"Неверный индекс карты: {callback_data.p} для пользователя {user.id}")
                await callback.message.answer(MText.get("inventory_empty"))
        else:
            await callback.message.answer(MText.get("inventory_empty"))

    except Exception as e:
            logger.error(f"Ошибка при обработке callback пагинации инвентаря: {e}")
            await callback.answer(MText.get("processing_error"), show_alert=True)

async def show_inventory_card(callback: CallbackQuery, user: User, card_index: int, filtered_cards: list = None, mode = 0):
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

    keyboard = await pagination_keyboard(card_index + 1, len(cards),mode)
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