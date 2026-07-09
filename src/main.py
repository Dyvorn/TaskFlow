import sys
import os
from PyQt6.QtWidgets import QApplication

# Ensure the database is setup before launching UI
from core.database import setup_database
from ui.main_window import MainWindow

def main():
    """
    Entry point for the TaskFlow application.
    Initializes the database, loads the UI styles, and starts the PyQt event loop.
    """
    # 1. Initialize data layer
    setup_database()
    
    # 2. Setup Application
    app = QApplication(sys.argv)
    app.setApplicationName("TaskFlow")
    
    # Load stylesheet
    style_path = os.path.join(os.path.dirname(__file__), 'ui', 'styles', 'theme.qss')
    if os.path.exists(style_path):
        with open(style_path, 'r') as f:
            app.setStyleSheet(f.read())
    else:
        print(f"Warning: Stylesheet not found at {style_path}")

    # 3. Launch UI
    window = MainWindow()
    window.show()
    
    # 4. Run event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
