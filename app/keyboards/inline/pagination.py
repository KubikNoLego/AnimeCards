from aiogram.utils.keyboard import InlineKeyboardBuilder

from .CallbackDatas import (
                            Pagination,VerseFilter,VerseFilterPagination,
                            RarityFilter,RarityFilterPagination,
                            TradeVerseFilterPagination, TradePagination,
                            TradeRarityFilter, TradeRarityFilterPagination,
                            TradeVerseFilter,SelectedCard
                            )


async def back_to_sort(trade: bool = False):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад к сортировке", callback_data=(
        "sort_inventory" if not trade else "sort_inventory_trade")
        )
    builder.adjust(1)

    return builder.as_markup()

async def sort_inventory_kb(selected_rarity_name,selected_verse_name,
                            trade: bool = False):

    builder = InlineKeyboardBuilder()

    if selected_rarity_name:
        builder.button(text=f"📊 По редкости ({selected_rarity_name})",
                    callback_data=("sort_by_rarity"
                                if not trade
                                else "sort_by_rarity_trade"),style = "success")
    else:
        builder.button(text="📊 По редкости", callback_data=("sort_by_rarity"
                                if not trade
                                else "sort_by_rarity_trade"))

    if selected_verse_name:
        builder.button(text=f"🌌 По вселенной ({selected_verse_name})",
            callback_data=(VerseFilterPagination(p=1)
                        if not trade
                        else TradeVerseFilterPagination(p=1)).pack(), style = "success")
    else:
        builder.button(text="🌌 По вселенной",
                    callback_data=(VerseFilterPagination(p=1)
                        if not trade
                        else TradeVerseFilterPagination(p=1)).pack())

    builder.button(text="🔄 Сбросить фильтры",
                callback_data=("reset_sort_filters"
                            if not trade
                            else "reset_sort_filters_trade"), style = "danger")
    builder.button(text="✅ Применить фильтры",
                callback_data=(Pagination(p=1)
                            if not trade
                            else TradePagination(p=1)).pack(), style = "success")
    builder.adjust(2, 1, 1)

    return builder.as_markup()

async def pagination_keyboard(current_page: int, total_pages: int,
                            trade: bool = False, card_id: int | None = None):
    """Инлайн-клавиатура пагинации."""
    builder = InlineKeyboardBuilder()

    prev_100_active = current_page > 100
    prev_10_active = current_page > 10
    prev_1_active = current_page > 1
    next_1_active = current_page < total_pages
    next_10_active = current_page <= total_pages - 10
    next_100_active = current_page <= total_pages - 100

    buttons = []

    callback = Pagination if not trade else TradePagination

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

    builder.button(text="✂️ Сортировка", callback_data=("sort_inventory" if not
                        trade else "sort_inventory_trade"),
                style = "success")
    
    if trade:
        builder.button(text="👉 Выбрать карту",
                    callback_data=SelectedCard(card_id=card_id).pack())

    builder.adjust(len(buttons),1)

    return builder.as_markup()

async def rarity_filter_pagination_keyboard(current_page: int, rarities: list,
                                            trade:bool = False):
    """Создать инлайн-клавиатуру пагинации для фильтра по редкости"""
    builder = InlineKeyboardBuilder()

    rarities_names: list
    pages = (len(rarities) + 5) // 6
    start_index = (current_page - 1) * 6
    end_index = start_index + 6
    rarities_names = [rarity.name for rarity in rarities[start_index:end_index]]

    for rarity_name in rarities_names:
        builder.button(text=rarity_name,
            callback_data=(RarityFilter(rarity_name=rarity_name)
                        if not trade
                        else TradeRarityFilter(rarity_name=rarity_name)
                        ).pack(),
            style="primary")

    empty_buttons_needed = 6 - len(rarities_names)
    for _ in range(empty_buttons_needed):
        builder.button(text=" ", callback_data="pass")

    prev_1_active = current_page > 1
    next_1_active = current_page < pages

    if prev_1_active:
        builder.button(text="←",
                callback_data=(RarityFilterPagination(p=current_page-1)
                            if not trade
                            else TradeRarityFilterPagination(p=current_page-1)
                            ).pack())
    builder.button(text=f"{current_page}/{pages}", callback_data="pass")
    if next_1_active:
        builder.button(text="→",
                callback_data=(RarityFilterPagination(p=current_page+1)
                            if not trade
                            else TradeRarityFilterPagination(p=current_page+1)
                            ).pack())
    builder.button(text="◀️ Назад", callback_data=("sort_inventory" if not
                        trade else "sort_inventory_trade"))

    if prev_1_active and next_1_active:
        builder.adjust(3, 3, 3, 1)
    elif prev_1_active or next_1_active:
        builder.adjust(3, 3, 2, 1)
    else:
        builder.adjust(3, 3, 1, 1)

    return builder.as_markup()

async def verse_filter_pagination_keyboard(current_page: int, verses: list,
                                        trade:bool = False):
    """Создать инлайн-клавиатуру пагинации для фильтра по вселенной"""
    builder = InlineKeyboardBuilder()

    verses_data: list
    pages = (len(verses) + 3) // 4
    start_index = (current_page - 1) * 4
    end_index = start_index + 4
    verses_data = verses[start_index:end_index]

    for verse in verses_data:
        builder.button(text=verse.name,
                callback_data=(VerseFilter(verse_id=verse.id)
                            if not trade
                            else TradeVerseFilter(verse_id=verse.id)
                            ).pack(),
                style = "primary")

    empty_buttons_needed = 4 - len(verses_data)
    for _ in range(empty_buttons_needed):
        builder.button(text=" ", callback_data="pass")


    prev_1_active = current_page > 1
    next_1_active = current_page < pages

    if prev_1_active:
        builder.button(text="←",
                callback_data=(VerseFilterPagination(p=current_page-1)
                            if not trade else TradeVerseFilterPagination(
                                p=current_page-1
                            )).pack())
    builder.button(text=f"{current_page}/{pages}", callback_data="pass")
    if next_1_active:
        builder.button(text="→", 
                callback_data=(VerseFilterPagination(p=current_page+1)
                            if not trade else TradeVerseFilterPagination(
                                p=current_page+1
                            )).pack())
    builder.button(text="◀️ Назад",callback_data=("sort_inventory" 
                        if not trade else "sort_inventory_trade"))

    if prev_1_active and next_1_active:
        builder.adjust(2, 2, 3, 1)
    elif prev_1_active or next_1_active:
        builder.adjust(2, 2, 2, 1)
    else:
        builder.adjust(2, 2, 1, 1)

    return builder.as_markup()