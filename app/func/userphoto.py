from typing import Optional
from aiogram.types import Message
from loguru import logger


async def user_photo_link(message: Message) -> Optional[str]:
    """Возвращает file_id аватарки пользователя (reply target или отправитель). Если фото нет — возвращает None.
    """
    try:
        # Определяем чей профиль запрашивать: reply target имеет приоритет
        target_id = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id

        profile_photos = await message.bot.get_user_profile_photos(target_id, limit=1)

        # Проверяем, есть ли хоть одна фотография
        if profile_photos and len(profile_photos.photos) > 0:
            # Берём последний элемент в первом варианте (обычно наибольший размер)
            photo = profile_photos.photos[0][-1]
            file_id = photo.file_id
            logger.info(f"Найдено фото для пользователя id={target_id}: file_id={file_id}")
            return file_id
        else:
            logger.info(f"У пользователя id={target_id} нет фото профиля")
    except Exception as exc:
        # Логируем исключение с трассировкой для удобства отладки
        logger.exception(f"Ошибка при получении фото пользователя: {exc}")

    return None