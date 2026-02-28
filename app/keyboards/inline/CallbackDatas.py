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

class TradePagination(CallbackData, prefix="tp"):
    """Данные обратного вызова для кнопок пагинации."""
    p: int

class TradeVerseFilterPagination(CallbackData, prefix="tvfpg"):
    """Данные обратного вызова для кнопок пагинации фильтра по вселенной."""
    p: int

class TradeVerseFilter(CallbackData, prefix="tvf"):
    """Данные обратного вызова для кнопок фильтра по вселенной."""
    verse_name: str

class TradeRarityFilterPagination(CallbackData, prefix="trfpg"):
    """Данные обратного вызова для кнопок пагинации фильтра по редкости."""
    p: int

class TradeRarityFilter(CallbackData, prefix="trf"):
    """Данные обратного вызова для кнопок фильтра по редкости."""
    rarity_name: str

class SelectedCard(CallbackData, prefix="ts"):
    card_id: int
