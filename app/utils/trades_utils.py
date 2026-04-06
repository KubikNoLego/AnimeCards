from aiogram.types import FSInputFile, Message

from app.database.models import Card
from app.keyboards.inline.trade_kbs import trade_kb_pagination
from app.utils.card_formater import format_card


async def send_trade_card(message: Message, card: Card) -> None:
    card_info = await format_card(card)

    # Отправляем карту с учетом типа файла
    file_path = f"app/assets/cards/{card.verse.name}/{card.icon}"
    if card.icon.endswith('.mp4'):
        await message.answer_video(
            FSInputFile(path=file_path),
            caption=card_info,
            reply_markup=await trade_kb_pagination()
        )
    else:
        await message.answer_photo(
            FSInputFile(path=file_path),
            caption=card_info,
            reply_markup=await trade_kb_pagination()
        )