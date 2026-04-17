import os
import tempfile

from aiogram import Bot
import qrcode
from aiogram.types import FSInputFile
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

async def user_photo_link(bot: Bot, user_id: int) -> str | None:
    """Получить file_id фото профиля пользователя"""
    try:

        profile_photos = await bot.get_user_profile_photos(
                                                        user_id,
                                                        limit=1
                                                        )

        if profile_photos and len(profile_photos.photos) > 0:
            photo = profile_photos.photos[0][-1]
            file_id = photo.file_id
            return file_id
        else:
            return None
    except Exception as exc:
        logger.exception(f"Ошибка при получении фото пользователя: {exc}")

        return None