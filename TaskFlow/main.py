import os
import sys
from pathlib import Path

# --- PyTorch DLL Fix ---
# This is a workaround for a common PyTorch issue on Windows.
# It manually adds the path to the torch DLLs to the system's DLL search path
# before any other torch import is attempted. This is often necessary when
# environment variables are not configured correctly.
try:
    site_packages = next(p for p in sys.path if 'site-packages' in p)
    torch_lib_path = Path(site_packages) / "torch" / "lib"
    if torch_lib_path.exists():
        os.add_dll_directory(str(torch_lib_path))
except (StopIteration, TypeError):
    pass
# --- End of Fix ---

# Import the AI Engine (Loads Torch) - Must be before PyQt6 to avoid DLL conflicts
from ai.engine import AIEngine

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Import the UI
from ui.hub import HubWindow, SplashWindow, SPLASH_DURATION_MS

# Import Data Model
from core.model import get_data_paths, load_state, save_state, rollover_tasks

def main():
    # 1. Setup Application
    app = QApplication(sys.argv)
    app.setApplicationName("TaskFlow")
    
    # 2. Load State
    paths = get_data_paths()
    state = load_state(paths)
    
    # 3. Daily Maintenance
    rollover_tasks(state)
    save_state(paths, state)
    
    # 4. Splash Screen
    splash = SplashWindow()
    splash.show()
    
    # Create the AI Engine instance for the current user
    ai_engine = AIEngine(user_id="user_123")
    
    # 5. Launch Main Hub
    def show_hub():
        # Keep reference to avoid GC
        show_hub.window = HubWindow(state, paths, ai_engine)
        
        settings = state.get("settings", {})
        if settings.get("startWithHubMaximized", True):
            show_hub.window.showMaximized()
        else:
            show_hub.window.show()
            
    QTimer.singleShot(SPLASH_DURATION_MS, show_hub)
    
    # 6. Run
    sys.exit(app.exec())

if __name__ == "__main__":
    main()