import os
import sys
import subprocess
import shutil
import zipfile

# Configuration
APP_NAME = "TaskFlow"
MAIN_SCRIPT = "TaskFlow.py"
VERSION = "5.3"

def validate_icon(icon_path):
    if not os.path.exists(icon_path):
        print(f"Error: Icon file '{icon_path}' not found.")
        sys.exit(1)
    
    with open(icon_path, "rb") as f:
        header = f.read(4)
        if header.startswith(b'\x89PNG'):
            print(f"CRITICAL: '{icon_path}' is a PNG file renamed to .ico.")
            print("Inno Setup will fail. Please convert it to a real ICO format.")
            sys.exit(1)
        if header != b'\x00\x00\x01\x00':
            print(f"Warning: '{icon_path}' header does not match standard ICO format.")

def build():
    print(f"Building {APP_NAME} v{VERSION}...")
    validate_icon("icon.ico")
    
    # Clean previous builds
    if os.path.exists("dist"): shutil.rmtree("dist")
    if os.path.exists("build"): shutil.rmtree("build")
    if os.path.exists(f"{APP_NAME}_v{VERSION}.spec"): os.remove(f"{APP_NAME}_v{VERSION}.spec")
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", f"{APP_NAME}_v{VERSION}",
        "--clean",
        "--icon", "icon.ico",
        "--add-data", f"README.md{os.pathsep}.",
        "--add-data", f"icon.ico{os.pathsep}.",
        MAIN_SCRIPT
    ]
    
    subprocess.check_call(cmd)
    
    print("Build complete. Creating zip archive...")
    
    # Zip the executable
    exe_name = f"{APP_NAME}_v{VERSION}.exe"
    zip_name = f"{APP_NAME}_v{VERSION}.zip"
    
    with zipfile.ZipFile(os.path.join("dist", zip_name), "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(os.path.join("dist", exe_name), exe_name)
            
    print(f"Release ready: dist/{zip_name}")

if __name__ == "__main__":
    build()