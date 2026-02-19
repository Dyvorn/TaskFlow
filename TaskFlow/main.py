import os
import sys
import time
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
from PyQt6.QtCore import QTimer, QRect

# Import the UI
from ui.hub import HubWindow, SplashWindow, SPLASH_DURATION_MS

# Import Data Model
from core.model import get_data_paths, load_state, save_state, rollover_tasks

def main():
    # 1. Setup Application
    app = QApplication(sys.argv)
    app.setApplicationName("TaskFlow")
    
    # Prevent app from closing when splash screen closes before main window opens
    app.setQuitOnLastWindowClosed(False)
    
    # 2. Load State
    paths = get_data_paths()
    state = load_state(paths)
    
    # 3. Daily Maintenance
    rollover_tasks(state)
    save_state(paths, state)
    
    # 4. Splash Screen
    splash = SplashWindow()
    splash.show()
    app.processEvents() # Ensure splash paints before AI load
    
    # Track timing for smooth progress
    start_time = time.time()
    min_duration_ms = 3000  # Minimum 3 seconds
    ai_engine = [None]  # Store AI engine when ready
    ai_ready = [False]  # Flag to track if AI loading is done
    finish_loading_called = [False]  # Track if we've called finish_loading
    
    # Start progress animation (smooth linear fill over minimum duration)
    progress_timer = QTimer()
    
    # Prepare Hub Window variable (closure access)
    hub_window = [None]
    
    # Calculate target geometry for the transition
    settings = state.get("settings", {})
    start_maximized = settings.get("startWithHubMaximized", True)
    target_rect = QRect()
    
    if start_maximized:
        target_rect = app.primaryScreen().availableGeometry()
    else:
        geom = state.get("uiGeometry")
        if geom:
            target_rect = QRect(*geom)
        else:
            geo = app.primaryScreen().availableGeometry()
            w, h = 1200, 800
            target_rect = QRect(
                geo.center().x() - w // 2,
                geo.center().y() - h // 2,
                w, h
            )

    def on_transition_done():
        """Called when splash morphing is complete."""
        if hub_window[0]:
            if start_maximized:
                hub_window[0].showMaximized()
            else:
                hub_window[0].show()
                hub_window[0].setGeometry(target_rect)
            
            # Start popups (Welcome, Daily Plan) only NOW that the Hub is visible
            hub_window[0].start_post_load_tasks()
            
        splash.close()

    def update_progress():
        elapsed_ms = (time.time() - start_time) * 1000
        
        if ai_ready[0] and elapsed_ms >= min_duration_ms and not finish_loading_called[0]:
            # AI is ready AND minimum duration has passed
            splash.set_progress(100)
            finish_loading_called[0] = True
            progress_timer.stop()
            
            # Create Hub Window NOW (so it's ready)
            hub_window[0] = HubWindow(state, paths, ai_engine[0])
            
            # Start smooth transition
            splash.transition_to_main(target_rect, on_transition_done)
        else:
            # Keep filling progress bar linearly up to 90% over minimum duration
            progress = min(90, (elapsed_ms / min_duration_ms) * 100)
            splash.set_progress(int(progress))
    
    progress_timer.timeout.connect(update_progress)
    progress_timer.start(50)  # Update every 50ms for smooth animation
    
    # Load AI in background thread
    import threading
    
    def load_ai():
        try:
            ai_engine[0] = AIEngine(user_id="user_123", state=state)
        except Exception as e:
            print(f"DEBUG: AI engine error: {e}")
        finally:
            ai_ready[0] = True
    
    ai_thread = threading.Thread(target=load_ai, daemon=True)
    ai_thread.start()
    
    
    # 6. Run
    sys.exit(app.exec())

if __name__ == "__main__":
    main()