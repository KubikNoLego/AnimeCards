from enum import Enum

class TitleOpen(Enum):
    """Результаты открытия титулов"""
    NOT_REGISTERED = 0
    NOT_ENOUGH_YENS = 1
    ERROR = 2
    SUCCESS = 3