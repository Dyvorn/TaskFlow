# c:\Users\Lennard Finn Penzler\Documents\VSC_Projects\todo_app\TaskFlow\TaskFlow\build.py

import os
import sys
import subprocess
import shutil

# Import from the source of truth to ensure consistency
try:
    from core.model import APP_NAME, APP_VERSION
except ImportError:
    print("Error: Could not import from core.model. Make sure you are running this from the project root.")
    APP_NAME = "TaskFlow"
    APP_VERSION = "9.0"

# --- Configuration ---
MAIN_SCRIPT = "main.py"
ICON_FILE = "icon.ico"
ISS_FILE = f"{APP_NAME}.iss"

def build():
    """
    Builds the TaskFlow application using PyInstaller.
    """
    print(f"--- Starting build for {APP_NAME} v{APP_VERSION} ---")

    # --- Clean previous builds ---
    print("1. Cleaning previous build artifacts...")
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists(f"{APP_NAME}.spec"):
        os.remove(f"{APP_NAME}.spec")

    # --- PyInstaller command ---
    print(f"2. Running PyInstaller for {MAIN_SCRIPT}...")
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", APP_NAME,
        "--hidden-import", "requests",
        "--hidden-import", "core.analytics", # Critical for the new structure
        "--hidden-import", "ai.engine",      # Critical for the new structure
    ]

    if os.path.exists(ICON_FILE):
        print(f"   - Including icon: {ICON_FILE}")
        cmd.extend(["--icon", ICON_FILE])
    else:
        print("   - Warning: Icon file not found, skipping.")

    cmd.append(MAIN_SCRIPT)

    subprocess.check_call(cmd)

    print(f"--- PyInstaller build complete! ---")
    print(f"Executable created in: {os.path.abspath('dist')}")

    # --- Inno Setup ---
    if os.path.exists(ISS_FILE):
        print(f"3. Compiling Installer with Inno Setup...")
        try:
            iscc_cmd = [
                "iscc",
                f'/DMyAppVersion="{APP_VERSION}"',
                ISS_FILE
            ]
            subprocess.check_call(iscc_cmd)
            print(f"--- Installer created successfully! ---")
        except FileNotFoundError:
            print("Error: 'iscc' command not found. Is Inno Setup installed and in your PATH?")
        except subprocess.CalledProcessError as e:
            print(f"Error compiling installer: {e}")
    else:
        print(f"Warning: {ISS_FILE} not found. Skipping installer generation.")

if __name__ == "__main__":
    build()
