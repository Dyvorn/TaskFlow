import sys
import random
import traceback
import os
from PyQt6.QtWidgets import QApplication, QPushButton, QLineEdit, QCheckBox, QComboBox, QAbstractButton, QListWidget, QMessageBox, QWidget
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtCore import qInstallMessageHandler, QtMsgType
from PyQt6.QtTest import QTest

# Capture stdout/stderr to detect non-fatal errors
class LogCapturer:
    def __init__(self, original_stream):
        self.original_stream = original_stream
        self.captured_logs = []

    def write(self, text):
        self.original_stream.write(text)
        if text.strip():
            self.captured_logs.append(text.strip())

    def flush(self):
        self.original_stream.flush()

stdout_capturer = LogCapturer(sys.stdout)
stderr_capturer = LogCapturer(sys.stderr)
sys.stdout = stdout_capturer
sys.stderr = stderr_capturer

# Capture Qt internal messages (Warnings, Criticals, etc.)
def qt_message_handler(mode, context, message):
    msg_type = "Qt Info"
    if mode == QtMsgType.QtInfoMsg: msg_type = "Qt Info"
    elif mode == QtMsgType.QtWarningMsg: msg_type = "Qt Warning"
    elif mode == QtMsgType.QtCriticalMsg: msg_type = "Qt Critical"
    elif mode == QtMsgType.QtFatalMsg: msg_type = "Qt Fatal"
    
    print(f"[{msg_type}] {message}")

qInstallMessageHandler(qt_message_handler)

# Override the exception handler to capture crashes
def monkey_exception_handler(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("CRASH DETECTED!")
    
    # Save to file
    with open("crash_report.txt", "w", encoding="utf-8") as f:
        f.write(error_msg)
        
    # Show GUI message
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle("Monkey Tester - Crash Detected")
    msg.setText("TaskFlow crashed during testing!")
    msg.setInformativeText("The error has been saved to 'crash_report.txt'.\n\nPlease copy the content of that file and send it to the developer.")
    msg.setDetailedText(error_msg)
    msg.exec()
    
    sys.exit(1)

sys.excepthook = monkey_exception_handler

class MonkeyTester:
    def __init__(self, window):
        self.window = window
        self.timer = QTimer()
        self.timer.timeout.connect(self.act)
        self.actions = 0
        self.max_actions = 300  # Number of random actions to perform

    def start(self):
        print(f"Starting Monkey Test ({self.max_actions} actions)...")
        self.timer.start(100)  # 100ms interval (fast but allows event processing)

    def act(self):
        self.actions += 1
        if self.actions > self.max_actions:
            self.timer.stop()
            print("Monkey test completed successfully!")
            
            # Check for non-fatal errors in logs
            keywords = ["error", "exception", "failed", "warning", "critical", "fatal"]
            issues = []
            for log in stdout_capturer.captured_logs + stderr_capturer.captured_logs:
                if any(k in log.lower() for k in keywords):
                    issues.append(log)

            msg = QMessageBox()
            if issues:
                msg.setIcon(QMessageBox.Icon.Warning)
                msg.setWindowTitle("Monkey Tester - Issues Found")
                msg.setText("Test completed, but potential issues were detected.")
                msg.setDetailedText("\n".join(issues))
            else:
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("Monkey Tester")
                msg.setText("No crashes or errors detected.")
                msg.setInformativeText("The application remained stable during the test.")
            msg.exec()
            
            self.window.close()
            return

        # Find all interactive widgets
        widgets = self.window.findChildren(QWidget)
        interactive = [
            w for w in widgets 
            if w.isVisible() and w.isEnabled() and 
            isinstance(w, (QPushButton, QLineEdit, QCheckBox, QComboBox, QListWidget))
        ]
        
        if not interactive:
            return

        w = random.choice(interactive)
        
        try:
            if isinstance(w, (QPushButton, QCheckBox, QAbstractButton)):
                QTest.mouseClick(w, Qt.MouseButton.LeftButton)
                
            elif isinstance(w, QLineEdit):
                # Randomly type or clear
                if random.random() > 0.5:
                    QTest.keyClicks(w, "test")
                else:
                    w.clear()
                QTest.keyClick(w, Qt.Key.Key_Enter)
                
            elif isinstance(w, QComboBox):
                count = w.count()
                if count > 0:
                    w.setCurrentIndex(random.randint(0, count - 1))
                    
            elif isinstance(w, QListWidget):
                count = w.count()
                if count > 0:
                    row = random.randint(0, count - 1)
                    rect = w.visualItemRect(w.item(row))
                    QTest.mouseClick(w.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
                    
        except Exception as e:
            # Ignore interaction errors (e.g. widget disappeared), but log them
            # to stderr for debugging the monkey itself.
            print(f"Monkey interaction failed on {w}: {e}", file=sys.stderr)
            pass

if __name__ == "__main__":
    # 1. Setup Application
    app = QApplication(sys.argv)
    app.setApplicationName("TaskFlowMonkey")

    # 2. Load State
    from core.model import get_data_paths, load_state, rollover_tasks, save_state
    paths = get_data_paths()
    state = load_state(paths)
    
    # 3. Daily Maintenance
    rollover_tasks(state)
    save_state(paths, state) # Save rollover before launching

    # 4. Import UI and AI
    from ai.engine import AIEngine
    from ui.hub import HubWindow

    # 5. Launch TaskFlow Hub (without splash for testing)
    print("Launching TaskFlow for Monkey Test...")
    # AI Engine can be mocked or loaded if needed. For a simple UI test, None is fine.
    ai_engine = None
    window = HubWindow(state, paths, ai_engine)
    window.show()
    
    # Allow window to fully load and run post-load tasks which might open dialogs
    QApplication.processEvents()
    window.start_post_load_tasks()
    
    # 6. Start Monkey
    monkey = MonkeyTester(window)

    def wait_for_app_ready():
        """
        Polls until the application has no active modal widgets (e.g., popups).
        This is more robust than a fixed delay.
        """
        modal_widget = QApplication.activeModalWidget()
        if modal_widget is not None:
            # App is still busy with a popup, wait and check again.
            QTimer.singleShot(500, wait_for_app_ready)
        else:
            # No modal widgets, safe to start the test.
            monkey.start()

    # Start polling after a short delay to allow initial popups to appear.
    QTimer.singleShot(1000, wait_for_app_ready)
    
    sys.exit(app.exec())
