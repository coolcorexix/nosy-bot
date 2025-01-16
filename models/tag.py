from enum import Enum
from typing import List, Optional

class TagSource(Enum):
    EXTRACTED = 'extracted'  # From task description
    MANUAL = 'manual'       # Added via command
    
    def __str__(self):
        return self.value

class Tag:
    db = None  # Will be set by application

    @classmethod
    def get_connection(cls):
        if cls.db is None:
            raise RuntimeError("Database not initialized")
        return cls.db.get_connection()

    @classmethod
    def create_table(cls):
        """Create tags table if it doesn't exist."""
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    tag TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'extracted',
                    FOREIGN KEY (task_id) REFERENCES tasks(id),
                    UNIQUE(task_id, tag)
                )
            ''')

    @classmethod
    def add_tags_to_task(cls, task_id: int, tags: List[str], source: TagSource = TagSource.EXTRACTED) -> bool:
        """Add multiple tags to a task."""
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(
                    'INSERT OR IGNORE INTO tags (task_id, tag, source) VALUES (?, ?, ?)',
                    [(task_id, tag.lower(), str(source)) for tag in tags]
                )
            return True
        except Exception as e:
            print(f"Error adding tags: {e}")
            return False

    @classmethod
    def get_tags_for_task(cls, task_id: int, include_source: bool = False) -> List[tuple]:
        """Get all tags for a task. Optionally include source information."""
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            if include_source:
                cursor.execute('SELECT tag, source FROM tags WHERE task_id = ?', (task_id,))
                return cursor.fetchall()
            else:
                cursor.execute('SELECT tag FROM tags WHERE task_id = ?', (task_id,))
                return [row[0] for row in cursor.fetchall()]

    @classmethod
    def get_tasks_by_tag(cls, tag: str) -> List[int]:
        """Get all task IDs that have a specific tag."""
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT task_id FROM tags WHERE tag = ?', (tag.lower(),))
            return [row[0] for row in cursor.fetchall()] 