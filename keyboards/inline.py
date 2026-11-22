from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛡 Управление чатом", callback_data="menu_chat_settings")],
        [InlineKeyboardButton(text="📝 Ключевые слова", callback_data="menu_keywords")],
        [InlineKeyboardButton(text="🚫 Чёрный список слов", callback_data="menu_blacklist")],
        [InlineKeyboardButton(text="📖 Правила", callback_data="menu_rules")],
        [InlineKeyboardButton(text="👋 Приветствие", callback_data="menu_welcome")],
    ])


def get_chat_settings_keyboard(chat_id: int, settings: dict) -> InlineKeyboardMarkup:
    def status(key: str) -> str:
        return "✅" if settings.get(key) else "❌"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{status('anti_spam')} Анти-капс / флуд",
            callback_data=f"toggle_{chat_id}_anti_spam"
        )],
        [InlineKeyboardButton(
            text=f"{status('anti_links')} Анти-ссылки",
            callback_data=f"toggle_{chat_id}_anti_links"
        )],
        [InlineKeyboardButton(
            text=f"{status('anti_mentions')} Анти-теги",
            callback_data=f"toggle_{chat_id}_anti_mentions"
        )],
        [InlineKeyboardButton(
            text=f"{status('captcha')} Капча на входе",
            callback_data=f"toggle_{chat_id}_captcha"
        )],
        [InlineKeyboardButton(
            text=f"{status('anti_raid')} Анти-рейд",
            callback_data=f"toggle_{chat_id}_anti_raid"
        )],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")],
    ])


def get_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")]
    ])


def get_captcha_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я не бот", callback_data=f"captcha_{user_id}")]
    ])
