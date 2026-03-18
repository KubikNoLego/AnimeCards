from aiogram.utils.keyboard import InlineKeyboardBuilder

from .CallbackDatas import PvPPagination

async def selects_card_pvp():
    kb = InlineKeyboardBuilder()

    kb.button(text="🔵", callback_data=PvPPagination(p=1, s=0))
    kb.button(text="🟢", callback_data=PvPPagination(p=1, s=1))
    kb.button(text="🟠", callback_data=PvPPagination(p=1, s=2))
    kb.button(text="🟡", callback_data=PvPPagination(p=1, s=3))
    kb.button(text="🔴", callback_data=PvPPagination(p=1, s=4))
    kb.button(text="Искать противника", callback_data="none")

    kb.adjust(5,1)

    return kb.as_markup()

