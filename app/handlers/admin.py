# Стандартные библиотеки
from datetime import datetime, timedelta, timezone
from html import escape

# Сторонние библиотеки
from aiogram import Router,F
from aiogram.types import Message,FSInputFile
from aiogram.fsm.context import FSMContext
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Локальные импорты
from app.func import (card_formatter, not_user, nottime, profile_creator,
                    profile_step2_tutorial, profile_tutorial,
                    random_card, user_photo_link, _load_messages,
                    top_players_formatter, top_collections_formatter, create_qr)
from app.keyboards import profile_keyboard, shop_keyboard
from db.models import Card, User
from db.requests import RedisRequests