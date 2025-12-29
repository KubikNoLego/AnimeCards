from aiogram.types import Message
from loguru import logger

async def user_photo_link(message:Message):
    try:
        profile_photos = await message.bot.get_user_profile_photos(
            message.from_user.id if not message.reply_to_message 
            else message.reply_to_message.from_user.id,limit=1)

        if len(profile_photos.photos) > 0:
            photo = profile_photos.photos[0][-1]
            file_id = photo.file_id

            return file_id
    except Exception as _ex:
        logger.error(_ex)
    return None