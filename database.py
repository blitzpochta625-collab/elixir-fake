# database.py
import sqlite3

def init_db():
    conn = sqlite3.connect("moderator.db")
    cursor = conn.cursor()
    
    # Настройки чатов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            anti_spam INTEGER DEFAULT 1,
            anti_links INTEGER DEFAULT 1,
            anti_mentions INTEGER DEFAULT 1,
            captcha INTEGER DEFAULT 1,
            rules TEXT DEFAULT 'Правила пока не установлены.'
        )
    """)
    
    # Варны (предупреждения)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warns (
            chat_id INTEGER,
            user_id INTEGER,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        )
    """)
    
    # Ключевые слова (Триггеры)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keywords (
            chat_id INTEGER,
            trigger_word TEXT,
            response_text TEXT,
            PRIMARY KEY (chat_id, trigger_word)
        )
    """)
    
    conn.commit()
    conn.close()

def get_chat_settings(chat_id):
    conn = sqlite3.connect("moderator.db")
    cursor = conn.cursor()
    cursor.execute("SELECT anti_spam, anti_links, anti_mentions, captcha, rules FROM chats WHERE chat_id = ?", (chat_id,))
    res = cursor.fetchone()
    if not res:
        cursor.execute("INSERT INTO chats (chat_id) VALUES (?)", (chat_id,))
        conn.commit()
        res = (1, 1, 1, 1, 'Правила пока не установлены.')
    conn.close()
    return res

def toggle_setting(chat_id, setting_name):
    conn = sqlite3.connect("moderator.db")
    cursor = conn.cursor()
    cursor.execute(f"UPDATE chats SET {setting_name} = 1 - {setting_name} WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

def set_rules(chat_id, rules_text):
    conn = sqlite3.connect("moderator.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE chats SET rules = ? WHERE chat_id = ?", (rules_text, chat_id))
    conn.commit()
    conn.close()

def get_warns(chat_id, user_id):
    conn = sqlite3.connect("moderator.db")
    cursor = conn.cursor()
    cursor.execute("SELECT count FROM warns WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 0

def add_warn(chat_id, user_id):
    conn = sqlite3.connect("moderator.db")
    cursor = conn.cursor()
    count = get_warns(chat_id, user_id) + 1
    cursor.execute("INSERT OR REPLACE INTO warns (chat_id, user_id, count) VALUES (?, ?, ?)", (chat_id, user_id, count))
    conn.commit()
    conn.close()
    return count

def reset_warns(chat_id, user_id):
    conn = sqlite3.connect("moderator.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM warns WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
    conn.commit()
    conn.close()

def add_keyword(chat_id, trigger, response):
    conn = sqlite3.connect("moderator.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO keywords (chat_id, trigger_word, response_text) VALUES (?, ?, ?)", (chat_id, trigger.lower(), response))
    conn.commit()
    conn.close()

def get_keywords(chat_id):
    conn = sqlite3.connect("moderator.db")
    cursor = conn.cursor()
    cursor.execute("SELECT trigger_word, response_text FROM keywords WHERE chat_id = ?", (chat_id,))
    res = cursor.fetchall()
    conn.close()
    return res
