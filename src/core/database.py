import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager
import logging

# Set up basic logging for database operations
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@contextmanager
def get_connection():
    """
    Yields a database connection and ensures it is safely closed.
    Provides context manager support for safe transactions.
    """
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / "taskflow.db"
    
    # Ensure data directory exists
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logging.error(f"Failed to create data directory: {e}")
        raise
        
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        yield conn
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def setup_database():
    """Initializes the database tables if they do not exist."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Create tasks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    section TEXT DEFAULT 'Today',
                    is_important BOOLEAN DEFAULT 0,
                    is_completed BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            ''')
            
            # Create settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            logging.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Failed to setup database: {e}")

if __name__ == "__main__":
    setup_database()
