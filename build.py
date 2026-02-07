import os
import subprocess
import shutil
import zipfile

# Configuration
APP_NAME = "TaskFlow"
MAIN_SCRIPT = "TaskFlow.py"
VERSION = "5.1"

def build():
    print(f"Building {APP_NAME} v{VERSION}...")
    
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