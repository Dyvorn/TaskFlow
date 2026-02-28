import os
import shutil
import sys

def clean_project():
    """Removes build artifacts, pycache, and other temporary files."""
    print("Starting project cleanup...")
    
    # Get the directory of the script to ensure we run from the project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.getcwd() != script_dir:
        os.chdir(script_dir)

    # --- Directories to remove ---
    dirs_to_remove = [
        "build", 
        "dist", 
        ".pytest_cache", 
        "htmlcov",
        "TaskFlow.egg-info" # Common setuptools artifact
    ]
    
    print("\n--- Removing build and cache directories ---")
    for d in dirs_to_remove:
        if os.path.exists(d):
            print(f"Removing '{d}' directory...")
            try:
                shutil.rmtree(d)
            except Exception as e:
                print(f"  Warning: Could not remove '{d}': {e}")
        else:
            print(f"'{d}' not found, skipping.")

    # --- Specific files to remove from the root ---
    files_to_remove = [
        "crash_report.txt", 
        "temp_voice.wav"
    ]
    
    print("\n--- Removing temporary files ---")
    for f in files_to_remove:
        if os.path.exists(f):
            print(f"Removing '{f}'...")
            try:
                os.remove(f)
            except Exception as e:
                print(f"  Warning: Could not remove '{f}': {e}")
        else:
            print(f"'{f}' not found, skipping.")

    # --- Clean __pycache__ directories recursively ---
    print("\n--- Cleaning __pycache__ directories ---")
    pycache_found = False
    # Walk from the current directory (project root)
    for root, dirs, files in os.walk("."):
        if "__pycache__" in dirs:
            pycache_found = True
            path = os.path.join(root, "__pycache__")
            # Make path relative for cleaner output
            rel_path = os.path.relpath(path)
            print(f"Removing: {rel_path}")
            try:
                shutil.rmtree(path)
            except Exception as e:
                print(f"  Warning: Could not remove '{rel_path}': {e}")
    
    if not pycache_found:
        print("No __pycache__ directories found.")
        
    print("\nCleanup complete! ✨")

if __name__ == "__main__":
    clean_project()