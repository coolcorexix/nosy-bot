from typing import List, Tuple
from enum import IntEnum
from datetime import datetime

class TaskState(IntEnum):
    TODO = 0
    WIP = 1
    DONE = 2
    CANCELLED = 3

    def __str__(self):
        return self.name

class Todo:
    db = None  # This will be set by the application
    
    @classmethod
    def get_connection(cls):
        if cls.db is None:
            raise RuntimeError("Database not initialized")
        return cls.db.get_connection()
    
    def __init__(self, user_id: int, task: str, id: int = None, created_at: str = None, 
                 state: TaskState = TaskState.TODO, image_file_id: str = None):
        self.id = id
        self.user_id = user_id
        self.task = task
        self.created_at = created_at
        self.state = state
        self.image_file_id = image_file_id

    @classmethod
    def create(cls, user_id: int, task: str, state: TaskState = TaskState.TODO, 
               image_file_id: str = None) -> int:
        """Create a new todo item with optional initial state and image.
        Returns: task_id if successful, None if failed"""
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''INSERT INTO tasks 
                       (user_id, task, state, image_file_id) 
                       VALUES (?, ?, ?, ?)''',
                    (user_id, task, state, image_file_id)
                )
                return cursor.lastrowid  # Return the ID of the newly created task
        except Exception as e:
            print(f"Error adding task: {e}")
            return None

    @classmethod
    def get_all_by_user(cls, user_id):
        """Get all active tasks (not done or cancelled) for a user."""
        cursor = cls.db.cursor()
        cursor.execute("""
            SELECT id, task, state, image_file_id 
            FROM todos 
            WHERE user_id = ? 
            AND state NOT IN ('DONE', 'CANCELLED')
            ORDER BY id DESC
        """, (user_id,))
        return cursor.fetchall()

    @classmethod
    def get_active_tasks(cls) -> List[Tuple[int, int, str, int]]:
        """Get all active tasks (TODO or WIP) with their user_ids."""
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, user_id, task, state FROM tasks WHERE state != ?',
                (TaskState.DONE,)
            )
            return cursor.fetchall()

    @classmethod
    def update_state(cls, task_id: int, user_id: int, new_state: TaskState) -> bool:
        """Update task state."""
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE tasks SET state = ? WHERE id = ? AND user_id = ?',
                    (new_state, task_id, user_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating task state: {e}")
            return False 

    @classmethod
    def get_all_users(cls) -> List[int]:
        """Get all unique user IDs who have interacted with the bot."""
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT user_id FROM tasks')
            return [row[0] for row in cursor.fetchall()] 

    @classmethod
    def get_done_tasks(cls, user_id: int) -> List[Tuple[int, str, str, str]]:
        """Get completed tasks for a user."""
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT id, task, state, image_file_id 
                   FROM tasks 
                   WHERE user_id = ? AND state = ? 
                   ORDER BY created_at DESC''',
                (user_id, TaskState.DONE)
            )
            return [(id, task, TaskState(state).name, image_file_id) 
                    for id, task, state, image_file_id in cursor.fetchall()] 

    @classmethod
    def cancel_task(cls, task_id: int, user_id: int, cancel_reason: str) -> bool:
        """Cancel a task with a reason."""
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    UPDATE tasks 
                       SET state = ?, cancel_reason = ? 
                       WHERE id = ? AND user_id = ? AND state != ?
                    ''',
                    (TaskState.CANCELLED, cancel_reason, task_id, user_id, TaskState.DONE)
                )
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error cancelling task: {e}")
            return False

    @classmethod
    def get_cancelled_tasks(cls, user_id: int) -> List[Tuple[int, str, str, str, str]]:
        """Get cancelled tasks for a user."""
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT id, task, state, image_file_id, cancel_reason
                   FROM tasks 
                   WHERE user_id = ? AND state = ? 
                   ORDER BY created_at DESC''',
                (user_id, TaskState.CANCELLED)
            )
            return [(id, task, TaskState(state).name, image_file_id, cancel_reason) 
                    for id, task, state, image_file_id, cancel_reason in cursor.fetchall()] 

    @classmethod
    def get_tasks_completed_in_range(cls, user_id: int, start_date: datetime, end_date: datetime) -> List[Tuple[int, str, str, datetime]]:
        """Get tasks completed between start_date and end_date."""
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT id, task, state, created_at 
                FROM tasks 
                WHERE user_id = ? 
                AND state = ? 
                AND created_at BETWEEN ? AND ?
                ORDER BY created_at
            '''
            # Format dates as strings in SQLite format: YYYY-MM-DD HH:MM:SS
            start_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
            end_str = end_date.strftime('%Y-%m-%d %H:%M:%S')
            
            print('Query:', query)
            print('Query params:', user_id, int(TaskState.DONE), start_str, end_str)
            
            cursor.execute(query, (user_id, int(TaskState.DONE), start_str, end_str))
            results = cursor.fetchall()
            print('Query results:', results)
            
            return [(id, task, TaskState(state).name, created_at) 
                    for id, task, state, created_at in cursor.fetchall()] 

    @classmethod
    def get_active_tasks_by_user(cls, user_id):
        """Get all active tasks (not done or cancelled) for a user."""
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, task, state, image_file_id 
                FROM tasks 
                WHERE user_id = ? 
                AND state NOT IN (?, ?)
                ORDER BY id DESC
            """, (user_id, TaskState.DONE, TaskState.CANCELLED))
            return [(id, task, TaskState(state).name, image_file_id) 
                    for id, task, state, image_file_id in cursor.fetchall()] 