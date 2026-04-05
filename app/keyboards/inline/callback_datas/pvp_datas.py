from aiogram.filters.callback_data import CallbackData

class PvPPagination(CallbackData, prefix="pp"):
    """Данные обратного вызова для кнопок пагинации."""
    p: int

class PvPVerseFilterPagination(CallbackData, prefix="pvfpg"):
    """Данные обратного вызова для кнопок пагинации фильтра по вселенной PvP."""
    p: int

class PvPVerseFilter(CallbackData, prefix="pvf"):
    """Данные обратного вызова для кнопок фильтра по вселенной PvP."""
    verse_id: int

class PvPRarityFilterPagination(CallbackData, prefix="prfpg"):
    """Данные обратного вызова для кнопок пагинации фильтра по редкости PvP."""
    p: int

class PvPRarityFilter(CallbackData, prefix="prf"):
    """Данные обратного вызова для кнопок фильтра по редкости PvP."""
    rarity_name: str

class SelectedCardPvP(CallbackData, prefix="scp"):
    c: int
    t: int