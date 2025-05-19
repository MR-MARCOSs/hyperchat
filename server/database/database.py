import sqlite3

def get_connection():
    conn = sqlite3.connect("chat.db", check_same_thread=False)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS messages (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           username TEXT NOT NULL,
           message TEXT NOT NULL,
           timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    return conn

def save_message(username: str, message: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (username, message) VALUES (?, ?)", (username, message))
    conn.commit()

def get_last_messages(limit=50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, message, timestamp FROM messages ORDER BY timestamp DESC LIMIT ?", (limit,))
    return cursor.fetchall()
