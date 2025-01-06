import sqlite3
from typing import List, Tuple

class Database:
    def __init__(self, db_file="nosy_bot.db"):
        self.db_file = db_file
        self.init_db()

    def init_db(self):
        """Initialize the database with required tables."""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        # Create tasks table
        c.execute('''
            CREATE TABLE IF NOT EXISTS tasks
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             user_id INTEGER NOT NULL,
             task TEXT NOT NULL,
             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
        ''')
        
        conn.commit()
        conn.close()

    def add_task(self, user_id: int, task: str) -> bool:
        """Add a new task for a user."""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        try:
            c.execute('INSERT INTO tasks (user_id, task) VALUES (?, ?)', (user_id, task))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding task: {e}")
            return False
        finally:
            conn.close()

    def get_tasks(self, user_id: int) -> List[Tuple[int, str]]:
        """Get all tasks for a user."""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        c.execute('SELECT id, task FROM tasks WHERE user_id = ? ORDER BY created_at', (user_id,))
        tasks = c.fetchall()
        conn.close()
        
        return tasks

    def delete_task(self, task_id: int, user_id: int) -> bool:
        """Delete a specific task for a user."""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        try:
            c.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
            conn.commit()
            return c.rowcount > 0
        except Exception as e:
            print(f"Error deleting task: {e}")
            return False
        finally:
            conn.close() 