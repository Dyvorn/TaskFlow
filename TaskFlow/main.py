import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Import the UI
from ui.hub import HubWindow, SplashWindow, SPLASH_DURATION_MS

# Import Data Model
from core.model import get_data_paths, load_state, save_state, rollover_tasks

# Import the AI Engine
from ai.engine import AIEngine

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
        show_hub.window = HubWindow(state, paths, ai_engine) # Pass engine to Hub
        
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