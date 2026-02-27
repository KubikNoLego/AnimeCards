from html import escape

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.keyboards import clan_invite_kb
from app.messages import MText
from db import DB


router = Router()


@router.message(Command("пригласить",prefix="."))
async def _(message: Message, session:AsyncSession):
    db = DB(session)
    sender = await db.get_user(message.from_user.id)

    # Проверка, является ли пользователь лидером клана
    if not sender.clan_member or sender.clan_member.clan.leader_id != sender.id:
        await message.reply(MText.get("not_clan_leader"))
        return

    # Проверка, что команда используется в групповом чате и как ответ на сообщение
    if message.chat.type == "private":
        await message.reply(MText.get("not_in_private_chat"))
        return

    if not message.reply_to_message:
        await message.reply(MText.get("not_in_private_chat"))
        return

    # Получаем пользователя, которого приглашаем
    user = await db.get_user(message.reply_to_message.from_user.id)
    if not user:
        await message.reply(MText.get("not_user").format(name=escape(message.reply_to_message.from_user.full_name)))
        return

    # Проверка, что пользователь не состоит в клане
    if user.clan_member:
        await message.reply(MText.get("user_already_in_clan"))
        return

    # Проверяем, не отправляли ли мы уже приглашение этому пользователю
    existing_invitation = await db.get_clan_invitation(
        sender.clan_member.clan.id, user.id)
    if existing_invitation:
        await message.reply(MText.get("clan_invite_already_sent"))
        return

    # Создаем приглашение в базе данных
    invitation = await db.create_clan_invitation(
        sender.clan_member.clan.id,
        sender.id, user.id)
    if not invitation:
        await message.reply(MText.get("clan_invite_already_sent"))
        return

    # Отправляем приглашение
    try:
        await message.reply(MText.get("clan_invite_success"))
        await message.bot.send_message(user.id,
                        text=MText.get("clan_invite_prompt")
                        .format(clan=sender.clan_member.clan.name),
                        reply_markup= await clan_invite_kb(
                            sender.clan_member.clan_id)
                            )
    except Exception as e:
        logger.error(f"Ошибка при отправке приглашения: {str(e)}", exc_info=True)
        await message.answer(MText.get("invite_send_error"))