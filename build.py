import os
import shutil
import subprocess
import sys

def clean():
    """Removes previous build artifacts to ensure a fresh compile."""
    dirs = ["build", "dist"]
    for d in dirs:
        if os.path.exists(d):
            print(f"Cleaning '{d}' directory...")
            try:
                shutil.rmtree(d)
            except Exception as e:
                print(f"Warning: Could not remove {d}: {e}")

def build():
    """Runs PyInstaller using the existing spec file."""
    print("Starting PyInstaller build...")
    
    spec_file = "TaskFlow.spec"
    if not os.path.exists(spec_file):
        print(f"Error: {spec_file} not found in current directory!")
        sys.exit(1)

    # Run PyInstaller via subprocess to ensure it uses the current python environment
    try:
        # --clean: Cleans PyInstaller cache
        # --noconfirm: Replace output directory without asking
        subprocess.check_call([sys.executable, "-m", "PyInstaller", spec_file, "--clean", "--noconfirm"])
        print("\n-------------------------------------------------------")
        print("Build successful! Output is located in 'dist/TaskFlow'.")
        print("You can now compile 'taskflow.iss' with Inno Setup.")
        print("-------------------------------------------------------")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error code {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    # Ensure we are in the script's directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    clean()
    build()