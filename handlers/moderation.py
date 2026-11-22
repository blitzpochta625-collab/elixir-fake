from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest

from database import db
from utils.helpers import (
    parse_time, format_timedelta, is_admin, can_restrict,
    get_mute_permissions, get_unmute_permissions, mention_user
)

router = Router()


async def check_moderation_rights(message: Message, target_id: int) -> bool:
    if not await is_admin(message):
        await message.reply("❌ Только администраторы могут использовать эту команду.")
        return False

    if not await can_restrict(message):
        await message.reply("❌ У бота нет прав на ограничение участников.")
        return False

    try:
        target_member = await message.chat.get_member(target_id)
        if target_member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
            await message.reply("❌ Нельзя применять наказания к администраторам.")
            return False
    except TelegramBadRequest:
        await message.reply("❌ Не удалось получить информацию о пользователе.")
        return False

    if target_id == message.from_user.id:
        await message.reply("❌ Нельзя применять наказания к самому себе.")
        return False

    return True


def get_target(message: Message):
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user
    return None


@router.message(Command("warn", "варн"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_warn(message: Message, command: CommandObject):
    target = get_target(message)
    if not target:
        await message.reply("Ответь на сообщение пользователя, которого хочешь предупредить.")
        return

    if not await check_moderation_rights(message, target.id):
        return

    reason = command.args or "без причины"
    warns = await db.add_warn(message.chat.id, target.id)

    await db.add_log(
        chat_id=message.chat.id,
        moderator_id=message.from_user.id,
        target_id=target.id,
        action="warn",
        reason=reason
    )

    text = (
        f"⚠️ {mention_user(target)} получает предупреждение "
        f"<b>{warns}/3</b>\n"
        f"Причина: {reason}"
    )
    await message.reply(text, parse_mode="HTML")

    if warns >= 3:
        try:
            await message.chat.ban(target.id)
            await db.reset_warns(message.chat.id, target.id)
            await db.add_log(
                chat_id=message.chat.id,
                moderator_id=message.from_user.id,
                target_id=target.id,
                action="ban",
                reason="3 предупреждения"
            )
            await message.answer(f"🔨 {mention_user(target)} забанен за 3 предупреждения.", parse_mode="HTML")
        except TelegramBadRequest as e:
            await message.answer(f"❌ Не удалось забанить: {e}")


@router.message(Command("ban", "бан"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_ban(message: Message, command: CommandObject):
    target = get_target(message)
    if not target:
        await message.reply("Ответь на сообщение пользователя, которого хочешь забанить.")
        return

    if not await check_moderation_rights(message, target.id):
        return

    reason = command.args or "без причины"

    try:
        await message.chat.ban(target.id)
        await db.add_log(
            chat_id=message.chat.id,
            moderator_id=message.from_user.id,
            target_id=target.id,
            action="ban",
            reason=reason
        )
        await message.reply(
            f"🔨 {mention_user(target)} забанен.\nПричина: {reason}",
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        await message.reply(f"❌ Не удалось забанить: {e}")


@router.message(Command("unban", "разбан"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_unban(message: Message, command: CommandObject):
    target = get_target(message)
    if not target:
        if command.args and command.args.isdigit():
            target_id = int(command.args)
        else:
            await message.reply("Ответь на сообщение или укажи ID пользователя.")
            return
    else:
        target_id = target.id

    if not await is_admin(message):
        await message.reply("❌ Только администраторы.")
        return

    try:
        await message.chat.unban(target_id)
        await db.add_log(
            chat_id=message.chat.id,
            moderator_id=message.from_user.id,
            target_id=target_id,
            action="unban"
        )
        name = mention_user(target) if target else f"<code>{target_id}</code>"
        await message.reply(f"✅ {name} разбанен.", parse_mode="HTML")
    except TelegramBadRequest as e:
        await message.reply(f"❌ Ошибка: {e}")


@router.message(Command("mute", "мут"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_mute(message: Message, command: CommandObject):
    target = get_target(message)
    if not target:
        await message.reply("Ответь на сообщение пользователя.")
        return

    if not await check_moderation_rights(message, target.id):
        return

    args = (command.args or "").split(maxsplit=1)
    time_str = args[0] if args else "1ч"
    reason = args[1] if len(args) > 1 else "без причины"

    delta = parse_time(time_str)
    if not delta:
        await message.reply(
            "Неверный формат времени.\n"
            "Примеры: <code>30м</code>, <code>2ч</code>, <code>1д</code>",
            parse_mode="HTML"
        )
        return

    until_date = datetime.now() + delta

    try:
        await message.chat.restrict(
            user_id=target.id,
            permissions=get_mute_permissions(),
            until_date=until_date
        )
        await db.add_log(
            chat_id=message.chat.id,
            moderator_id=message.from_user.id,
            target_id=target.id,
            action="mute",
            reason=reason,
            duration=format_timedelta(delta)
        )
        await message.reply(
            f"🔇 {mention_user(target)} замучен на <b>{format_timedelta(delta)}</b>\n"
            f"Причина: {reason}",
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        await message.reply(f"❌ Не удалось замутить: {e}")


@router.message(Command("unmute", "размут"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_unmute(message: Message, command: CommandObject):
    target = get_target(message)
    if not target:
        await message.reply("Ответь на сообщение пользователя.")
        return

    if not await is_admin(message):
        await message.reply("❌ Только администраторы.")
        return

    try:
        await message.chat.restrict(
            user_id=target.id,
            permissions=get_unmute_permissions()
        )
        await db.add_log(
            chat_id=message.chat.id,
            moderator_id=message.from_user.id,
            target_id=target.id,
            action="unmute"
        )
        await message.reply(f"🔊 {mention_user(target)} размучен.", parse_mode="HTML")
    except TelegramBadRequest as e:
        await message.reply(f"❌ Ошибка: {e}")


@router.message(Command("warns", "варны"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_warns(message: Message):
    target = get_target(message)
    if not target:
        target = message.from_user

    count = await db.get_warns(message.chat.id, target.id)
    await message.reply(
        f"⚠️ У {mention_user(target)} сейчас <b>{count}/3</b> предупреждений.",
        parse_mode="HTML"
    )


@router.message(Command("resetwarns", "сбросварнов"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_resetwarns(message: Message):
    target = get_target(message)
    if not target:
        await message.reply("Ответь на сообщение пользователя.")
        return

    if not await is_admin(message):
        await message.reply("❌ Только администраторы.")
        return

    await db.reset_warns(message.chat.id, target.id)
    await db.add_log(
        chat_id=message.chat.id,
        moderator_id=message.from_user.id,
        target_id=target.id,
        action="resetwarns"
    )
    await message.reply(f"✅ Варны {mention_user(target)} сброшены.", parse_mode="HTML")


@router.message(Command("history", "история"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_history(message: Message):
    target = get_target(message)
    if not target:
        await message.reply("Ответь на сообщение пользователя.")
        return

    if not await is_admin(message):
        await message.reply("❌ Только администраторы.")
        return

    logs = await db.get_user_logs(message.chat.id, target.id, limit=8)
    if not logs:
        await message.reply("История пуста.")
        return

    lines = [f"📋 История {mention_user(target)}:\n"]
    for log in logs:
        action = log["action"]
        reason = log["reason"] or "—"
        duration = f" ({log['duration']})" if log["duration"] else ""
        date = log["created_at"][:16] if log["created_at"] else ""
        lines.append(f"• <b>{action}</b>{duration} — {reason} <i>({date})</i>")

    await message.reply("\n".join(lines), parse_mode="HTML")


@router.message(Command("rules", "правила"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_rules(message: Message):
    settings = await db.get_chat_settings(message.chat.id)
    rules = settings.get("rules") or "Правила пока не установлены."
    await message.reply(f"📖 <b>Правила чата:</b>\n\n{rules}", parse_mode="HTML")
