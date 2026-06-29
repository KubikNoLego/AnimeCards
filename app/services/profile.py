import os
import tempfile

import qrcode
from aiogram import Bot
from aiogram.types import FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database.requests import DB

async def create_qr(link:str) -> FSInputFile:
    """Создаёт QR для реферальной ссылки"""
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )
    qr.add_data(link)

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    try:
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(temp_file.name)
        return FSInputFile(temp_file.name)
    except Exception as e:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        logger.exception("Ошибкв при создании QR")
        return

