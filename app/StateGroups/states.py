# Стандартные библиотеки

# Сторонние библиотеки
from aiogram.fsm.state import State, StatesGroup

class ChangeDescribe(StatesGroup):
    text = State()

class CreateClan(StatesGroup):
    name = State()
    tag = State()
    description = State()
    accept = State()

class ClanLeader(StatesGroup):
    desc = State()