from typing import Any
import sqlite3
from contextlib import contextmanager

class Database:
    def __init__(self, db_file="nosy_bot.db"):
        self.db_file = db_file
        self.init_db()

    def init_db(self):
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 task TEXT NOT NULL,
                 state INTEGER DEFAULT 0,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
            ''')

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_file)
        try:
            yield conn
        finally:
            conn.commit()
            conn.close()

db = Database() 