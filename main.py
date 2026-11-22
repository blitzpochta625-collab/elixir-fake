import asyncio
import threading
import os
import re
from flask import Flask
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import Message, ChatPermissions

from config import BOT_TOKEN
from database import init_db, get_chat_settings, toggle_setting
from keyboards import get_admin_keyboard

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# Фейковый сайт для Render
@app.route('/')
def index():
    return "Moderator Bot is working 24/7!"

# --- ХЕНДЛЕРЫ БОТА ---

# Команда /start
@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer("Привет! Я бот-модератор. Добавь меня в чат и дай права администратора.")

# Меню настроек (только для админов)
@dp.message(Command("settings"))
async def settings_cmd(message: Message):
    # Проверяем, админ ли тот, кто пишет
    member = await message.chat.get_member(message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        return
    
    await message.answer("Настройки модерации:", reply_markup=get_admin_keyboard(message.chat.id))

# Обработка кнопок настроек
@dp.callback_query(F.data.startswith("toggle_"))
async def toggle_callback(callback: types.CallbackQuery):
    action, chat_id = callback.data.split(":")
    chat_id = int(chat_id)
    
    setting_name = "anti_spam" if action == "toggle_anti_spam" else "anti_links"
    toggle_setting(chat_id, setting_name)
    
    await callback.answer("Настройка изменена!")
    await callback.message.edit_reply_markup(reply_markup=get_admin_keyboard(chat_id))

# --- МОДЕРАЦИЯ ---

# Фильтр на мат и спам
@dp.message(F.text)
async def moderate_message(message: Message):
    if not message.chat.type in ["group", "supergroup"]:
        return

    settings = get_chat_settings(message.chat.id)
    anti_spam, anti_links = settings

    # 1. Проверка на ссылки
    if anti_links:
        if re.search(r'(https?://|t\.me/)', message.text):
            try:
                await message.delete()
                await message.answer(f"⚠️ {message.from_user.first_name}, ссылки запрещены!")
            except Exception:
                pass # Если бот не админ, он не сможет удалить
            return

    # 2. Проверка на капс (если больше 70% текста капсом)
    if anti_spam:
        if len(message.text) > 10 and sum(1 for c in message.text if c.isupper()) / len(message.text) > 0.7:
            try:
                await message.delete()
                await message.answer(f"⚠️ {message.from_user.first_name}, не пиши капсом!")
            except Exception:
                pass

# Запуск бота в отдельном потоке
def run_bot():
    init_db()
    asyncio.run(dp.start_polling(bot))

# Запуск
if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
