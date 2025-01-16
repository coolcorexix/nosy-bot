import sqlite3

class Migration:
    def __init__(self):
        self.description = "🏷️ Add source column to tags table"

    def up(self):
        """Add source column to tags table."""
        try:
            with sqlite3.connect('nosy_bot.db') as conn:
                cursor = conn.cursor()
                
                # Check if source column exists
                cursor.execute("PRAGMA table_info(tags)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'source' not in columns:
                    # Add source column to tags table
                    cursor.execute('''
                        ALTER TABLE tags 
                        ADD COLUMN source TEXT NOT NULL DEFAULT 'extracted'
                    ''')
                    print("✅ Successfully added source column to tags table")
                else:
                    print("👌 Source column already exists in tags table")
                
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            raise

    def down(self):
        """Remove source column from tags table."""
        try:
            with sqlite3.connect('nosy_bot.db') as conn:
                cursor = conn.cursor()
                
                # Check if source column exists
                cursor.execute("PRAGMA table_info(tags)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'source' in columns:
                    # Create temporary table without source column
                    cursor.execute('''
                        CREATE TABLE tags_temp (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            task_id INTEGER NOT NULL,
                            tag TEXT NOT NULL,
                            FOREIGN KEY (task_id) REFERENCES tasks(id),
                            UNIQUE(task_id, tag)
                        )
                    ''')
                    
                    # Copy data to temporary table
                    cursor.execute('''
                        INSERT INTO tags_temp (id, task_id, tag)
                        SELECT id, task_id, tag FROM tags
                    ''')
                    
                    # Drop original table
                    cursor.execute('DROP TABLE tags')
                    
                    # Rename temp table to original
                    cursor.execute('ALTER TABLE tags_temp RENAME TO tags')
                    
                    print("✅ Successfully removed source column from tags table")
                else:
                    print("👌 Source column does not exist in tags table")
                
        except Exception as e:
            print(f"❌ Error during migration rollback: {e}")
            raise 