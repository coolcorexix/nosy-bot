from typing import Any
import sqlite3
from contextlib import contextmanager
import os

class Database:
    def __init__(self, db_file="nosy_bot.db"):
        self.db_file = db_file
        print(f"Initializing database with file: {os.path.abspath(db_file)}")
        self.init_db()

    def init_db(self):
        print(f"Connecting to database at: {os.path.abspath(self.db_file)}")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print("Available tables:", tables)

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_file)
        try:
            yield conn
        finally:
            conn.commit()
            conn.close() 