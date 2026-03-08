from aiogram.utils.keyboard import InlineKeyboardBuilder

from .CallbackDatas import ClanInvite, MemberPagination

async def clan_invite_kb(clan_id: int):
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Принять",
                callback_data= ClanInvite(clan_id=clan_id, act=1).pack(),
                style = "success")
    builder.button(text="❌ Отклонить",
                callback_data= ClanInvite(clan_id=clan_id, act=0).pack(),
                style = "danger")

    return builder.as_markup()

async def create_clan():
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Создать клан",callback_data="create_clan")

    return builder.as_markup()

async def clan_create():
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Создать клан",callback_data="accept_create_clan",
                style = "success")
    builder.button(text="🔄 Начать заново",callback_data="create_clan",
                style = "primary")
    builder.button(text="❌ Отмена",callback_data="cancel_create_clan",
                style = "danger")

    return builder.as_markup()

async def clan_create_exit():
    
    builder = InlineKeyboardBuilder()

    builder.button(text="❌ Отмена",callback_data="cancel_create_clan",
                style = "danger")

    return builder.as_markup()

async def clan_member():
    builder = InlineKeyboardBuilder()
    
    builder.button(text="👤 Участники",
                callback_data=MemberPagination(p=1).pack())
    builder.button(text="🚪 Покинуть",
                callback_data="leave_clan", style="danger")

    builder.adjust(1)

    return builder.as_markup()

async def clan_leader():
    builder = InlineKeyboardBuilder()
    
    builder.button(text="👤 Участники",
                callback_data=MemberPagination(p=1).pack())
    builder.button(text="🖋️ Сменить описание",
                callback_data="change_desc_clan")
    builder.button(text="🚪 Покинуть",
                callback_data="leave_clan",style="danger")
    builder.button(text="🗑️ Удалить клан",
                callback_data="delete_clan", style="danger")

    builder.adjust(1)

    return builder.as_markup()

async def member_pagination_keyboard(current_page: int, total_pages: int,
                                    id:int, leader = False):
    """Инлайн-клавиатура пагинации."""
    builder = InlineKeyboardBuilder()

    prev_10_active = current_page > 10
    prev_1_active = current_page > 1
    next_1_active = current_page < total_pages
    next_10_active = current_page <= total_pages - 10

    buttons = []

    if prev_10_active:
        buttons.append(("‹", MemberPagination(p=current_page-10).pack(),
                        "primary"))

    if prev_1_active:
        buttons.append(("←", MemberPagination(p=current_page-1).pack(),
                        "primary"))

    buttons.append((f"{current_page}/{total_pages}", "pass"))

    if next_1_active:
        buttons.append(("→", MemberPagination(p=current_page+1).pack(),
                        "primary"))

    if next_10_active:
        buttons.append(("›", MemberPagination(p=current_page+10).pack(),
                        "primary"))

    for item in buttons:
        if len(item) == 3:
            text, callback_data, style = item
            builder.button(text=text, callback_data=callback_data, style=style)
        else:
            text, callback_data = item
            builder.button(text=text, callback_data=callback_data)

    if leader:
        builder.button(text="Выгнать", callback_data=f"kick_{id}",
                style = "danger")
        builder.adjust(len(buttons),1)

    return builder.as_markup()