from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from database import db
from keyboards import get_main_menu_keyboard, get_chat_settings_keyboard, get_back_keyboard

router = Router()


@router.message(Command("start"), F.chat.type == "private")
async def cmd_start(message: Message):
    await message.answer(
        "👑 <b>Панель управления ботом</b>\n\n"
        "Выбери раздел для настройки:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "menu_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "👑 <b>Главное меню</b>",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "menu_chat_settings")
async def menu_chat_settings(callback: CallbackQuery):
    await callback.message.edit_text(
        "Отправь мне <b>ID чата</b> (например <code>-1001234567890</code>), "
        "чтобы настроить его:",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(F.chat.type == "private", F.text.regexp(r"^-?\d+$"))
async def open_chat_settings(message: Message):
    chat_id = int(message.text)
    settings = await db.get_chat_settings(chat_id)
    await message.answer(
        f"⚙️ Настройки для чата <code>{chat_id}</code>:",
        reply_markup=get_chat_settings_keyboard(chat_id, settings),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("toggle_"))
async def toggle_setting_handler(callback: CallbackQuery):
    try:
        _, chat_id, setting_name = callback.data.split("_", 2)
        chat_id = int(chat_id)
    except ValueError:
        await callback.answer("Ошибка данных", show_alert=True)
        return

    success = await db.toggle_setting(chat_id, setting_name)
    if not success:
        await callback.answer("Неизвестная настройка", show_alert=True)
        return

    settings = await db.get_chat_settings(chat_id)
    await callback.message.edit_reply_markup(
        reply_markup=get_chat_settings_keyboard(chat_id, settings)
    )
    await callback.answer("Настройка изменена!")


@router.callback_query(F.data == "menu_rules")
async def menu_rules(callback: CallbackQuery):
    await callback.message.edit_text(
        "Отправь ID чата и через пробел текст правил.\n\n"
        "Пример:\n<code>-1001234567890 Не спамить и не оскорблять!</code>",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(F.chat.type == "private", F.text.regexp(r"^-?\d+\s.+"))
async def set_rules_handler(message: Message):
    parts = message.text.split(" ", 2)
    if len(parts) >= 3 and not parts[1].startswith("-"):
        return

    parts = message.text.split(" ", 1)
    chat_id = int(parts[0])
    rules_text = parts[1]
    await db.set_rules(chat_id, rules_text)
    await message.answer("✅ Правила успешно обновлены!")


@router.callback_query(F.data == "menu_keywords")
async def menu_keywords(callback: CallbackQuery):
    await callback.message.edit_text(
        "Отправь ID чата, триггер и ответ через пробел.\n\n"
        "Пример:\n<code>-1001234567890 привет Приветствую тебя!</code>\n\n"
        "Чтобы удалить: <code>-1001234567890 !привет</code>",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(F.chat.type == "private", F.text.regexp(r"^-?\d+\s\S+\s.+"))
async def add_keyword_handler(message: Message):
    parts = message.text.split(" ", 2)
    chat_id = int(parts[0])
    trigger = parts[1]
    response_text = parts[2]

    if trigger.startswith("!"):
        trigger = trigger[1:]
        removed = await db.remove_keyword(chat_id, trigger)
        if removed:
            await message.answer(f"🗑 Триггер <code>{trigger}</code> удалён.", parse_mode="HTML")
        else:
            await message.answer("Такого триггера нет.")
        return

    await db.add_keyword(chat_id, trigger, response_text)
    await message.answer(f"✅ Триггер <code>{trigger}</code> добавлен!", parse_mode="HTML")


@router.callback_query(F.data == "menu_blacklist")
async def menu_blacklist(callback: CallbackQuery):
    await callback.message.edit_text(
        "Чёрный список слов.\n\n"
        "Формат:\n<code>-1001234567890 слово delete/warn/ban</code>\n\n"
        "Пример:\n<code>-1001234567890 дурак warn</code>\n\n"
        "Удалить: <code>-1001234567890 !дурак</code>",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "menu_welcome")
async def menu_welcome(callback: CallbackQuery):
    await callback.message.edit_text(
        "Установка приветственного сообщения.\n\n"
        "Формат:\n<code>-1001234567890 Текст приветствия</code>\n\n"
        "Чтобы отключить: <code>-1001234567890 off</code>",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()
