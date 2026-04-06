from html import escape

from aiogram.types import Message
from loguru import logger

from app.database.models import User
from app.database.requests import DB
from app.messages.MessageControl import MText
from .enums.invite_enums import InviteEnum

async def check_user_invite(user_id: int,
        inviter_id: int,
        action: bool) -> InviteEnum:
    if not inviter_id:
        return InviteEnum.NOT_USER

    if not inviter_id != user_id:
        return InviteEnum.CANT_BE_REFERRAL

    if not action:
        return InviteEnum.ONLY_NEW_USERS
    
    return InviteEnum.SUCCESS


async def send_message_to_users(message: Message, inviter: User,
                                user: User) -> None:
    referrer_link = f'<a href="tg://user?id={inviter.id}">{escape(inviter.name)}</a>'
    new_user_link = f'<a href="tg://user?id={user.id}">{escape(user.name)}</a>'

    await message.reply(MText.get("referral_welcome").format(referrer_link=referrer_link))

    try:
        await message.bot.send_message(
            inviter.id,
            MText.get("new_referral").format(link=new_user_link)
            )
        await message.bot.send_message(
                inviter.id,
                MText.get("reward_message").format(
                    reward=1 if not inviter.vip else 2,
                    opens=inviter.free_open)
                )
    except Exception as e:
        logger.exception(f"Не удалось отправить сообщение реферреру {inviter.id}: {e}")
