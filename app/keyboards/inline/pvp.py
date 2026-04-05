from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .callback_datas.pvp_datas import (
    PvPPagination, PvPVerseFilter, PvPVerseFilterPagination,
    SelectedCardPvP, PvPRarityFilter, PvPRarityFilterPagination
)

async def back_to_sort() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад к сортировке", callback_data=
                "sort_inventory_pvp")
    builder.adjust(1)

    return builder.as_markup()

async def selects_card_pvp(in_queue: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    if not in_queue:
        kb.button(text="Выбрать карту", callback_data=PvPPagination(p=1).pack())
        kb.button(text="⚔️ Искать противника", callback_data="search_opponent")
    else:
        kb.button(text="❌ Выйти из очереди", callback_data="cancel_search")
        kb.button(text="⚠️ Изменение колоды заблокировано", callback_data="disabled", style="danger")

    kb.adjust(1)

    return kb.as_markup()

async def pvppagination(current_page: int, 
                    total_pages: int) -> InlineKeyboardMarkup:
    """Инлайн-клавиатура пагинации."""
    builder = InlineKeyboardBuilder()

    prev_100_active = current_page > 100
    prev_10_active = current_page > 10
    prev_1_active = current_page > 1
    next_1_active = current_page < total_pages
    next_10_active = current_page <= total_pages - 10
    next_100_active = current_page <= total_pages - 100

    buttons = []

    callback = PvPPagination

    if prev_100_active:
        buttons.append(("««", callback(p=current_page-100).pack(), 
                        "primary"))

    if prev_10_active:
        buttons.append(("‹", callback(p=current_page-10).pack(), 
                        "primary"))

    if prev_1_active:
        buttons.append(("←", callback(p=current_page-1).pack(), 
                        "primary"))

    buttons.append((f"{current_page}/{total_pages}", "pass"))

    if next_1_active:
        buttons.append(("→", callback(p=current_page+1).pack(), 
                        "primary"))

    if next_10_active:
        buttons.append(("›", callback(p=current_page+10).pack(), 
                        "primary"))

    if next_100_active:
        buttons.append(("»»", callback(p=current_page+100).pack(), 
                        "primary"))

    for item in buttons:
        if len(item) == 3:
            text, callback_data, style = item
            builder.button(text=text, callback_data=callback_data, style=style)
        else:
            text, callback_data = item
            builder.button(text=text, callback_data=callback_data)

    builder.button(text="✂️ Сортировка", callback_data=("sort_inventory_pvp"),
                style = "success")
    
    builder.button(text="👉 Выбрать карту",
                    callback_data=SelectedCardPvP(c = current_page,
                                                t = total_pages).pack())

    builder.adjust(len(buttons),1)

    return builder.as_markup()

async def sort_inventory_kb(selected_rarity_name,selected_verse_name):

    builder = InlineKeyboardBuilder()

    if selected_rarity_name:
        builder.button(text=f"📊 По редкости ({selected_rarity_name})",
                    callback_data="sort_by_rarity_pvp",style = "success")
    else:
        builder.button(text="📊 По редкости", callback_data="sort_by_rarity_pvp")

    if selected_verse_name:
        builder.button(text=f"🌌 По вселенной ({selected_verse_name})",
            callback_data=PvPVerseFilterPagination(p=1), style = "success")
    else:
        builder.button(text="🌌 По вселенной",
                    callback_data=PvPVerseFilterPagination(p=1).pack())

    builder.button(text="🔄 Сбросить фильтры",
                callback_data="reset_sort_filters_pvp", style = "danger")
    builder.button(text="✅ Применить фильтры",
                callback_data=PvPPagination(p=1).pack(), style = "success")
    builder.adjust(2, 1, 1)

    return builder.as_markup()

async def verse_filter_pagination_keyboard(current_page: int, verses: list):
    """Создать инлайн-клавиатуру пагинации для фильтра по вселенной"""
    builder = InlineKeyboardBuilder()

    verses_data: list
    pages = (len(verses) + 3) // 4
    start_index = (current_page - 1) * 4
    end_index = start_index + 4
    verses_data = verses[start_index:end_index]

    for verse in verses_data:
        builder.button(text=verse.name,
                callback_data=PvPVerseFilter(verse_id=verse.id),
                style = "primary")

    empty_buttons_needed = 4 - len(verses_data)
    for _ in range(empty_buttons_needed):
        builder.button(text=" ", callback_data="pass")


    prev_1_active = current_page > 1
    next_1_active = current_page < pages

    if prev_1_active:
        builder.button(text="←",
                callback_data=PvPVerseFilterPagination(p=current_page-1))
    builder.button(text=f"{current_page}/{pages}", callback_data="pass")
    if next_1_active:
        builder.button(text="→", 
                callback_data=PvPVerseFilterPagination(p=current_page+1))
    builder.button(text="◀️ Назад",callback_data="sort_inventory_pvp")

    if prev_1_active and next_1_active:
        builder.adjust(2, 2, 3, 1)
    elif prev_1_active or next_1_active:
        builder.adjust(2, 2, 2, 1)
    else:
        builder.adjust(2, 2, 1, 1)

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
        builder.button(text=rarity_name,
            callback_data=PvPRarityFilter(rarity_name=rarity_name).pack(),
            style="primary")

    empty_buttons_needed = 6 - len(rarities_names)
    for _ in range(empty_buttons_needed):
        builder.button(text=" ", callback_data="pass")

    prev_1_active = current_page > 1
    next_1_active = current_page < pages

    if prev_1_active:
        builder.button(text="←",
                callback_data=PvPRarityFilterPagination(p=current_page-1).pack())
    builder.button(text=f"{current_page}/{pages}", callback_data="pass")
    if next_1_active:
        builder.button(text="→",
                callback_data=PvPRarityFilterPagination(p=current_page+1).pack())
    builder.button(text="◀️ Назад", callback_data="sort_inventory_pvp")

    if prev_1_active and next_1_active:
        builder.adjust(3, 3, 3, 1)
    elif prev_1_active or next_1_active:
        builder.adjust(3, 3, 2, 1)
    else:
        builder.adjust(3, 3, 1, 1)

    return builder.as_markup()


async def select_slot_keyboard(card_rarity: str, is_limited: bool = False, 
                                is_in_slot: bool = False, current_slot: str = None) -> InlineKeyboardMarkup:
    """Клавиатура для выбора слота для карты.
    
    Args:
        card_rarity: Название редкости карты
        is_limited: Является ли карта лимитированной
        is_in_slot: Установлена ли карта уже в какой-либо слот
        current_slot: Текущий слот карты (если is_in_slot=True)
    """
    builder = InlineKeyboardBuilder()
    
    # Словарь для сопоставления редкости и слота
    rarity_to_slot = {
        "Обычный": "common",
        "Редкий": "uncommon",
        "Мифический": "mythic",
        "Легендарный": "legend",
        "Хроно": "hrono"
    }
    
    # Если карта уже установлена в слоте, показываем кнопку "Убрать"
    if is_in_slot and current_slot:
        slot_names = {
            "common": "Обычный",
            "uncommon": "Редкий",
            "mythic": "Мифический",
            "legend": "Легендарный",
            "hrono": "Хроно"
        }
        builder.button(
            text=f"❌ Убрать из слота {slot_names[current_slot]}",
            callback_data=f"remove_from_slot_{current_slot}"
        )
        builder.adjust(1)
    elif is_limited:
        # Для лимитированной карты показываем все слоты
        for rarity, slot in rarity_to_slot.items():
            builder.button(
                text=f"{rarity}",
                callback_data=f"select_slot_{slot}"
            )
        builder.adjust(1)
    else:
        # Для обычной карты показываем только соответствующий слот
        slot = rarity_to_slot.get(card_rarity)
        if slot:
            builder.button(
                text=f"Поставить",
                callback_data=f"select_slot_{slot}"
            )
            builder.adjust(1)
    
    builder.button(text="❌ Отмена", callback_data="cancel_slot_selection")
    builder.adjust(1)
    
    return builder.as_markup()
