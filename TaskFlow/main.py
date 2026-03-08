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
from PyQt6.QtCore import QTimer, QRect, QObject, pyqtSignal, QThread

# Import the UI
from ui.hub import HubWindow, SplashWindow

# Import Data Model
from core.model import get_data_paths, load_state, save_state, rollover_tasks

class AILoader(QObject):
    """
    Worker object to load the AI engine in a separate thread.
    """
    finished = pyqtSignal(object)  # Emits the loaded AI engine instance
    error = pyqtSignal()           # Emits on failure

    def __init__(self, state):
        super().__init__()
        self.state = state

    def run(self):
        """Load the AI engine."""
        try:
            ai_engine = AIEngine(user_id="user_123", state=self.state)
            self.finished.emit(ai_engine)
        except Exception as e:
            print(f"DEBUG: AI engine error: {e}")
            self.error.emit()

def main():
    # 1. Setup Application
    app = QApplication(sys.argv)
    app.setApplicationName("TaskFlow")

    # Global stylesheet for consistency (fixed syntax)
    app.setStyleSheet("""
        QScrollBar:vertical {
            border: none;
            background: transparent;
            width: 6px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: rgba(255, 255, 255, 0.1);
            min-height: 20px;
            border-radius: 3px;
        }
        QScrollBar::handle:vertical:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
            height: 0px;
        }
        QToolTip {
            background-color: #252525;
            color: #e0e0e0;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 4px;
            border-radius: 4px;
        }
        QMenu {
            background-color: #1E1E1E;
            color: #e0e0e0;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 5px;
        }
        QMenu::item {
            padding: 6px 20px;
            border-radius: 4px;
        }
        QMenu::item:selected {
            background-color: rgba(255, 215, 0, 0.15);
            color: #ffd700;
        }
    """)
    
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
    ai_engine = None  # Store AI engine when ready
    ai_loading_finished = False # Flag to track if AI loading is done
    transition_started = False  # Track if we've started the transition
    
    # Start progress animation (smooth linear fill over minimum duration)
    progress_timer = QTimer()
    
    # Prepare Hub Window variable (closure access)
    hub_window = None
    
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
        # By the time this is called, hub_window is guaranteed to be created.
        if start_maximized:
            hub_window.showMaximized()
        else:
            hub_window.show()
            hub_window.setGeometry(target_rect)
        
        # Start popups (Welcome, Daily Plan) only NOW that the Hub is visible
        hub_window.start_post_load_tasks()
        
        splash.close()

    def update_progress():
        nonlocal transition_started, hub_window
        elapsed_ms = (time.time() - start_time) * 1000
        
        if ai_loading_finished and elapsed_ms >= min_duration_ms and not transition_started:
            # AI is ready AND minimum duration has passed
            splash.set_progress(100)
            transition_started = True
            progress_timer.stop()
            
            # Create Hub Window NOW (so it's ready)
            hub_window = HubWindow(state, paths, ai_engine)
            
            # Start smooth transition
            splash.transition_to_main(target_rect, on_transition_done)
        else:
            # Keep filling progress bar linearly up to 90% over minimum duration
            progress = min(90, (elapsed_ms / min_duration_ms) * 100)
            splash.set_progress(int(progress))
    
    progress_timer.timeout.connect(update_progress)
    progress_timer.start(50)  # Update every 50ms for smooth animation
    
    # --- Load AI in background thread using QThread ---
    ai_thread = QThread()
    ai_loader = AILoader(state)
    ai_loader.moveToThread(ai_thread)

    def on_ai_ready(engine):
        nonlocal ai_engine, ai_loading_finished
        ai_engine = engine
        ai_loading_finished = True
        ai_thread.quit()

    def on_ai_error():
        nonlocal ai_loading_finished
        # AI failed, engine remains None
        ai_loading_finished = True
        ai_thread.quit()

    # Connect signals and slots
    ai_thread.started.connect(ai_loader.run)
    ai_loader.finished.connect(on_ai_ready)
    ai_loader.error.connect(on_ai_error)
    
    # Clean up thread and worker object
    ai_thread.finished.connect(ai_thread.deleteLater)
    ai_loader.finished.connect(ai_loader.deleteLater)
    ai_thread.start()
    
    # 6. Run
    sys.exit(app.exec())

if __name__ == "__main__":
    main()