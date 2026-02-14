import os
import sys
import subprocess
import shutil

# --- Configuration ---
APP_NAME = "TaskFlow"
MAIN_SCRIPT = "TaskFlowHub.py"
ICON_FILE = "icon.ico" # Assumes icon is in an assets folder
ISS_FILE = "TaskFlow.iss"


def build():
    """
    Builds the TaskFlow application using PyInstaller.
    """
    print(f"--- Starting build for {APP_NAME} ---")

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
        "--hidden-import", "requests", # Ensure requests is included if available
        "--hidden-import", "taskflowanalytics",
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
            # Assumes ISCC is in PATH. If not, add it or use full path.
            subprocess.check_call(["iscc", ISS_FILE])
            print(f"--- Installer created successfully! ---")
        except FileNotFoundError:
            print("Error: 'iscc' command not found. Is Inno Setup installed and in your PATH?")
        except subprocess.CalledProcessError as e:
            print(f"Error compiling installer: {e}")
    else:
        print(f"Warning: {ISS_FILE} not found. Skipping installer generation.")

if __name__ == "__main__":
    build()