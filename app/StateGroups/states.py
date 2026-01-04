from aiogram.fsm.state import State, StatesGroup

class CardViewStates(StatesGroup):
    verse_id: int = State()
    rarity_id: int = State()

    curent_page: int = State()