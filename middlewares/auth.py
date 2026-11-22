from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from config import ADMIN_IDS


class AdminCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
            if event.chat.type in ("group", "supergroup"):
                return await handler(event, data)
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            if event.message and event.message.chat.type in ("group", "supergroup"):
                return await handler(event, data)

        if user and user.id not in ADMIN_IDS and user.id != 6169359403:
            if isinstance(event, Message):
                await event.answer("⛔ У тебя нет доступа к управлению ботом.")
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ Нет доступа", show_alert=True)
            return

        return await handler(event, data)
