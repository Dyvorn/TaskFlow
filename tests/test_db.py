import os
import sys

# Ensure we can import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.database import setup_database
from core.task_manager import add_task, get_tasks, update_task_status, delete_task

def run_tests():
    print("Setting up database...")
    setup_database()
    
    print("Adding a test task...")
    task_id = add_task(title="Hello World", description="Testing the new DB", section="Today", is_important=True)
    print(f"Task added with ID: {task_id}")
    
    print("Fetching tasks...")
    tasks = get_tasks()
    for t in tasks:
        print(t)
        
    print(f"Completing task {task_id}...")
    update_task_status(task_id, is_completed=True)
    
    print("Fetching tasks again...")
    tasks = get_tasks()
    for t in tasks:
        print(t)
        
    print(f"Cleaning up task {task_id}...")
    delete_task(task_id)
    
    print("Done!")

if __name__ == "__main__":
    run_tests()
