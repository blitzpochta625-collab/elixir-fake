from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_keyboard(chat_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Вкл/Выкл Анти-спам", callback_data=f"toggle_anti_spam:{chat_id}")],
        [InlineKeyboardButton(text="🔗 Вкл/Выкл Анти-ссылки", callback_data=f"toggle_anti_links:{chat_id}")]
    ])
