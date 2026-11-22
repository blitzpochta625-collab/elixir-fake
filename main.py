# main.py
import asyncio
import threading
import os
import re
import time
from datetime import datetime, timedelta
from flask import Flask
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, ChatPermissions, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from config import BOT_TOKEN, MAIN_ADMIN_ID
from database import (
    init_db, get_chat_settings, toggle_setting, set_rules, 
    get_warns, add_warn, reset_warns, add_keyword, get_keywords
)
from keyboards import get_main_menu_keyboard, get_chat_settings_keyboard, get_back_keyboard

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (чтобы не засыпал) ---
@app.route('/')
def index():
    return "CoreHelp Bot is running 24/7!"

def run_flask():
    from waitress import serve
    port = int(os.environ.get('PORT', 8080))
    serve(app, host='0.0.0.0', port=port)

# ==========================================
# 1. ЛИЧКА БОТА (УПРАВЛЕНИЕ)
# ==========================================

@dp.message(Command("start"), F.chat.type == "private")
async def start_private(message: Message):
    if message.from_user.id != MAIN_ADMIN_ID:
        await message.answer("⛔ У тебя нет доступа к управлению ботом.")
        return
    await message.answer(
        "👑 Привет, Главный Админ!\nВыбери раздел для настройки:",
        reply_markup=get_main_menu_keyboard()
    )

@dp.callback_query(F.data == "menu_main")
async def back_to_main(callback: CallbackQuery):
    if callback.from_user.id != MAIN_ADMIN_ID: return
    await callback.message.edit_text(
        "👑 Главное меню:", 
        reply_markup=get_main_menu_keyboard()
    )

@dp.callback_query(F.data == "menu_chat_settings")
async def chat_settings_menu(callback: CallbackQuery):
    if callback.from_user.id != MAIN_ADMIN_ID: return
    await callback.message.edit_text(
        "Отправь мне ID чата (например, -1001234567890), чтобы настроить его:", 
        reply_markup=get_back_keyboard()
    )

# Настройка чата по его ID
@dp.message(F.chat.type == "private", F.text.regexp(r"^-?\d+$"))
async def open_chat_settings(message: Message):
    if message.from_user.id != MAIN_ADMIN_ID: return
    chat_id = int(message.text)
    settings = get_chat_settings(chat_id)
    await message.answer(
        f"⚙️ Настройки для чата `{chat_id}`:",
        parse_mode="Markdown",
        reply_markup=get_chat_settings_keyboard(chat_id, settings)
    )

# Переключение кнопок (Вкл/Выкл)
@dp.callback_query(F.data.startswith("toggle_"))
async def toggle_setting_handler(callback: CallbackQuery):
    if callback.from_user.id != MAIN_ADMIN_ID: return
    _, chat_id, setting_name = callback.data.split("_", 2)
    chat_id = int(chat_id)
    
    toggle_setting(chat_id, setting_name)
    settings = get_chat_settings(chat_id)
    
    await callback.message.edit_reply_markup(reply_markup=get_chat_settings_keyboard(chat_id, settings))
    await callback.answer("Настройка изменена!")

# Добавление правил
@dp.callback_query(F.data == "menu_rules")
async def rules_menu(callback: CallbackQuery):
    if callback.from_user.id != MAIN_ADMIN_ID: return
    await callback.message.edit_text(
        "Отправь ID чата и через пробел текст правил.\nПример: `-1001234567890 Не спамить!`",
        reply_markup=get_back_keyboard()
    )

@dp.message(F.chat.type == "private", F.text.regexp(r"^-?\d+\s.+"))
async def set_rules_handler(message: Message):
    if message.from_user.id != MAIN_ADMIN_ID: return
    parts = message.text.split(" ", 1)
    chat_id = int(parts[0])
    rules_text = parts[1]
    set_rules(chat_id, rules_text)
    await message.answer("✅ Правила успешно обновлены!")

# Ключевые слова (Добавление)
@dp.callback_query(F.data == "menu_keywords")
async def keywords_menu(callback: CallbackQuery):
    if callback.from_user.id != MAIN_ADMIN_ID: return
    await callback.message.edit_text(
        "Отправь ID чата, триггер и ответ через пробел.\nПример: `-1001234567890 привет Приветствую тебя!`",
        reply_markup=get_back_keyboard()
    )

@dp.message(F.chat.type == "private", F.text.regexp(r"^-?\d+\s\S+\s.+"))
async def add_keyword_handler(message: Message):
    if message.from_user.id != MAIN_ADMIN_ID: return
    parts = message.text.split(" ", 2)
    chat_id = int(parts[0])
    trigger = parts[1]
    response_text = parts[2]
    add_keyword(chat_id, trigger, response_text)
    await message.answer(f"✅ Триггер `{trigger}` добавлен!")

# ==========================================
# 2. РАБОТА В ЧАТЕ (МОДЕРАЦИЯ)
# ==========================================

# Команда /rules в чате
@dp.message(Command("rules"), F.chat.type.in_({"group", "supergroup"}))
async def send_rules(message: Message):
    _, _, _, _, rules = get_chat_settings(message.chat.id)
    await message.reply(f"📖 **Правила чата:**\n\n{rules}", parse_mode="Markdown")

# БАН, МУТ, ВАРН (Только через реплай)
@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def moderation_commands(message: Message):
    if not message.reply_to_message: return
    text = message.text.lower()
    
    # Проверяем, админ ли тот, кто пишет
    member = await message.chat.get_member(message.from_user.id)
    if member.status not in ["administrator", "creator"]: return

    target_user = message.reply_to_message.from_user
    target_name = target_user.first_name

    # ВАРН
    if text == "варн":
        warns = add_warn(message.chat.id, target_user.id)
        await message.reply(f"⚠️ {target_name} получает предупреждение {warns}/3.")
        if warns >= 3:
            try:
                await message.chat.ban(target_user.id)
                await message.reply(f"🔨 {target_name} забанен за 3 предупреждения!")
                reset_warns(message.chat.id, target_user.id)
            except:
                await message.reply("❌ У бота нет прав на бан.")

    # БАН
    elif text == "бан":
        try:
            await message.chat.ban(target_user.id)
            await message.reply(f"🔨 {target_name} отправлен в бан.")
        except:
            await message.reply("❌ У бота нет прав на бан.")

    # МУТ (формат "мут 5м" или "мут 1ч")
    elif text.startswith("мут"):
        match = re.search(r'(\d+)\s*([мчд])', text)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            
            if unit == 'м': delta = timedelta(minutes=amount)
            elif unit == 'ч': delta = timedelta(hours=amount)
            elif unit == 'д': delta = timedelta(days=amount)
            else: return

            until_date = datetime.now() + delta
            try:
                await message.chat.restrict(
                    target_user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until_date
                )
                await message.reply(f"🔇 {target_name} замучен на {amount}{unit}.")
            except:
                await message.reply("❌ У бота нет прав на мут.")

# ==========================================
# 3. АВТОМАТИЧЕСКИЕ ФИЛЬТРЫ И КАПЧА
# ==========================================

# Приветствие и Капча для новых участников
@dp.message(F.new_chat_members)
async def captcha_handler(message: Message):
    settings = get_chat_settings(message.chat.id)
    captcha = settings[3]
    
    if not captcha: return

    for user in message.new_chat_members:
        if user.is_bot: continue
        try:
            # Ограничиваем права до нажатия кнопки
            await message.chat.restrict(user.id, permissions=ChatPermissions(can_send_messages=False))
            
            # Отправляем кнопку
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="✅ Я не бот", callback_data=f"captcha_{user.id}")]
            ])
            await message.answer(f"👋 Добро пожаловать, {user.first_name}!\nНажми на кнопку ниже, чтобы получить доступ к чату.", reply_markup=kb)
        except:
            pass

@dp.callback_query(F.data.startswith("captcha_"))
async def pass_captcha(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    if callback.from_user.id != user_id:
        await callback.answer("Это не твоя кнопка!", show_alert=True)
        return
        
    try:
        # Возвращаем права
        await callback.message.chat.restrict(user_id, permissions=ChatPermissions(
            can_send_messages=True, can_send_media_messages=True, 
            can_send_other_messages=True, can_add_web_page_previews=True
        ))
        await callback.message.delete()
    except:
        pass

# Анти-спам, Анти-ссылки, Анти-теги, Ключевые слова
@dp.message(F.text, F.chat.type.in_({"group", "supergroup"}))
async def auto_moderator(message: Message):
    if message.from_user.is_bot: return
    
    # Пропускаем админов
    member = await message.chat.get_member(message.from_user.id)
    if member.status in ["administrator", "creator"]: return

    settings = get_chat_settings(message.chat.id)
    anti_spam, anti_links, anti_mentions, _, _ = settings

    # 1. КЛЮЧЕВЫЕ СЛОВА
    keywords = get_keywords(message.chat.id)
    for trigger, response in keywords:
        if re.search(rf'\b{re.escape(trigger)}\b', message.text.lower()):
            await message.reply(response)

    # 2. АНТИ-ССЫЛКИ
    if anti_links and re.search(r'(https?://|t\.me/)', message.text):
        try:
            await message.delete()
            await message.answer(f"⚠️ {message.from_user.first_name}, ссылки запрещены!")
        except:
            pass
        return

    # 3. АНТИ-ТЕГИ (Больше 5 тегов)
    if anti_mentions and message.entities:
        mentions = sum(1 for entity in message.entities if entity.type == "mention")
        if mentions > 5:
            try:
                await message.delete()
                await message.answer(f"⚠️ {message.from_user.first_name}, массовые теги запрещены!")
            except:
                pass
            return

    # 4. АНТИ-КАПС
    if anti_spam and len(message.text) > 10 and sum(1 for c in message.text if c.isupper()) / len(message.text) > 0.7:
        try:
            await message.delete()
            await message.answer(f"⚠️ {message.from_user.first_name}, не пиши капсом!")
        except:
            pass

# --- ЗАПУСК ---
if __name__ == '__main__':
    init_db()
    threading.Thread(target=run_flask, daemon=True).start()
    print("Бот запущен...")
    asyncio.run(dp.start_polling(bot))
