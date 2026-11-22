import sqlite3

def init_db():
    conn = sqlite3.connect("moderator.db")
    cursor = conn.cursor()
    # Таблица для настроек чатов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            anti_spam INTEGER DEFAULT 1,
            anti_links INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()

def get_chat_settings(chat_id):
    conn = sqlite3.connect("moderator.db")
    cursor = conn.cursor()
    cursor.execute("SELECT anti_spam, anti_links FROM chats WHERE chat_id = ?", (chat_id,))
    res = cursor.fetchone()
    if not res:
        cursor.execute("INSERT INTO chats (chat_id) VALUES (?)", (chat_id,))
        conn.commit()
        res = (1, 1) # По умолчанию всё включено
    conn.close()
    return res

def toggle_setting(chat_id, setting_name):
    conn = sqlite3.connect("moderator.db")
    cursor = conn.cursor()
    cursor.execute(f"UPDATE chats SET {setting_name} = 1 - {setting_name} WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()
