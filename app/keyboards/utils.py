# Стандартные библиотеки
from random import randint

# Сторонние библиотеки
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

class ClanInvite(CallbackData,prefix = "clan"):
    clan_id: int
    act: int

class ShopItemCallback(CallbackData, prefix="shop"):
    """Данные обратного вызова для кнопок товаров магазина."""
    item_id: int

class MemberPagination(CallbackData, prefix="pc"):
    """Данные обратного вызова для кнопок пагинации."""
    p: int

class Pagination(CallbackData, prefix="p"):
    """Данные обратного вызова для кнопок пагинации."""
    p: int

class VerseFilterPagination(CallbackData, prefix="vfpg"):
    """Данные обратного вызова для кнопок пагинации фильтра по вселенной."""
    p: int

class VerseFilter(CallbackData, prefix="vf"):
    """Данные обратного вызова для кнопок фильтра по вселенной."""
    verse_name: str

class RarityFilterPagination(CallbackData, prefix="rfpg"):
    """Данные обратного вызова для кнопок пагинации фильтра по редкости."""
    p: int

class RarityFilter(CallbackData, prefix="rf"):
    """Данные обратного вызова для кнопок фильтра по редкости."""
    rarity_name: str

class TradePagination(CallbackData,prefix="tp"):
    p: int

async def main_kb():
    """Создать главную клавиатуру ответов.

    Returns:
        ReplyKeyboardMarkup с основными кнопками
    """
    buttons = ["🌐 Открыть карту", "👤 Профиль", "🏆 Топ игроков", "🔗 Реферальная ссылка","🛒 Магазин", "💎 Купить VIP","🔁 Трейды","🛡️ Клан"]
    builder = ReplyKeyboardBuilder()
    [builder.button(text=item) for item in buttons]
    builder.adjust(2, 3, 2, 1)

    return builder.as_markup(resize_keyboard=True, input_field_placeholder=("💫" if randint(1, 1000) == 777 else "Меню 🌟"))

async def sort_inventory_kb(selected_rarity_name,selected_verse_name,mode = "standart"):

    builder = InlineKeyboardBuilder()

    callback = Pagination if mode == "standart" else TradePagination

    if selected_rarity_name:
        builder.button(text=f"📊 По редкости ({selected_rarity_name})", callback_data="sort_by_rarity", style = "success")
    else:
        builder.button(text="📊 По редкости", callback_data="sort_by_rarity")

    if selected_verse_name:
        builder.button(text=f"🌌 По вселенной ({selected_verse_name})", callback_data=VerseFilterPagination(p=1).pack(), style = "success")
    else:
        builder.button(text="🌌 По вселенной", callback_data=VerseFilterPagination(p=1).pack())

    builder.button(text="🔄 Сбросить фильтры", callback_data="reset_sort_filters" + ("_s" if mode == "standart" else "_t"), style = "danger")
    builder.button(text="✅ Применить фильтры", callback_data=callback(p=1).pack(), style = "success")
    builder.adjust(2, 1, 1)


    return builder.as_markup()

async def clan_invite_kb(clan_id: int):
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Принять", callback_data= ClanInvite(clan_id=clan_id, act=1).pack(),style = "success")
    builder.button(text="❎ Отклонить", callback_data= ClanInvite(clan_id=clan_id, act=0).pack(),style = "danger")

    return builder.as_markup()

async def trade_start():
    builder = InlineKeyboardBuilder()
    builder.button(text="👉 Выбрать карту", callback_data=TradePagination(p=1).pack())
    return builder.as_markup()

async def pagination_keyboard(current_page: int, total_pages: int, mode: str = "standart"):
    """Инлайн-клавиатура пагинации."""
    builder = InlineKeyboardBuilder()

    callback = Pagination if mode == "standart" else TradePagination

    prev_100_active = current_page > 100
    prev_10_active = current_page > 10
    prev_1_active = current_page > 1
    next_1_active = current_page < total_pages
    next_10_active = current_page <= total_pages - 10
    next_100_active = current_page <= total_pages - 100

    buttons = []

    if prev_100_active:
        buttons.append(("««", callback(p=current_page-100).pack(), "primary"))

    if prev_10_active:
        buttons.append(("‹", callback(p=current_page-10).pack(), "primary"))

    if prev_1_active:
        buttons.append(("←", callback(p=current_page-1).pack(), "primary"))

    buttons.append((f"{current_page}/{total_pages}", "pass"))

    if next_1_active:
        buttons.append(("→", callback(p=current_page+1).pack(), "primary"))

    if next_10_active:
        buttons.append(("›", callback(p=current_page+10).pack(), "primary"))

    if next_100_active:
        buttons.append(("»»", callback(p=current_page+100).pack(), "primary"))

    for item in buttons:
        if len(item) == 3:
            text, callback_data, style = item
            builder.button(text=text, callback_data=callback_data, style=style)
        else:
            text, callback_data = item
            builder.button(text=text, callback_data=callback_data)

    builder.button(text="✂️ Сортировка", callback_data="sort_inventory" + ("_s" if mode == "standart" else "_t"), style = "success")
    builder.adjust(len(buttons), 1)

    return builder.as_markup()

async def rarity_filter_pagination_keyboard(current_page: int, rarities: list):
    """Создать инлайн-клавиатуру пагинации для фильтра по редкости"""
    builder = InlineKeyboardBuilder()

    rarities_names: list
    pages = (len(rarities) + 5) // 6
    start_index = (current_page - 1) * 6
    end_index = start_index + 6
    rarities_names = [rarity.name for rarity in rarities[start_index:end_index]]

    for rarity_name in rarities_names:
        builder.button(text=rarity_name, callback_data=RarityFilter(rarity_name=rarity_name).pack(),style="primary")

    empty_buttons_needed = 6 - len(rarities_names)
    for _ in range(empty_buttons_needed):
        builder.button(text=" ", callback_data="pass")

    prev_1_active = current_page > 1
    next_1_active = current_page < pages

    if prev_1_active:
        builder.button(text="←", callback_data=RarityFilterPagination(p=current_page-1).pack())
    builder.button(text=f"{current_page}/{pages}", callback_data="pass")
    if next_1_active:
        builder.button(text="→", callback_data=RarityFilterPagination(p=current_page+1).pack())
    builder.button(text="◀️ Назад", callback_data="sort_inventory")

    if prev_1_active and next_1_active:
        builder.adjust(3, 3, 3, 1)
    elif prev_1_active or next_1_active:
        builder.adjust(3, 3, 2, 1)
    else:
        builder.adjust(3, 3, 1, 1)

    return builder.as_markup()

async def profile_keyboard(has_describe: bool):
    builder = InlineKeyboardBuilder()

    builder.button(text="📦 Инвентарь", callback_data=Pagination(p=1).pack())
    builder.button(text="🖋️ Сменить подпись",callback_data="change_describe")
    if has_describe:
        builder.button(text="❌ Удалить подпись",callback_data="delete_describe",style = "danger")

    builder.adjust(1)

    return builder.as_markup()

async def verse_filter_pagination_keyboard(current_page: int, verses: list):
    """Создать инлайн-клавиатуру пагинации для фильтра по вселенной"""
    builder = InlineKeyboardBuilder()

    verses_names: list
    pages = (len(verses) + 3) // 4
    start_index = (current_page - 1) * 4
    end_index = start_index + 4
    verses_names = [verse.name for verse in verses[start_index:end_index]]

    for verse_name in verses_names:
        builder.button(text=verse_name, callback_data=VerseFilter(verse_name=verse_name).pack(),style = "primary")

    empty_buttons_needed = 4 - len(verses_names)
    for _ in range(empty_buttons_needed):
        builder.button(text=" ", callback_data="pass")


    prev_1_active = current_page > 1
    next_1_active = current_page < pages

    if prev_1_active:
        builder.button(text="←", callback_data=VerseFilterPagination(p=current_page-1).pack())
    builder.button(text=f"{current_page}/{pages}", callback_data="pass")
    if next_1_active:
        builder.button(text="→", callback_data=VerseFilterPagination(p=current_page+1).pack())
    builder.button(text="◀️ Назад",callback_data="sort_inventory")

    if prev_1_active and next_1_active:
        builder.adjust(2, 2, 3, 1)
    elif prev_1_active or next_1_active:
        builder.adjust(2, 2, 2, 1)
    else:
        builder.adjust(2, 2, 1, 1)

    return builder.as_markup()


async def shop_keyboard(cards: list):
    """Создать инлайн-клавиатуру для магазина"""
    builder = InlineKeyboardBuilder()

    for card in cards:
        builder.button(text=f"{card.name} ({int(card.value)} ¥)", callback_data=ShopItemCallback(item_id=card.id).pack(),style = "primary")

    builder.adjust(2)

    return builder.as_markup()

async def create_clan():
    builder = InlineKeyboardBuilder()
    

    builder.button(text="📝 Создать клан",callback_data="create_clan")

    return builder.as_markup()

async def clan_create():
    
    builder = InlineKeyboardBuilder()
    

    builder.button(text="✅ Создать клан",callback_data="accept_create_clan", style = "success")
    builder.button(text="🔄 Начать заново",callback_data="create_clan",style = "primary")
    builder.button(text="❌ Отмена",callback_data="cancel_create_clan",style = "danger")

    return builder.as_markup()

async def clan_create_exit():
    
    builder = InlineKeyboardBuilder()
    

    builder.button(text="❌ Отмена",callback_data="cancel_create_clan",style = "danger")

    return builder.as_markup()

async def clan_member():
    builder = InlineKeyboardBuilder()
    

    builder.button(text="👤 Участники",callback_data=MemberPagination(p=1).pack())
    builder.button(text="🚪 Покинуть",callback_data="leave_clan", style="danger")

    builder.adjust(1)

    return builder.as_markup()

async def clan_leader():
    builder = InlineKeyboardBuilder()
    

    builder.button(text="👤 Участники",callback_data=MemberPagination(p=1).pack())
    builder.button(text="🖋️ Сменить описание", callback_data="change_desc_clan")
    builder.button(text="🚪 Покинуть",callback_data="leave_clan",style="danger")
    builder.button(text="🗑️ Удалить клан",callback_data="delete_clan", style="danger")


    builder.adjust(1)

    return builder.as_markup()

async def member_pagination_keyboard(current_page: int, total_pages: int, id:int, leader = False):
    """Инлайн-клавиатура пагинации."""
    builder = InlineKeyboardBuilder()

    prev_10_active = current_page > 10
    prev_1_active = current_page > 1
    next_1_active = current_page < total_pages
    next_10_active = current_page <= total_pages - 10

    buttons = []

    if prev_10_active:
        buttons.append(("‹", MemberPagination(p=current_page-10).pack(), "primary"))

    if prev_1_active:
        buttons.append(("←", MemberPagination(p=current_page-1).pack(), "primary"))

    buttons.append((f"{current_page}/{total_pages}", "pass"))

    if next_1_active:
        buttons.append(("→", MemberPagination(p=current_page+1).pack(), "primary"))

    if next_10_active:
        buttons.append(("›", MemberPagination(p=current_page+10).pack(), "primary"))

    for item in buttons:
        if len(item) == 3:
            text, callback_data, style = item
            builder.button(text=text, callback_data=callback_data, style=style)
        else:
            text, callback_data = item
            builder.button(text=text, callback_data=callback_data)

    if leader:
        builder.button(text="Выгнать", callback_data=f"kick_{id}", style = "danger")
        builder.adjust(len(buttons),1)

    return builder.as_markup()
