from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ChatPermissions
from aiogram.exceptions import TelegramBadRequest

from database import db
from keyboards import get_captcha_keyboard
from utils.helpers import get_unmute_permissions, mention_user
from loguru import logger

router = Router()


@router.message(F.new_chat_members)
async def on_new_member(message: Message):
    settings = await db.get_chat_settings(message.chat.id)
    captcha_enabled = settings.get("captcha")

    for user in message.new_chat_members:
        if user.is_bot:
            continue

        if await db.is_globally_blacklisted(user.id):
            try:
                await message.chat.ban(user.id)
                await message.answer(f"🚫 {mention_user(user)} находится в глобальном чёрном списке и был забанен.")
            except TelegramBadRequest:
                pass
            continue

        welcome = settings.get("welcome_text")
        if welcome:
            text = welcome.replace("{name}", user.first_name or "друг")
            text = text.replace("{mention}", mention_user(user))
            try:
                await message.answer(text, parse_mode="HTML")
            except Exception:
                pass

        if not captcha_enabled:
            continue

        try:
            await message.chat.restrict(
                user.id,
                permissions=ChatPermissions(can_send_messages=False)
            )

            await message.answer(
                f"👋 Добро пожаловать, {mention_user(user)}!\n"
                f"Нажми на кнопку ниже в течение 2 минут, чтобы получить доступ к чату.",
                reply_markup=get_captcha_keyboard(user.id),
                parse_mode="HTML"
            )
        except TelegramBadRequest as e:
            logger.warning(f"Не удалось выдать капчу: {e}")


@router.callback_query(F.data.startswith("captcha_"))
async def pass_captcha(callback: CallbackQuery):
    try:
        user_id = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.answer("Ошибка", show_alert=True)
        return

    if callback.from_user.id != user_id:
        await callback.answer("Это не твоя кнопка!", show_alert=True)
        return

    try:
        await callback.message.chat.restrict(
            user_id,
            permissions=get_unmute_permissions()
        )
        await callback.message.delete()
        await callback.answer("✅ Добро пожаловать!")
    except TelegramBadRequest:
        await callback.answer("Не удалось снять ограничения. Обратись к админу.", show_alert=True)
