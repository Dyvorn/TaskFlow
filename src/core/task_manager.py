from datetime import datetime
from typing import List, Dict, Optional, Any
import sqlite3
import logging

from .database import get_connection

def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> Dict[str, Any]:
    """Helper to return sqlite rows as dictionaries."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def add_task(title: str, description: str = "", section: str = "Today", is_important: bool = False) -> Optional[int]:
    """Adds a new task to the database and returns its ID."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tasks (title, description, section, is_important)
                VALUES (?, ?, ?, ?)
            ''', (title, description, section, is_important))
            task_id = cursor.lastrowid
            conn.commit()
            return task_id
    except sqlite3.Error as e:
        logging.error(f"Failed to add task '{title}': {e}")
        return None

def get_tasks(section: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all tasks, optionally filtered by section."""
    try:
        with get_connection() as conn:
            conn.row_factory = dict_factory
            cursor = conn.cursor()
            
            if section:
                cursor.execute('SELECT * FROM tasks WHERE section = ? ORDER BY is_important DESC, created_at DESC', (section,))
            else:
                cursor.execute('SELECT * FROM tasks ORDER BY section, is_important DESC, created_at DESC')
                
            tasks = cursor.fetchall()
            return tasks
    except sqlite3.Error as e:
        logging.error(f"Failed to retrieve tasks: {e}")
        return []

def update_task_status(task_id: int, is_completed: bool) -> bool:
    """Marks a task as completed or incomplete."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            completed_at = datetime.now().isoformat() if is_completed else None
            
            cursor.execute('''
                UPDATE tasks 
                SET is_completed = ?, completed_at = ? 
                WHERE id = ?
            ''', (is_completed, completed_at, task_id))
            
            conn.commit()
            return True
    except sqlite3.Error as e:
        logging.error(f"Failed to update task {task_id}: {e}")
        return False

def delete_task(task_id: int) -> bool:
    """Deletes a task permanently."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
            conn.commit()
            return True
    except sqlite3.Error as e:
        logging.error(f"Failed to delete task {task_id}: {e}")
        return False
