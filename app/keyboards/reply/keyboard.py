from random import randint

from aiogram.utils.keyboard import ReplyKeyboardBuilder

async def main_kb():
    """Создать главную клавиатуру ответов.

    Returns:
        ReplyKeyboardMarkup с основными кнопками
    """
    buttons = ["🌐 Открыть карту", "👤 Профиль", "🏆 Топ игроков", "🔗 Реферальная ссылка","🛒 Магазин", "💎 Купить VIP"]
    builder = ReplyKeyboardBuilder()
    [builder.button(text=item) for item in buttons]
    builder.adjust(2, 2, 1)

    return builder.as_markup(resize_keyboard=True, input_field_placeholder=("💫" if randint(1, 1000) == 777 else "Меню 🌟"))

async def admin_kb():
    """Клавиатура админ-панели"""
    
    builder = ReplyKeyboardBuilder()
    builder.button(text="📊 Статистика")
    builder.button(text="👤 Поиск пользователя")
    builder.button(text="💰 Изменить баланс")
    builder.button(text="⭐ VIP управление")
    builder.button(text="📋 Список пользователей")
    builder.button(text="📢 Рассылка")
    builder.adjust(2, 2, 1, 1)

    return builder.as_markup(resize_keyboard=True)
