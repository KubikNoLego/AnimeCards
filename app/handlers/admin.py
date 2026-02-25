from datetime import datetime, timedelta, timezone, timedelta
from html import escape
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from loguru import logger
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db import User, Card, Verse, VipSubscription, DB
from app.filters import Private

# Создаем таймзону для Москвы (UTC+3)
MSK_TIMEZONE = timezone(timedelta(hours=3))

# ID администратора (из main.py видно что это 5027089008)
ADMIN_ID = 5027089008

router = Router()

async def get_stats_text(session: AsyncSession) -> str:
    """Получение текста со статистикой бота"""
    # Количество пользователей
    users_count = await session.scalar(select(func.count(User.id)))
    
    # Количество карточек
    cards_count = await session.scalar(select(func.count(Card.id)))
    
    # Количество вселенных
    verses_count = await session.scalar(select(func.count(Verse.id)))
    
    # Количество VIP пользователей
    vip_count = await session.scalar(select(func.count(VipSubscription.id)))
    
    return (
        f"<b>📊 Статистика бота AnimeCards</b>\n\n"
        f"<b>Пользователи:</b> {users_count}\n"
        f"<b>Карточки:</b> {cards_count}\n"
        f"<b>Вселенные:</b> {verses_count}\n"
        f"<b>VIP пользователей:</b> {vip_count}\n\n"
    )


@router.message(Command("admin"), Private())
async def admin_panel(message: Message, session: AsyncSession):
    """Главное меню админ-панели"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа к админ-панели")
        return
    
    await message.answer(
        "👋 <b>Добро пожаловать в админ-панель AnimeCards!</b>\n\n"
        "Выберите действие из меню ниже:",
        reply_markup=admin_kb()
    )


@router.message(F.text == "📊 Статистика", Private())
async def stats_handler(message: Message, session: AsyncSession):
    """Показ статистики бота"""
    if message.from_user.id != ADMIN_ID:
        return
    
    text = await get_stats_text(session)
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "👤 Поиск пользователя", Private())
async def search_user_start(message: Message, state: FSMContext):
    """Начало поиска пользователя"""
    if message.from_user.id != ADMIN_ID:
        return
    
    await message.answer(
        "👤 <b>Поиск пользователя</b>\n\n"
        "Введите ID пользователя или username (с @):",
        parse_mode="HTML"
    )
    await state.set_state("admin_search_user")


@router.message(StateFilter("admin_search_user"), Private())
async def search_user_result(message: Message, session: AsyncSession, state: FSMContext):
    """Результат поиска пользователя"""
    if message.from_user.id != ADMIN_ID:
        return
    
    db = DB(session)
    
    # Определяем, что ввел пользователь
    text = message.text.strip()
    
    if text.startswith('@'):
        username = text[1:]
        # Ищем по username
        user = await session.scalar(select(User).filter_by(username=username))
    else:
        try:
            user_id = int(text)
            user = await db.get_user(user_id)
        except ValueError:
            await message.answer("❌ Введите корректный ID или username")
            return
    
    if not user:
        await message.answer("❌ Пользователь не найден")
        await state.clear()
        return
    
    # Формируем информацию о пользователе
    place = await db.get_user_place_on_top(user)
    
    vip_status = "✅ Да" if user.vip else "❌ Нет"
    vip_end = ""
    if user.vip:
        vip_end = f"\n⏰ VIP до: {user.vip.end_date.strftime('%d.%m.%Y %H:%M')}"
    
    clan_info = ""
    if user.clan_member:
        clan_info = f"\n🏰 Клан: [{user.clan_member.clan.tag}] {user.clan_member.clan.name}"
    
    text = (
        f"<b>👤 Информация о пользователе</b>\n\n"
        f"<b>ID:</b> {user.id}\n"
        f"<b>Имя:</b> {escape(user.name)}\n"
        f"<b>Username:</b> @{user.username if user.username else 'нет'}\n"
        f"<b>Баланс:</b> 💰{user.balance}\n"
        f"<b>Место в топе:</b> #{place}\n"
        f"<b>Карточек:</b> {len(user.inventory)} шт.\n"
        f"<b>VIP:</b> {vip_status}{vip_end}\n"
        f"<b>Дата регистрации:</b> {user.profile.joined.strftime('%d.%m.%Y')}{clan_info}"
    )
    
    # Клавиатура действий с пользователем
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Изменить баланс", callback_data=f"adm_bal_{user.id}")
    kb.button(text="⭐ VIP", callback_data=f"adm_vip_{user.id}")
    kb.button(text="📋 Инвентарь", callback_data=f"adm_inv_{user.id}")
    kb.adjust(2, 1)
    
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await state.clear()


@router.message(F.text == "💰 Изменить баланс", Private())
async def change_balance_start(message: Message, state: FSMContext):
    """Начало изменения баланса"""
    if message.from_user.id != ADMIN_ID:
        return
    
    await message.answer(
        "💰 <b>Изменение баланса</b>\n\n"
        "Введите ID пользователя:",
        parse_mode="HTML"
    )
    await state.set_state("admin_balance_id")


@router.message(StateFilter("admin_balance_id"), Private())
async def change_balance_amount(message: Message, session: AsyncSession, state: FSMContext):
    """Ввод суммы для изменения баланса"""
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        user_id = int(message.text.strip())
        user = await DB(session).get_user(user_id)
        
        if not user:
            await message.answer("❌ Пользователь не найден")
            await state.clear()
            return
        
        await state.update_data(user_id=user_id)
        await message.answer(
            f"💰 <b>Изменение баланса</b>\n\n"
            f"Пользователь: {escape(user.name)}\n"
            f"Текущий баланс: 💰{user.balance}\n\n"
            f"Введите новый баланс или сумму для изменения (+/-):",
            parse_mode="HTML"
        )
        await state.set_state("admin_balance_amount")
        
    except ValueError:
        await message.answer("❌ Введите корректный ID")
        await state.clear()


@router.message(StateFilter("admin_balance_amount"), Private())
async def change_balance_apply(message: Message, session: AsyncSession, state: FSMContext):
    """Применение изменения баланса"""
    if message.from_user.id != ADMIN_ID:
        return
    
    text = message.text.strip()
    db = DB(session)
    
    data = await state.get_data()
    user_id = data.get("user_id")
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("❌ Пользователь не найден")
        await state.clear()
        return
    
    try:
        if text.startswith('+') or text.startswith('-'):
            # Изменение на сумму
            amount = int(text)
            new_balance = user.balance + amount
        else:
            # Установка нового баланса
            new_balance = int(text)
        
        if new_balance < 0:
            await message.answer("❌ Баланс не может быть отрицательным")
            return
        
        # Обновляем баланс
        await session.execute(
            update(User).where(User.id == user_id).values(balance=new_balance)
        )
        await session.commit()
        
        await message.answer(
            f"✅ <b>Баланс изменён!</b>\n\n"
            f"Пользователь: {escape(user.name)}\n"
            f"Было: 💰{user.balance}\n"
            f"Стало: 💰{new_balance}",
            parse_mode="HTML"
        )
        logger.info(f"ADMIN: Баланс пользователя {user_id} изменён с {user.balance} на {new_balance}")
        
    except ValueError:
        await message.answer("❌ Введите корректное число")
        return
    
    await state.clear()


@router.message(F.text == "⭐ VIP управление", Private())
async def vip_management_start(message: Message, state: FSMContext):
    """Начало управления VIP"""
    if message.from_user.id != ADMIN_ID:
        return
    
    await message.answer(
        "⭐ <b>VIP управление</b>\n\n"
        "Введите ID пользователя:",
        parse_mode="HTML"
    )
    await state.set_state("admin_vip_id")


@router.message(StateFilter("admin_vip_id"), Private())
async def vip_management_days(message: Message, session: AsyncSession, state: FSMContext):
    """Выбор количества дней VIP"""
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        user_id = int(message.text.strip())
        user = await DB(session).get_user(user_id)
        
        if not user:
            await message.answer("❌ Пользователь не найден")
            await state.clear()
            return
        
        await state.update_data(user_id=user_id)
        
        current_vip = "✅ Да" if user.vip else "❌ Нет"
        current_end = ""
        if user.vip:
            current_end = f"\n⏰ Текущий VIP до: {user.vip.end_date.strftime('%d.%m.%Y %H:%M')}"
        
        await message.answer(
            f"⭐ <b>VIP управление</b>\n\n"
            f"Пользователь: {escape(user.name)}\n"
            f"Текущий VIP: {current_vip}{current_end}\n\n"
            f"Введите количество дней VIP (0 - отключить, число - добавить дней):",
            parse_mode="HTML"
        )
        await state.set_state("admin_vip_days")
        
    except ValueError:
        await message.answer("❌ Введите корректный ID")
        await state.clear()


@router.message(StateFilter("admin_vip_days"), Private())
async def vip_management_apply(message: Message, session: AsyncSession, state: FSMContext):
    """Применение изменения VIP"""
    if message.from_user.id != ADMIN_ID:
        return
    
    text = message.text.strip()
    db = DB(session)
    
    try:
        days = int(text)
        data = await state.get_data()
        user_id = data.get("user_id")
        user = await db.get_user(user_id)
        
        if not user:
            await message.answer("❌ Пользователь не найден")
            await state.clear()
            return
        
        now = datetime.now(MSK_TIMEZONE)
        
        if days == 0:
            # Отключаем VIP
            if user.vip:
                await session.delete(user.vip)
                await session.commit()
                await message.answer(
                    f"✅ <b>VIP отключён!</b>\n\n"
                    f"Пользователь: {escape(user.name)}",
                    parse_mode="HTML"
                )
                logger.info(f"ADMIN: VIP отключён для пользователя {user_id}")
            else:
                await message.answer("❌ У пользователя нет VIP")
        else:
            # Добавляем или создаём VIP
            if user.vip:
                new_end = user.vip.end_date + timedelta(days=days)
                user.vip.end_date = new_end
            else:
                vip_sub = VipSubscription(
                    user_id=user_id,
                    start_date=now,
                    end_date=now + timedelta(days=days)
                )
                session.add(vip_sub)
            
            await session.commit()
            
            await message.answer(
                f"✅ <b>VIP продлён!</b>\n\n"
                f"Пользователь: {escape(user.name)}\n"
                f"Добавлено дней: {days}\n"
                f"Новая дата окончания: {user.vip.end_date.strftime('%d.%m.%Y %H:%M')}" if user.vip else "VIP активирован",
                parse_mode="HTML"
            )
            logger.info(f"ADMIN: VIP на {days} дней выдан пользователю {user_id}")
        
    except ValueError:
        await message.answer("❌ Введите корректное число")
        return
    
    await state.clear()


@router.message(F.text == "📋 Список пользователей", Private())
async def user_list(message: Message, session: AsyncSession):
    """Показ списка пользователей"""
    if message.from_user.id != ADMIN_ID:
        return
    
    # Получаем последних 10 пользователей
    result = await session.execute(
        select(User).order_by(User.id.desc()).limit(10)
    )
    users = result.scalars().all()
    
    text = "<b>📋 Последние 10 пользователей:</b>\n\n"
    
    for user in users:
        vip_mark = " ⭐" if user.vip else ""
        clan_mark = f" [{user.clan_member.clan.tag}]" if user.clan_member else ""
        text += f"• {escape(user.name)}{vip_mark}{clan_mark} - ID: {user.id}\n"
    
    await message.answer(text, parse_mode="HTML")

# Обработчики callback-кнопок для управления пользователями
@router.callback_query(F.data.startswith("adm_bal_"))
async def callback_balance(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Изменение баланса из поиска"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.replace("adm_bal_", ""))
    user = await DB(session).get_user(user_id)
    
    if user:
        await callback.message.answer(
            f"💰 <b>Изменение баланса</b>\n\n"
            f"Пользователь: {escape(user.name)}\n"
            f"Введите новый баланс или сумму для изменения (+/-):",
            parse_mode="HTML"
        )
        await state.update_data(user_id=user_id)
        await state.set_state("admin_balance_amount")
    
    await callback.answer()


@router.callback_query(F.data.startswith("adm_vip_"))
async def callback_vip(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """VIP управление из поиска"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.replace("adm_vip_", ""))
    user = await DB(session).get_user(user_id)
    
    if user:
        await callback.message.answer(
            f"⭐ <b>VIP управление</b>\n\n"
            f"Пользователь: {escape(user.name)}\n"
            f"Введите количество дней VIP (0 - отключить):",
            parse_mode="HTML"
        )
        await state.update_data(user_id=user_id)
        await state.set_state("admin_vip_days")
    
    await callback.answer()


@router.callback_query(F.data.startswith("adm_inv_"))
async def callback_inventory(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Просмотр инвентаря"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.replace("adm_inv_", ""))
    user = await DB(session).get_user(user_id)
    
    if user:
        inventory_text = "<b>📋 Инвентарь пользователя:</b>\n\n"
        for card in user.inventory[:20]:
            inventory_text += f"• {escape(card.name)} [{card.verse_name}] - {card.rarity_name}\n"
        
        if len(user.inventory) > 20:
            inventory_text += f"\n... и ещё {len(user.inventory) - 20} карточек"
        
        await callback.message.answer(inventory_text, parse_mode="HTML")
    
    await callback.answer()


@router.message(F.text == "📢 Рассылка", Private())
async def broadcast_start(message: Message, state: FSMContext):
    """Начало рассылки"""
    if message.from_user.id != ADMIN_ID:
        return
    
    await message.answer(
        "📢 <b>Рассылка</b>\n\n"
        "Перешли любое сообщение (с текстом, фото, медиа), которое хочешь разослать.",
        parse_mode="HTML"
    )
    await state.set_state("admin_broadcast")


@router.message(StateFilter("admin_broadcast"), Private())
async def broadcast_confirm(message: Message, state: FSMContext):
    """Подтверждение рассылки"""
    if message.from_user.id != ADMIN_ID:
        return
    
    # Сохраняем chat_id и message_id для копирования
    await state.update_data(
        broadcast_chat_id=message.chat.id,
        broadcast_message_id=message.message_id
    )
    
    # Показываем превью сообщения
    try:
        await message.copy_to(message.chat.id)
    except:
        pass
    
    await message.answer(
        "Отправить это сообщение всем пользователям?",
        reply_markup=InlineKeyboardBuilder()
        .button(text="✅ Да, отправить", callback_data="broadcast_send")
        .button(text="❌ Отмена", callback_data="broadcast_cancel")
        .as_markup()
    )
    await state.set_state("admin_broadcast_confirm")


@router.callback_query(StateFilter("admin_broadcast_confirm"))
async def broadcast_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Обработка кнопок рассылки"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    data = callback.data
    
    if data == "broadcast_send":
        # Отправка рассылки
        state_data = await state.get_data()
        from_chat = state_data.get("broadcast_chat_id")
        from_message_id = state_data.get("broadcast_message_id")
        
        # Получаем всех пользователей
        result = await session.execute(select(User.id))
        user_ids = result.scalars().all()
        
        success_count = 0
        fail_count = 0
        
        await callback.message.edit_text("📢 <b>Рассылка начата...</b>", parse_mode="HTML")
        
        for user_id in user_ids:
            try:
                await callback.bot.copy_message(
                    from_chat_id=from_chat,
                    chat_id=user_id,
                    message_id=from_message_id
                )
                success_count += 1
            except Exception as e:
                fail_count += 1
                logger.warning(f"Не удалось отправить пользователю {user_id}: {e}")
        
        await callback.message.edit_text(
            f"✅ <b>Рассылка завершена!</b>\n\n"
            f"Отправлено: {success_count}\n"
            f"Не удалось: {fail_count}\n"
            f"Всего: {len(user_ids)}",
            parse_mode="HTML"
        )
        
        logger.info(f"ADMIN: Рассылка отправлена {success_count} пользователям")
        await state.clear()
        await callback.answer()
    
    elif data == "broadcast_cancel":
        # Отмена рассылки
        await callback.message.edit_text("❌ Рассылка отменена")
        await state.clear()
        await callback.answer()
    
    else:
        await callback.answer()
