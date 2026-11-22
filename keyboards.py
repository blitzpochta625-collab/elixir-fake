# keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛡 Управление чатом", callback_data="menu_chat_settings")],
        [InlineKeyboardButton(text="📝 Ключевые слова", callback_data="menu_keywords")],
        [InlineKeyboardButton(text="📖 Правила", callback_data="menu_rules")]
    ])

def get_chat_settings_keyboard(chat_id, settings):
    anti_spam, anti_links, anti_mentions, captcha, _ = settings
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{'✅' if anti_spam else '❌'} Анти-флуд", callback_data=f"toggle_{chat_id}_anti_spam")],
        [InlineKeyboardButton(text=f"{'✅' if anti_links else '❌'} Анти-ссылки", callback_data=f"toggle_{chat_id}_anti_links")],
        [InlineKeyboardButton(text=f"{'✅' if anti_mentions else '❌'} Анти-теги", callback_data=f"toggle_{chat_id}_anti_mentions")],
        [InlineKeyboardButton(text=f"{'✅' if captcha else '❌'} Капча на входе", callback_data=f"toggle_{chat_id}_captcha")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
    ])

def get_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
    ])
