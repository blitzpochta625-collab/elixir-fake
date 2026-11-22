import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не указан в .env")

MAIN_ADMIN_ID = int(os.getenv("MAIN_ADMIN_ID", 0))

ADMIN_IDS = set()
admin_ids_raw = os.getenv("ADMIN_IDS", "")
if admin_ids_raw:
    ADMIN_IDS = {int(x.strip()) for x in admin_ids_raw.split(",") if x.strip().isdigit()}

if MAIN_ADMIN_ID:
    ADMIN_IDS.add(MAIN_ADMIN_ID)

DATABASE_PATH = os.getenv("DATABASE_PATH", "moderator.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
