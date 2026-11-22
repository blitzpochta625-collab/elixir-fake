import re
from datetime import datetime, timedelta
from aiogram.types import Message, ChatPermissions
from aiogram.enums import ChatMemberStatus


def parse_time(time_str: str) -> timedelta | None:
    time_str = time_str.lower().replace(" ", "")
    match = re.match(r"^(\d+(?:\.\d+)?)(с|м|ч|д|s|m|h|d)$", time_str)
    if not match:
        return None

    amount = float(match.group(1))
    unit = match.group(2)

    if unit in ("с", "s"):
        return timedelta(seconds=amount)
    if unit in ("м", "m"):
        return timedelta(minutes=amount)
    if unit in ("ч", "h"):
        return timedelta(hours=amount)
    if unit in ("д", "d"):
        return timedelta(days=amount)
    return None


def format_timedelta(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days:
        parts.append(f"{days}д")
    if hours:
        parts.append(f"{hours}ч")
    if minutes:
        parts.append(f"{minutes}м")
    if seconds and not parts:
        parts.append(f"{seconds}с")
    return " ".join(parts) if parts else "0с"


async def is_admin(message: Message, user_id: int | None = None) -> bool:
    uid = user_id or message.from_user.id
    try:
        member = await message.chat.get_member(uid)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)
    except Exception:
        return False


async def can_restrict(message: Message) -> bool:
    try:
        bot_member = await message.chat.get_member(message.bot.id)
        return (
            bot_member.status == ChatMemberStatus.ADMINISTRATOR
            and bot_member.can_restrict_members
        )
    except Exception:
        return False


def get_mute_permissions() -> ChatPermissions:
    return ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False,
        can_send_polls=False,
        can_invite_users=False,
        can_pin_messages=False,
        can_change_info=False,
    )


def get_unmute_permissions() -> ChatPermissions:
    return ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_send_polls=True,
        can_invite_users=True,
        can_pin_messages=False,
        can_change_info=False,
    )


def mention_user(user) -> str:
    name = user.full_name or user.first_name or "Пользователь"
    return f'<a href="tg://user?id={user.id}">{name}</a>'
