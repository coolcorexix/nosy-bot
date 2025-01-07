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
        """Add image_file_id column to tasks table"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("PRAGMA table_info(tasks)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'image_file_id' not in columns:
                    cursor.execute('''
                        ALTER TABLE tasks 
                        ADD COLUMN image_file_id TEXT
                    ''')
                    print("✅ Successfully added image_file_id column to tasks table")
                else:
                    print("ℹ️ image_file_id column already exists in tasks table")
            except Exception as e:
                print(f"❌ Error during migration: {e}")
                raise e

    def down(self):
        """Remove image_file_id column from tasks table"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Create new table without image_file_id column
                cursor.execute('''
                    CREATE TABLE tasks_new
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id INTEGER NOT NULL,
                     task TEXT NOT NULL,
                     state INTEGER DEFAULT 0,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
                ''')
                
                # Copy data
                cursor.execute('''
                    INSERT INTO tasks_new (id, user_id, task, state, created_at)
                    SELECT id, user_id, task, state, created_at FROM tasks
                ''')
                
                # Drop old table
                cursor.execute('DROP TABLE tasks')
                
                # Rename new table
                cursor.execute('ALTER TABLE tasks_new RENAME TO tasks')
                
                print("✅ Successfully removed image_file_id column from tasks table")
            except Exception as e:
                print(f"❌ Error during migration rollback: {e}")
                raise e 