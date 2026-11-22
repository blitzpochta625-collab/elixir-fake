import re
from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest

from database import db
from utils.helpers import mention_user

router = Router()


@router.message(F.text, F.chat.type.in_({"group", "supergroup"}))
async def auto_moderator(message: Message):
    if not message.from_user or message.from_user.is_bot:
        return

    try:
        member = await message.chat.get_member(message.from_user.id)
        if member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
            return
    except Exception:
        return

    chat_id = message.chat.id
    settings = await db.get_chat_settings(chat_id)
    text = message.text or ""
    text_lower = text.lower()

    # 1. Ключевые слова
    keywords = await db.get_keywords(chat_id)
    for trigger, response in keywords:
        if re.search(rf"\b{re.escape(trigger)}\b", text_lower):
            try:
                await message.reply(response)
            except TelegramBadRequest:
                pass
            break

    # 2. Чёрный список слов
    blacklist = await db.get_blacklist_words(chat_id)
    for word, action in blacklist:
        if re.search(rf"\b{re.escape(word)}\b", text_lower):
            try:
                await message.delete()
            except TelegramBadRequest:
                pass

            if action == "warn":
                warns = await db.add_warn(chat_id, message.from_user.id)
                await message.answer(
                    f"⚠️ {mention_user(message.from_user)} использовал запрещённое слово.\n"
                    f"Предупреждение {warns}/3",
                    parse_mode="HTML"
                )
                if warns >= 3:
                    try:
                        await message.chat.ban(message.from_user.id)
                        await db.reset_warns(chat_id, message.from_user.id)
                    except TelegramBadRequest:
                        pass
            elif action == "ban":
                try:
                    await message.chat.ban(message.from_user.id)
                    await message.answer(
                        f"🔨 {mention_user(message.from_user)} забанен за запрещённое слово.",
                        parse_mode="HTML"
                    )
                except TelegramBadRequest:
                    pass
            else:
                await message.answer(
                    f"⚠️ {mention_user(message.from_user)}, это слово запрещено.",
                    parse_mode="HTML"
                )
            return

    # 3. Анти-ссылки
    if settings.get("anti_links") and re.search(r"(https?://|t\.me/|www\.)", text, re.IGNORECASE):
        try:
            await message.delete()
            await message.answer(
                f"⚠️ {mention_user(message.from_user)}, ссылки запрещены!",
                parse_mode="HTML"
            )
        except TelegramBadRequest:
            pass
        return

    # 4. Анти-теги
    if settings.get("anti_mentions") and message.entities:
        mentions = sum(1 for e in message.entities if e.type in ("mention", "text_mention"))
        if mentions > 5:
            try:
                await message.delete()
                await message.answer(
                    f"⚠️ {mention_user(message.from_user)}, массовые теги запрещены!",
                    parse_mode="HTML"
                )
            except TelegramBadRequest:
                pass
            return

    # 5. Анти-капс
    if settings.get("anti_spam") and len(text) > 15:
        upper_ratio = sum(1 for c in text if c.isupper()) / len(text)
        if upper_ratio > 0.7:
            try:
                await message.delete()
                await message.answer(
                    f"⚠️ {mention_user(message.from_user)}, не пиши капсом!",
                    parse_mode="HTML"
                )
            except TelegramBadRequest:
                pass
            return
