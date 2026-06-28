from abc import abstractmethod
from math import ceil

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.models import Title
from app.keyboards.inline.datas import TitlePagination as TP

class BasePagination:
    PAGE_SIZE = 6

    def __init__(self, page: int = 0):
        self.page = max(page,0)

    @property
    @abstractmethod
    def total_items(self) -> int:
        """Возвращает общее количество элементов"""
        ...
    
    @property
    def total_pages(self) -> int:
        return max(1, ceil(self.total_items / self.PAGE_SIZE))
    
    @property
    def offset(self) -> int:
        return self.page * self.PAGE_SIZE
    
    @property
    def has_next(self) -> bool:
        return self.page + 1 < self.total_pages
    
    @property
    def has_previuos(self) -> bool:
        return self.page > 0

    @abstractmethod
    def callback(self, page: int) -> str:
        """Возвращает callback_data для указанной страницы."""
        ...
    
    @abstractmethod
    async def build_items(self, builder: InlineKeyboardBuilder):
        ...

    @abstractmethod
    def build_extra_buttons(self, builder: InlineKeyboardBuilder):
        ...

    def build_navigation(self, builder: InlineKeyboardBuilder):

        buttons = []

        for step, text in (
            (-100, "««"), (-10, "‹"), (-1, "←"),
            (1, "→"), (10, "›"), (100, "»»")):
            
            page = self.page + step

            if 1 <= page <= self.total_pages:
                buttons.append(
                    InlineKeyboardButton(
                        text=text,
                        callback_data=self.callback(page)
                    )
                )

        left_buttons = sum(
            1
            for step in (-100, -10, -1)
            if 1 <= self.page + step <= self.total_pages)

        buttons.insert(
            left_buttons,
            InlineKeyboardButton(
                text=f"{self.page}/{self.total_pages}",
                callback_data="pass"
            ))
        
        builder.row(*buttons)

    async def keyboard(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        await self.build_items(builder)
        self.build_navigation(builder)
        self.build_extra_buttons(builder)

        return builder.as_markup()
    
class TitlePagination(BasePagination):

    PAGE_SIZE = 1
    
    def __init__(self, page = 0, titles: list[Title] = []):
        super().__init__(page)

        self.titles = titles

    @property
    def total_items(self):
        return len(self.titles)
    
    async def build_items(self, builder):
        pass

    def build_extra_buttons(self, builder):
        title_id = self.titles[self.page-1].id
        builder.row(
            InlineKeyboardButton(
                text="👉 Выбрать",
                callback_data=f"select_title:{title_id}"))

    def callback(self, page: int):
        return TP(p=page).pack()
    
