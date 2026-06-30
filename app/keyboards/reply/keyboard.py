from random import randint

from aiogram.utils.keyboard import ReplyKeyboardBuilder

async def main_kb():
    """Создать главную клавиатуру ответов.

    Returns:
        ReplyKeyboardMarkup с основными кнопками
    """
    buttons = ["🎴 Баннеры", "🛒 Магазин", "👤 Профиль",
            "🏆 Топ игроков","🛡️ Клан", "🔁 Трейды"]
    builder = ReplyKeyboardBuilder()
    [builder.button(text=item) for item in buttons]
    builder.adjust(3, 3 )

    return builder.as_markup(resize_keyboard=True, input_field_placeholder=("🌟 <- это ты" if randint(1, 1000) == 777 else "Меню 🌟"))

async def admin_kb():
    """Клавиатура админ-панели"""

    builder = ReplyKeyboardBuilder()
    builder.button(text="📊 Статистика")
    builder.button(text="👤 Поиск пользователя")
    builder.button(text="💰 Изменить баланс")
    builder.button(text="⭐ VIP управление")
    builder.button(text="🎁 Создать промокод")
    builder.button(text="📋 Список пользователей")
    builder.button(text="📢 Рассылка")
    builder.adjust(2, 2, 2, 1)

    return builder.as_markup(resize_keyboard=True)
