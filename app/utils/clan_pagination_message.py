from aiogram.types import InputMediaPhoto, Message


async def edit_message(message: Message, text:str, reply_markup=None,
                                                    photo: str | None = None):
    if photo:
        media = InputMediaPhoto(
            media=photo,
            caption=text
        )

        if message.photo:
            await message.edit_media(
                media=media,
                reply_markup=reply_markup
            )
        else:
            await message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=reply_markup
            )
            await message.delete()

    else:
        if message.photo:
            await message.answer(
                text=text,
                reply_markup=reply_markup
            )
            await message.delete()

        else:
            await message.edit_text(
                text=text,
                reply_markup=reply_markup
            )