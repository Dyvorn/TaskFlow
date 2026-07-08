from datetime import datetime
from .database import get_connection

def add_task(title: str, description: str = "", section: str = "Today", is_important: bool = False) -> int:
    """Adds a new task to the database and returns its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tasks (title, description, section, is_important)
        VALUES (?, ?, ?, ?)
    ''', (title, description, section, is_important))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

def get_tasks(section: str = None) -> list:
    """Retrieves all tasks, optionally filtered by section."""
    conn = get_connection()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    if section:
        cursor.execute('SELECT * FROM tasks WHERE section = ? ORDER BY is_important DESC, created_at DESC', (section,))
    else:
        cursor.execute('SELECT * FROM tasks ORDER BY section, is_important DESC, created_at DESC')
        
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def update_task_status(task_id: int, is_completed: bool):
    """Marks a task as completed or incomplete."""
    conn = get_connection()
    cursor = conn.cursor()
    
    completed_at = datetime.now().isoformat() if is_completed else None
    
    cursor.execute('''
        UPDATE tasks 
        SET is_completed = ?, completed_at = ? 
        WHERE id = ?
    ''', (is_completed, completed_at, task_id))
    
    conn.commit()
    conn.close()

def delete_task(task_id: int):
    """Deletes a task permanently."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()

def dict_factory(cursor, row):
    """Helper to return sqlite rows as dictionaries."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d
