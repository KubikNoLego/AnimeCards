from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from random import randint

class Pagination(CallbackData, prefix="p"):
    """Данные обратного вызова для кнопок пагинации."""
    p: int
    m: int

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

async def main_kb():
    """Создать главную клавиатуру ответов.

    Returns:
        ReplyKeyboardMarkup с основными кнопками
    """
    buttons = ["🌐 Открыть карту", "👤 Профиль"]
    builder = ReplyKeyboardBuilder()
    [builder.button(text=item) for item in buttons]
    builder.adjust(2)

    return builder.as_markup(resize_keyboard=True, input_field="Привет!" if randint(1, 1000) == 777 else "...")

async def sort_inventory_kb(selected_rarity_name, selected_verse_name, mode: int = 0):

    builder = InlineKeyboardBuilder()

    if selected_rarity_name:
        builder.button(text=f"📊 По редкости ({selected_rarity_name})", callback_data="sort_by_rarity", style = "success")
    else:
        builder.button(text="📊 По редкости", callback_data="sort_by_rarity")

    if selected_verse_name:
        builder.button(text=f"🌌 По вселенной ({selected_verse_name})", callback_data=VerseFilterPagination(p=1).pack(), style = "success")
    else:
        builder.button(text="🌌 По вселенной", callback_data=VerseFilterPagination(p=1).pack())

    builder.button(text="🔄 Сбросить фильтры", callback_data="reset_sort_filters" + ("_0" if mode == 0 else "_1" if mode == 1 else "_2"), style = "danger")
    builder.button(text="✅ Применить фильтры", callback_data=Pagination(p=1, m=mode).pack(), style = "success")
    builder.adjust(2, 1, 1)

    return builder.as_markup()

async def trade_start():
    builder = InlineKeyboardBuilder()
    builder.button(text="👉 Выбрать карту", callback_data=Pagination(p=1, m=1).pack())
    return builder.as_markup()

async def upgrade_start():
    builder = InlineKeyboardBuilder()
    builder.button(text="⏫ Выбрать карту", callback_data=Pagination(p=1, m=2).pack())
    return builder.as_markup()

async def pagination_keyboard(current_page: int, total_pages: int, mode: int = 0):
    #mode 0 - простая пагинация
    #mode 1 - пагинация для трейда
    #mode 2 - пагинация для улучшения карт
    """Создать инлайн-клавиатуру пагинации.

    Args:
        current_page: Текущий номер страницы
        total_pages: Общее количество страниц
        mode: Режим пагинации (0 - инвентарь, 1 - трейд, 2 - улучшение)

    Returns:
        InlineKeyboardMarkup с кнопками пагинации
    """
    builder = InlineKeyboardBuilder()

    prev_100_active = current_page > 100
    prev_10_active = current_page > 10
    prev_1_active = current_page > 1
    next_1_active = current_page < total_pages
    next_10_active = current_page <= total_pages - 10
    next_100_active = current_page <= total_pages - 100

    buttons = []

    if prev_100_active:
        buttons.append(("««", Pagination(p=current_page-100, m=mode).pack()))

    if prev_10_active:
        buttons.append(("‹", Pagination(p=current_page-10, m=mode).pack()))

    if prev_1_active:
        buttons.append(("←", Pagination(p=current_page-1, m=mode).pack()))

    buttons.append((f"{current_page}/{total_pages}", "pass"))

    if next_1_active:
        buttons.append(("→", Pagination(p=current_page+1, m=mode).pack()))

    if next_10_active:
        buttons.append(("›", Pagination(p=current_page+10, m=mode).pack()))

    if next_100_active:
        buttons.append(("»»", Pagination(p=current_page+100, m=mode).pack()))

    for text, callback_data in buttons:
        builder.button(text=text, callback_data=callback_data)

    builder.button(text="✂️ Сортировка", callback_data="sort_inventory" + ("_0" if mode == 0 else "_1" if mode == 1 else "_2"), style = "success")
    if mode == 1: builder.button(text="✅ Выбрать", callback_data=f"tr:{current_page}")
    if mode == 2: builder.button(text="⏫ Улучшить", callback_data=f"up:{current_page}")
    builder.adjust(len(buttons), 1)

    return builder.as_markup()

async def rarity_filter_pagination_keyboard(current_page: int, rarities: list):
    """Создать инлайн-клавиатуру пагинации для фильтра по редкости.

    Args:
        current_page: Текущий номер страницы
        rarities: Список редкостей
    Returns:
        InlineKeyboardMarkup с кнопками пагинации
    """
    builder = InlineKeyboardBuilder()

    rarities_names: list
    pages = (len(rarities) + 5) // 6
    start_index = (current_page - 1) * 6
    end_index = start_index + 6
    rarities_names = [rarity.name for rarity in rarities[start_index:end_index]]

    for rarity_name in rarities_names:
        builder.button(text=rarity_name, callback_data=RarityFilter(rarity_name=rarity_name).pack())

    empty_buttons_needed = 6 - len(rarities_names)
    for _ in range(empty_buttons_needed):
        builder.button(text=" ", callback_data="pass")

    prev_1_active = current_page > 1
    next_1_active = current_page < len(rarities)

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


async def profile_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Инвентарь", callback_data=Pagination(p=1).pack())

    return builder.as_markup()

async def verse_filter_pagination_keyboard(current_page: int, verses: list):
    """Создать инлайн-клавиатуру пагинации для фильтра по вселенной.

    Args:
        current_page: Текущий номер страницы
        verses: Список вселенных
    Returns:
        InlineKeyboardMarkup с кнопками пагинации
    """
    builder = InlineKeyboardBuilder()

    verses_names: list
    pages = (len(verses) + 3) // 4
    start_index = (current_page - 1) * 4
    end_index = start_index + 4
    verses_names = [verse.name for verse in verses[start_index:end_index]]

    for verse_name in verses_names:
        builder.button(text=verse_name, callback_data=VerseFilter(verse_name=verse_name).pack())

    empty_buttons_needed = 4 - len(verses_names)
    for _ in range(empty_buttons_needed):
        builder.button(text=" ", callback_data="pass")


    prev_1_active = current_page > 1
    next_1_active = current_page < len(verses)

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
