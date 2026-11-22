import aiosqlite
from config import DATABASE_PATH
from loguru import logger


class Database:
    def __init__(self):
        self.path = DATABASE_PATH

    async def connect(self):
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self._create_tables()
        logger.info("База данных подключена")

    async def close(self):
        if hasattr(self, "conn"):
            await self.conn.close()
            logger.info("База данных закрыта")

    async def _create_tables(self):
        await self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY,
                anti_spam INTEGER DEFAULT 1,
                anti_links INTEGER DEFAULT 1,
                anti_mentions INTEGER DEFAULT 1,
                captcha INTEGER DEFAULT 1,
                anti_raid INTEGER DEFAULT 0,
                welcome_text TEXT DEFAULT NULL,
                rules TEXT DEFAULT 'Правила пока не установлены.',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS warns (
                chat_id INTEGER,
                user_id INTEGER,
                count INTEGER DEFAULT 0,
                last_warn_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                trigger_word TEXT,
                response_text TEXT,
                UNIQUE(chat_id, trigger_word)
            );

            CREATE TABLE IF NOT EXISTS blacklist_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                word TEXT,
                action TEXT DEFAULT 'delete',
                UNIQUE(chat_id, word)
            );

            CREATE TABLE IF NOT EXISTS moderation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                moderator_id INTEGER,
                target_id INTEGER,
                action TEXT,
                reason TEXT,
                duration TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_stats (
                chat_id INTEGER,
                user_id INTEGER,
                messages_count INTEGER DEFAULT 0,
                warns_count INTEGER DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS global_blacklist (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                added_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await self.conn.commit()

    async def get_chat_settings(self, chat_id: int) -> dict:
        async with self.conn.execute(
            "SELECT * FROM chats WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            await self.conn.execute(
                "INSERT INTO chats (chat_id) VALUES (?)", (chat_id,)
            )
            await self.conn.commit()
            return {
                "anti_spam": 1,
                "anti_links": 1,
                "anti_mentions": 1,
                "captcha": 1,
                "anti_raid": 0,
                "welcome_text": None,
                "rules": "Правила пока не установлены."
            }
        return dict(row)

    async def toggle_setting(self, chat_id: int, setting: str) -> bool:
        allowed = {"anti_spam", "anti_links", "anti_mentions", "captcha", "anti_raid"}
        if setting not in allowed:
            return False
        await self.conn.execute(
            f"UPDATE chats SET {setting} = 1 - {setting} WHERE chat_id = ?",
            (chat_id,)
        )
        await self.conn.commit()
        return True

    async def set_rules(self, chat_id: int, rules: str):
        await self.get_chat_settings(chat_id)
        await self.conn.execute(
            "UPDATE chats SET rules = ? WHERE chat_id = ?", (rules, chat_id)
        )
        await self.conn.commit()

    async def set_welcome(self, chat_id: int, text: str | None):
        await self.get_chat_settings(chat_id)
        await self.conn.execute(
            "UPDATE chats SET welcome_text = ? WHERE chat_id = ?", (text, chat_id)
        )
        await self.conn.commit()

    async def get_warns(self, chat_id: int, user_id: int) -> int:
        async with self.conn.execute(
            "SELECT count FROM warns WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
        return row["count"] if row else 0

    async def add_warn(self, chat_id: int, user_id: int) -> int:
        current = await self.get_warns(chat_id, user_id)
        new_count = current + 1
        await self.conn.execute("""
            INSERT INTO warns (chat_id, user_id, count, last_warn_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                count = excluded.count,
                last_warn_at = CURRENT_TIMESTAMP
        """, (chat_id, user_id, new_count))
        await self.conn.commit()
        return new_count

    async def reset_warns(self, chat_id: int, user_id: int):
        await self.conn.execute(
            "DELETE FROM warns WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        )
        await self.conn.commit()

    async def add_keyword(self, chat_id: int, trigger: str, response: str):
        await self.conn.execute("""
            INSERT INTO keywords (chat_id, trigger_word, response_text)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id, trigger_word) DO UPDATE SET response_text = excluded.response_text
        """, (chat_id, trigger.lower(), response))
        await self.conn.commit()

    async def get_keywords(self, chat_id: int) -> list:
        async with self.conn.execute(
            "SELECT trigger_word, response_text FROM keywords WHERE chat_id = ?",
            (chat_id,)
        ) as cursor:
            rows = await cursor.fetchall()
        return [(r["trigger_word"], r["response_text"]) for r in rows]

    async def remove_keyword(self, chat_id: int, trigger: str) -> bool:
        cursor = await self.conn.execute(
            "DELETE FROM keywords WHERE chat_id = ? AND trigger_word = ?",
            (chat_id, trigger.lower())
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def add_blacklist_word(self, chat_id: int, word: str, action: str = "delete"):
        await self.conn.execute("""
            INSERT INTO blacklist_words (chat_id, word, action)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id, word) DO UPDATE SET action = excluded.action
        """, (chat_id, word.lower(), action))
        await self.conn.commit()

    async def get_blacklist_words(self, chat_id: int) -> list:
        async with self.conn.execute(
            "SELECT word, action FROM blacklist_words WHERE chat_id = ?",
            (chat_id,)
        ) as cursor:
            rows = await cursor.fetchall()
        return [(r["word"], r["action"]) for r in rows]

    async def remove_blacklist_word(self, chat_id: int, word: str) -> bool:
        cursor = await self.conn.execute(
            "DELETE FROM blacklist_words WHERE chat_id = ? AND word = ?",
            (chat_id, word.lower())
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def add_log(self, chat_id: int, moderator_id: int, target_id: int,
                      action: str, reason: str = None, duration: str = None):
        await self.conn.execute("""
            INSERT INTO moderation_logs (chat_id, moderator_id, target_id, action, reason, duration)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (chat_id, moderator_id, target_id, action, reason, duration))
        await self.conn.commit()

    async def get_user_logs(self, chat_id: int, user_id: int, limit: int = 10) -> list:
        async with self.conn.execute("""
            SELECT * FROM moderation_logs
            WHERE chat_id = ? AND target_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (chat_id, user_id, limit)) as cursor:
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def add_global_blacklist(self, user_id: int, reason: str, added_by: int):
        await self.conn.execute("""
            INSERT INTO global_blacklist (user_id, reason, added_by)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET reason = excluded.reason, added_by = excluded.added_by
        """, (user_id, reason, added_by))
        await self.conn.commit()

    async def remove_global_blacklist(self, user_id: int) -> bool:
        cursor = await self.conn.execute(
            "DELETE FROM global_blacklist WHERE user_id = ?", (user_id,)
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def is_globally_blacklisted(self, user_id: int) -> bool:
        async with self.conn.execute(
            "SELECT 1 FROM global_blacklist WHERE user_id = ?", (user_id,)
        ) as cursor:
            return await cursor.fetchone() is not None
