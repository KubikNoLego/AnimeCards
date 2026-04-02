import os
import tempfile

import qrcode
from aiogram.types import FSInputFile, Message
from loguru import logger

async def create_qr(link:str) -> FSInputFile:
    """Создаёт QR для реферальной ссылки"""
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )
    qr.add_data(link)

    # Создаем временный файл
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    try:
        # Генерируем изображение и сохраняем во временный файл
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(temp_file.name)
        return FSInputFile(temp_file.name)
    except Exception as e:
        # Удаляем временный файл в случае ошибки
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        logger.exception("Ошибкв при создании QR")
        return

async def user_photo_link(message: Message) -> str | None:
    """Получить file_id фото профиля пользователя"""
    try:
        target_id = (message.reply_to_message.from_user.id 
            if message.reply_to_message and message.reply_to_message.from_user
            else message.from_user.id)

        profile_photos = await message.bot.get_user_profile_photos(
                                                                target_id,
                                                                limit=1
                                                                )

        # Проверяем, есть ли хоть одна фотография
        if profile_photos and len(profile_photos.photos) > 0:
            photo = profile_photos.photos[0][-1]
            file_id = photo.file_id
            return file_id
    except Exception as exc:
        logger.exception(f"Ошибка при получении фото пользователя: {exc}")

        return None