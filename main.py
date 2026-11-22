import asyncio
import threading
import os
from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from config import BOT_TOKEN, LOG_LEVEL
from database import db
from handlers import setup_routers
from middlewares import AdminCheckMiddleware


app = Flask(__name__)


@app.route("/")
def index():
    return "Moderator Bot is running 24/7!"


def run_flask():
    from waitress import serve
    port = int(os.environ.get("PORT", 8080))
    serve(app, host="0.0.0.0", port=port)


async def main():
    logger.add(
        "bot.log",
        rotation="10 MB",
        retention="7 days",
        level=LOG_LEVEL,
        encoding="utf-8"
    )
    logger.info("Запуск бота...")

    await db.connect()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    dp.message.middleware(AdminCheckMiddleware())
    dp.callback_query.middleware(AdminCheckMiddleware())

    dp.include_router(setup_routers())

    threading.Thread(target=run_flask, daemon=True).start()

    try:
        logger.info("Бот запущен и готов к работе")
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
