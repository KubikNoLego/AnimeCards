# Стандартные библиотеки

# Сторонние библиотеки
from aiogram.fsm.state import State, StatesGroup

class CardViewStates(StatesGroup):
    selected_verse_name: str = State()
    selected_rarity_name:str = State()

class ChangeDescribe(StatesGroup):
    text = State()