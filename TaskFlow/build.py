import os
import shutil
import warnings
import sys
import time

# 1. Aggressively suppress warnings to clean up the console
os.environ["PYTHONWARNINGS"] = "ignore"
warnings.filterwarnings("ignore")

import PyInstaller.__main__

def build():

    # Get absolute path to the script directory
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Ensure we are in the script's directory so PyInstaller finds main.py
    os.chdir(base_path)

    # Define absolute paths for assets
    assets_path = os.path.join(base_path, "assets")
    sounds_path = os.path.join(base_path, "sounds")
    icon_path = os.path.join(base_path, "icon.ico")
    notes_path = os.path.join(base_path, "release_notes.txt")
    dist_dir = os.path.join(base_path, "dist")

    # --- Pre-build Checks ---
    # 1. Ensure assets exist (Brain Model)
    if not os.path.exists(assets_path):
        print("⚠️ 'assets' directory not found. Generating base model...")
        try:
            # Add torch DLL fix here just in case training needs it
            try:
                site_packages = next(p for p in sys.path if 'site-packages' in p)
                torch_lib_path = os.path.join(site_packages, "torch", "lib")
                if os.path.exists(torch_lib_path):
                    os.add_dll_directory(torch_lib_path)
            except Exception:
                pass

            import train_brain_model
            train_brain_model.train_base()
        except Exception as e:
            print(f"❌ Failed to generate assets: {e}")
            os.makedirs(assets_path, exist_ok=True) # Create empty to prevent build crash

    # 2. Ensure sounds directory exists
    if not os.path.exists(sounds_path):
        os.makedirs(sounds_path, exist_ok=True)

    print("🚀 Starting TaskFlow Build Process...")
    print("⏳ Please wait... Analyzing AI dependencies (PyTorch) can take several minutes.")
    start_time = time.time()

    # 1. Clean previous build artifacts
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    if os.path.exists("build"):
        shutil.rmtree("build")

    # 2. Define PyInstaller arguments
    args = [
        'main.py',                       # Entry point
        '--name=TaskFlow',               # Executable name
        '--windowed',                    # No console window
        '--noconfirm',                   # Overwrite output directory
        '--clean',                       # Clean cache
        '--log-level=WARN',              # Reduce noise to see real errors
        
        # Include Data Files (Source;Dest)
        f'--add-data={assets_path}{os.pathsep}assets',
        f'--add-data={sounds_path}{os.pathsep}sounds',
        f'--add-data={notes_path}{os.pathsep}.',
        
        # Hidden imports often missed by PyInstaller
        '--hidden-import=torch',
        '--hidden-import=dateparser',
        '--hidden-import=pyaudio',
        '--hidden-import=faster_whisper',
        '--hidden-import=core.analytics',
        '--hidden-import=ai.engine',
        
        # Optimization: Exclude unnecessary heavy modules if not used
        '--exclude-module=tkinter',
        '--exclude-module=matplotlib',
        '--exclude-module=pygame',
    ]

    # Add icon only if it exists
    if os.path.exists(icon_path):
        args.append(f'--icon={icon_path}')
        args.append(f'--add-data={icon_path}{os.pathsep}.')

    # 3. Run PyInstaller
    try:
        PyInstaller.__main__.run(args)
        
        duration = time.time() - start_time
        print(f"✅ Build Complete in {duration:.1f}s!")
        print(f"📂 Output: {os.path.join(dist_dir, 'TaskFlow')}")
        
        # Check for Inno Setup Compiler
        iss_path = os.path.join(base_path, "TaskFlow.iss")
        if os.path.exists(iss_path):
            print(f"ℹ️  Ready to compile installer. Open '{os.path.basename(iss_path)}' with Inno Setup.")

        # Create Zip Archive
        print("📦 Creating Zip archive...")
        shutil.make_archive(
            base_name=os.path.join(dist_dir, "TaskFlow_v9.0"), 
            format='zip', 
            root_dir=dist_dir, 
            base_dir='TaskFlow'
        )
        print("✅ Zip created successfully.")
        
    except Exception as e:
        print(f"❌ Build Failed: {e}")

if __name__ == "__main__":
    build()