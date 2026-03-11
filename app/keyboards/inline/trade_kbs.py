from aiogram.utils.keyboard import InlineKeyboardBuilder

from .CallbackDatas import (TradePagination)


async def trade_kb_pagination():
    builder = InlineKeyboardBuilder()

    builder.button(text="👉 Выбрать карту", callback_data=TradePagination(p=1))

    return builder.as_markup()

async def choice():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, отправить", callback_data="broadcast_send")
    builder.button(text="❌ Отмена", callback_data="broadcast_cancel")
        
    return builder.as_markup()


async def trade_action_kb():
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Принять",
                callback_data="accept_trade",
                style = "success")
    builder.button(text="❌ Отклонить",
                callback_data="reject_trade",
                style = "danger")

    return builder.as_markup()