import sqlite3
from contextlib import contextmanager

class Migration:
    def __init__(self, db_file="nosy_bot.db"):
        self.db_file = db_file

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_file)
        try:
            yield conn
        finally:
            conn.commit()
            conn.close()

    def up(self):
        """Add state column to tasks table"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Check if state column exists
                cursor.execute("PRAGMA table_info(tasks)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'state' not in columns:
                    cursor.execute('''
                        ALTER TABLE tasks 
                        ADD COLUMN state INTEGER DEFAULT 0
                    ''')
                    print("✅ Successfully added state column to tasks table")
                else:
                    print("ℹ️ State column already exists in tasks table")
            except Exception as e:
                print(f"❌ Error during migration: {e}")
                raise e

    def down(self):
        """Remove state column from tasks table (SQLite doesn't support dropping columns directly)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Create new table without state column
                cursor.execute('''
                    CREATE TABLE tasks_new
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id INTEGER NOT NULL,
                     task TEXT NOT NULL,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
                ''')
                
                # Copy data
                cursor.execute('''
                    INSERT INTO tasks_new (id, user_id, task, created_at)
                    SELECT id, user_id, task, created_at FROM tasks
                ''')
                
                # Drop old table
                cursor.execute('DROP TABLE tasks')
                
                # Rename new table
                cursor.execute('ALTER TABLE tasks_new RENAME TO tasks')
                
                print("✅ Successfully removed state column from tasks table")
            except Exception as e:
                print(f"❌ Error during migration rollback: {e}")
                raise e 