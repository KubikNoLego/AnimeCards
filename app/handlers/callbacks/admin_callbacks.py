from html import escape

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from db import User, DB


ADMIN_ID = 5027089008
router = Router()


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