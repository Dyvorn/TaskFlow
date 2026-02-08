import sys
import os
import json
import shutil
import uuid
import traceback
import re
import subprocess
import tempfile
import random
import math
import socket
import ctypes
import calendar

# Global exception handler to catch startup crashes (defined early)
def global_exception_handler(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(f"CRITICAL ERROR:\n{error_msg}", file=sys.stderr)
    try:
        # Only attempt on Windows
        if os.name == 'nt':
            ctypes.windll.user32.MessageBoxW(0, f"Startup Error:\n{error_msg}", "TaskFlow Crash", 0x10)
    except:
        pass
sys.excepthook = global_exception_handler

try:
    import requests
except ImportError:
    requests = None

try:
    import keyboard
except ImportError:
    keyboard = None

try:
    import winreg
except ImportError:
    winreg = None

try:
    import winsound
except ImportError:
    winsound = None

from datetime import datetime, date, timedelta, time

from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    pyqtSignal, QThread, QRect, QPoint, QParallelAnimationGroup, pyqtProperty, QRectF, QPointF, QUrl,
    pyqtSlot, QSize, QEvent, QMimeData, QDir, 
)
from PyQt6.QtGui import (
    QFont, QCursor, QKeySequence, QShortcut, QColor, QDrag, QPixmap, QIcon, QDesktopServices,
    QPainter, QLinearGradient, QPainterPath, QPen, QRegion
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QScrollArea,
    QGraphicsDropShadowEffect, QMenu,
    QListWidget, QListWidgetItem, QStackedWidget, QTextEdit,
    QComboBox, QInputDialog, QSplitter, QMessageBox, QProgressBar,
    QDialog, QSystemTrayIcon, QProgressDialog, QSpinBox, QCheckBox,
    QGraphicsOpacityEffect, QCalendarWidget, QToolTip, QFileDialog
)
from PyQt6.QtWidgets import QTableView, QTimeEdit, QDialogButtonBox, QFormLayout
from PyQt6.QtCore import QMimeData, QEvent

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

APP_NAME = "TaskFlow"
APP_ID = "taskflow.ultimate.desktop"
VERSION = "6.0"
UPDATE_URL = "https://api.github.com/repos/Dyvorn/TaskFlow/releases/latest"

WHATS_NEW_HTML = (
    "<p>Welcome to TaskFlow 6.0!</p>"
    "<h2 style='color:#ffd700'>Welcome to TaskFlow 6.0</h2>"
    "<p>This is a complete overhaul focused on speed, stability, and intelligent features to keep you in a state of flow.</p>"
    "<h3>🚀 Major New Features</h3>"
    "<ul>"
    "<li><b>Major Update:</b> Welcome to the next generation of TaskFlow.</li>"
    "<li><b>Performance:</b> Optimized startup and interaction speeds.</li>"
    "<li><b>Refinements:</b> UI polish and under-the-hood improvements.</li>"
    "<li><b>Global Quick Capture:</b> Press <b>Alt+Space</b> from any application to instantly capture a task.</li>"
    "<li><b>Smart Parsing:</b> The input field now understands you. Try typing things like:"
    "<ul><li><i>'Design meeting on Friday at 4pm'</i></li><li><i>'Submit report tomorrow !important'</i></li><li><i>'Plan vacation +Personal'</i></li></ul>"
    "</li>"
    "<li><b>Zen Mode 2.0:</b> A beautiful, distraction-free timer to focus on a single task. Now with subtask support and sleep prevention.</li>"
    "<li><b>Local Cloud Sync:</b> Seamlessly sync tasks, notes, and projects between your devices on the same network.</li>"
    "<li><b>Project System:</b> Group related tasks and notes into color-coded projects for better organization.</li>"
    "<li><b>Calendar & Timeline:</b> A new tab with a daily timeline view. Drag-and-drop tasks to schedule them visually.</li>"
    "</ul>"
    "<p>Stay in the flow!</p>"
    "<h3>✨ Core Improvements</h3>"
    "<ul>"
    "<li><b>Performance:</b> The UI is faster and more responsive than ever.</li>"
    "<li><b>Data Safety:</b> Automatic backups are created during sync operations, and a new Backup Manager is in Settings.</li>"
    "<li><b>Intuitive UX:</b> Drag tasks onto tabs, paste text to create tasks, and enjoy a more polished, predictable workflow.</li>"
    "</ul>"
    "<p><i>Thank you for using TaskFlow. Stay focused, stay flowing.</i></p>"
)

if getattr(sys, "frozen", False):
    # Use AppData for installed version to ensure write permissions
    BASE_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
else:
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        BASE_DIR = os.getcwd()

if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR, exist_ok=True)

PATH_CONFIG = os.path.join(BASE_DIR, "path_config.json")

def get_data_dir():
    d = BASE_DIR
    if os.path.exists(PATH_CONFIG):
        try:
            with open(PATH_CONFIG, "r") as f:
                cfg = json.load(f)
                candidate = cfg.get("data_dir")
                if candidate and os.path.exists(candidate):
                    d = candidate
        except: pass
    return d

DATA_DIR = get_data_dir()
DATA_FILE = os.path.join(DATA_DIR, "taskflow_data.json")
BACKUP_FILE = os.path.join(DATA_DIR, "taskflow_data.backup.json")

SYNC_PORT = 54546
# Window geometry (includes shadow margin)
WIN_W = 360
WIN_H = 650
MARGIN = 10
COLLAPSED_WIDTH = 60
PILL_HEIGHT = 60

# Styling
DARK_BG = "#B3121212" # Refined opacity for better glass effect
CARD_BG = "#991E1E1E"
HOVER_BG = "#33FFFFFF"
TEXT_WHITE = "#e0e0e0"
TEXT_GRAY = "#cccccc" # Improved contrast for accessibility
GOLD = "#ffd700"
PROJECT_COLORS = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEEAD", "#D4A5A5", "#9B59B6", "#3498DB"]

AUTO_COLLAPSE_DELAY_MS = 1200
SAVE_DEBOUNCE_MS = 320

SECTIONS = ["Today", "Tomorrow", "This Week", "Someday"]
RECUR_OPTIONS = ["None", "Daily", "Weekly", "Monthly"]

MOTIVATIONAL_QUOTES = [
    "Small steps lead to big changes.",
    "Progress over perfection.",
    "You are doing enough.",
    "One thing at a time.",
    "Be proud of the effort you put in.",
    "Rest is also part of the work.",
    "You got this!",
    "Focus on the present moment.",
    "Your well-being comes first.",
    "Every checkmark is a victory.",
    "The secret of getting ahead is getting started."
]

def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _today_str():
    return str(date.today())

# --- Glassmorphism / Acrylic Effect ---
class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),
        ("AccentFlags", ctypes.c_uint),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_int)
    ]

class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.POINTER(ACCENT_POLICY)),
        ("SizeOfData", ctypes.c_size_t)
    ]

def apply_glass_effect(hwnd):
    if os.name != "nt": return
    try:
        policy = ACCENT_POLICY()
        policy.AccentState = 4 # ACCENT_ENABLE_ACRYLICBLURBEHIND
        policy.AccentFlags = 2
        policy.GradientColor = 0x99121212 # AABBGGRR
        policy.AnimationId = 0
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19 # WCA_ACCENT_POLICY
        data.Data = ctypes.pointer(policy)
        data.SizeOfData = ctypes.sizeof(policy)
        ctypes.windll.user32.SetWindowCompositionAttribute(int(hwnd), ctypes.byref(data))
    except Exception: pass

def _atomic_write_json(path: str, backup_path: str, data: dict):
    tmp = path + ".tmp"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        if os.path.exists(path):
            try:
                shutil.copy2(path, backup_path)
            except Exception:
                pass
        os.replace(tmp, path)
    except Exception as e:
        print(f"Error saving state: {e}", file=sys.stderr)


def load_state() -> dict:
    default = {
        "schema": 1,
        "last_version": "0.0",
        "last_opened": _today_str(),
        "tasks": [],
        "notes": {"groups": {"General": []}, "order": ["General"]},
        "sections": SECTIONS.copy(),
        "ui": {"collapsed": False, "active_tab": "Tasks", "section_states": {}},
        "config": {"zen_duration": 25, "auto_collapse": True, "window_snapping": True, "expand_on_hover": True, "compact_mode": False, "sound_enabled": True},
        "stats": {"current_streak": 0, "last_activity_date": None},
        "projects": [],
        "sync_devices": [],
        "zen_stats": {"total_minutes": 0, "sessions": []},
    }

    def _read(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    data = None
    if os.path.exists(DATA_FILE):
        try:
            data = _read(DATA_FILE)
        except (json.JSONDecodeError, OSError, ValueError):
            data = None

    if data is None and os.path.exists(BACKUP_FILE):
        try:
            data = _read(BACKUP_FILE)
            # STABILITY FIX: If we successfully recovered from backup,
            # restore the main file immediately. This prevents the next save
            # from backing up the corrupt/missing main file over our good backup.
            if data:
                try:
                    shutil.copy2(BACKUP_FILE, DATA_FILE)
                except Exception: pass
        except Exception:
            data = None

    if data is None:
        return default

    data.setdefault("tasks", [])
    data.setdefault("notes", default["notes"])
    data.setdefault("ui", default["ui"])
    data.setdefault("last_version", "0.0")
    data.setdefault("last_opened", _today_str())
    data.setdefault("sections", default["sections"])
    data.setdefault("config", default["config"])
    data.setdefault("stats", default["stats"])
    data["config"].setdefault("expand_on_hover", True)
    data["config"].setdefault("compact_mode", False)
    data["config"].setdefault("sound_enabled", True)
    data.setdefault("sync_devices", [])
    data.setdefault("projects", [])
    data.setdefault("sync_history", [])
    data.setdefault("zen_stats", default["zen_stats"])
    data.setdefault("last_weekly_review", None)
    data.setdefault("habits", [])
    
    # Migration for v6.0 streak system
    if "current_streak" not in data["stats"]:
        data["stats"].update({"current_streak": 0, "last_activity_date": None})

    # XP & Leveling System
    data["stats"].setdefault("xp", 0)
    data["stats"].setdefault("level", 1)

    data["notes"].setdefault("groups", {"General": []})
    data["notes"].setdefault("order", list(data["notes"]["groups"].keys()) or ["General"])

    fixed = []
    for t in data["tasks"]:
        if not isinstance(t, dict):
            continue
        t.setdefault("id", str(uuid.uuid4()))
        t.setdefault("text", "")
        t.setdefault("emoji", "📝")
        t.setdefault("completed", False)
        t.setdefault("section", "Today")
        if t["section"] not in data["sections"]:
            t["section"] = "Today"
        t.setdefault("order", 0)
        t.setdefault("note", "")
        t.setdefault("recur", "")
        t.setdefault("parent_id", None)
        t.setdefault("linked_note_id", None)
        t.setdefault("created_at", _now_iso())
        t.setdefault("updated_at", _now_iso())
        t.setdefault("due_date", None) # YYYY-MM-DD
        t.setdefault("due_time", None) # HH:MM
        t.setdefault("estimated_duration", None) # minutes
        t.setdefault("started_at", None) # ISO datetime
        t.setdefault("reminder_sent", False)
        t.setdefault("project_id", None)
        fixed.append(t)
    data["tasks"] = fixed

    for gname, notes in list(data["notes"]["groups"].items()):
        if not isinstance(notes, list):
            data["notes"]["groups"][gname] = []
            continue
        new_notes = []
        for n in notes:
            if not isinstance(n, dict):
                continue
            n.setdefault("id", str(uuid.uuid4()))
            n.setdefault("title", "")
            n.setdefault("content", "")
            n.setdefault("created_at", _now_iso())
            n.setdefault("updated_at", _now_iso())
            n.setdefault("project_id", None)
            new_notes.append(n)
        data["notes"]["groups"][gname] = new_notes

    if not data["notes"]["groups"]:
        data["notes"]["groups"] = {"General": []}
    if not data["notes"]["order"]:
        data["notes"]["order"] = list(data["notes"]["groups"].keys())

    # Deduplicate sections just in case
    seen = set()
    unique_sections = []
    for s in data["sections"]:
        if s not in seen:
            unique_sections.append(s)
            seen.add(s)
    
    # Ensure "Scheduled" exists and is at the bottom (User Request)
    if "Scheduled" in unique_sections:
        unique_sections.remove("Scheduled")
    unique_sections.append("Scheduled")

    data["sections"] = unique_sections

    # Cleanup orphaned subtasks (tasks referring to non-existent parents)
    all_ids = set(t["id"] for t in data["tasks"])
    data["tasks"] = [t for t in data["tasks"] if not t.get("parent_id") or t.get("parent_id") in all_ids]

    return data


def save_state(state: dict):
    _atomic_write_json(DATA_FILE, BACKUP_FILE, state)


class SyncListener(QThread):
    data_received = pyqtSignal(dict, str)

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(('', SYNC_PORT))
            server.listen(5)
            server.settimeout(1.0)
            while not self.isInterruptionRequested():
                try:
                    client, addr = server.accept()
                    # Simple protocol: 4-byte length header + JSON body
                    header = client.recv(4)
                    if not header:
                        client.close()
                        continue
                    length = int.from_bytes(header, 'big')
                    
                    chunks = []
                    bytes_recd = 0
                    while bytes_recd < length:
                        chunk = client.recv(min(length - bytes_recd, 4096))
                        if not chunk: break
                        chunks.append(chunk)
                        bytes_recd += len(chunk)
                    
                    data = b''.join(chunks)
                    if data:
                        obj = json.loads(data.decode('utf-8'))
                        self.data_received.emit(obj, addr[0])
                    client.close()
                except socket.timeout:
                    continue
                except Exception:
                    pass
        except Exception as e:
            print(f"Sync listener bind failed: {e}")


class SyncSender(QThread):
    def __init__(self, target_ip, data):
        super().__init__()
        self.target_ip = target_ip
        self.data = data

    def run(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3) # Short timeout to not hang background threads too long
            s.connect((self.target_ip, SYNC_PORT))
            payload = json.dumps(self.data).encode('utf-8')
            length = len(payload).to_bytes(4, 'big')
            s.sendall(length + payload)
            s.close()
        except:
            pass # Device offline, ignore

class UpdateCheckThread(QThread):
    finished = pyqtSignal(dict)

    def run(self):
        if not requests:
            self.finished.emit({"error": "The 'requests' library is not installed.\nPlease run: pip install requests"})
            return

        try:
            headers = {"User-Agent": "TaskFlow-Desktop"}
            res = requests.get(UPDATE_URL, headers=headers, timeout=10)
            res.raise_for_status()
            data = res.json()
            
            # Parse GitHub API response
            tag = data.get("tag_name", "")
            # FIX: Robust version extraction to handle "v6.0-beta", etc.
            match = re.search(r"(\d+(\.\d+)*)", tag) # Extracts "6", "6.0", "6.0.1"
            if match:
                clean_version = match.group(1)
            else:
                clean_version = tag.strip().lstrip("vV")

            # Check if it is a pre-release (not production ready)
            is_prerelease = data.get("prerelease", False)

            assets = data.get("assets", [])
            download_url = ""
            for asset in assets:
                asset_name = asset.get("name", "").lower()
                # Strict check: Must be an executable and contain "setup" to avoid zips/raw exes
                if "setup" in asset_name and asset_name.endswith(".exe"):
                    download_url = asset.get("browser_download_url")
                    break
            
            self.finished.emit({
                "latest_version": clean_version, 
                "download_url": download_url,
                "is_prerelease": is_prerelease
            })
            
        except Exception as e:
            self.finished.emit({"error": f"Could not connect to the update server:\n{str(e)}"})


class UpdateDownloadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path

    def run(self):
        if not requests:
            self.error.emit("The 'requests' library is not installed.")
            return
        try:
            headers = {"User-Agent": "TaskFlow-Desktop"}
            response = requests.get(self.url, stream=True, timeout=30, headers=headers)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(self.save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            self.progress.emit(int(downloaded * 100 / total_size))
            self.finished.emit(self.save_path)
        except Exception as e:
            self.error.emit(str(e))


class OverlayDialog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        # Dim background
        self.setStyleSheet("background-color: rgba(0, 0, 0, 160);")

        # Opacity Effect for Fade In
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        # Content Container (Centered)
        self.content = QFrame(self)
        self.content.setFixedWidth(360)
        # Height is dynamic based on content
        self.content.setStyleSheet(f"background:{CARD_BG};border:1px solid {HOVER_BG};border-radius:16px;")
        
        # Shadow for content
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 10)
        self.content.setGraphicsEffect(shadow)
        
        lay = QVBoxLayout(self.content)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)
        
        self.lbl_title = QLabel("Title")
        self.lbl_title.setStyleSheet(f"color:{GOLD};font-size:18px;font-weight:bold;background:transparent;border:none;")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.lbl_title)
        
        self.body_layout = QVBoxLayout()
        lay.addLayout(self.body_layout)

        self.lbl_msg = QLabel("Message")
        self.lbl_msg.setWordWrap(True)
        self.lbl_msg.setStyleSheet(f"color:{TEXT_WHITE};font-size:14px;background:transparent;border:none;")
        self.lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body_layout.addWidget(self.lbl_msg)
        
        self.custom_widget = None
        
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addLayout(self.btn_layout)

    def show_msg(self, title, msg, buttons, content_widget=None):
        self.lbl_title.setText(title)
        
        # Handle Body
        if self.custom_widget:
            self.custom_widget.deleteLater()
            self.custom_widget = None
            
        if content_widget:
            self.lbl_msg.setVisible(False)
            self.custom_widget = content_widget
            self.body_layout.addWidget(content_widget)
            content_widget.show()
        else:
            self.lbl_msg.setVisible(True)
            self.lbl_msg.setText(msg)
        
        # Clear old buttons
        while self.btn_layout.count():
            item = self.btn_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add new buttons: buttons = [("Text", callback, "primary"|"secondary")]
        for text, cb, style_type in buttons:
            btn = QPushButton(text)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            if style_type == "primary":
                btn.setStyleSheet(f"background:{GOLD};color:{DARK_BG};border-radius:8px;padding:8px 16px;font-weight:bold;border:none;")
            else:
                btn.setStyleSheet(f"background:{HOVER_BG};color:{TEXT_WHITE};border-radius:8px;padding:8px 16px;border:none;")
            
            btn.clicked.connect(lambda checked, c=cb: self._handle_click(c))
            self.btn_layout.addWidget(btn)
            
        # Ensure overlay covers the container before calculating positions
        self.content.adjustSize()
        if self.parentWidget():
            self.resize(self.parentWidget().size())

        if hasattr(self, "anim_group") and self.anim_group.state() == QParallelAnimationGroup.State.Running:
            self.anim_group.stop()

        self.opacity_effect.setOpacity(0)
        self.setVisible(True)
        self.raise_()
        self._center_content()
        
        # Slide + Fade Animation
        final_pos = self.content.pos()
        start_pos = final_pos + QPoint(0, 8)
        self.content.move(start_pos)
        
        self.anim_group = QParallelAnimationGroup(self)
        
        anim_fade = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        anim_fade.setStartValue(0.0)
        anim_fade.setEndValue(1.0)
        anim_fade.setDuration(200)
        anim_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        anim_slide = QPropertyAnimation(self.content, b"pos", self)
        anim_slide.setStartValue(start_pos)
        anim_slide.setEndValue(final_pos)
        anim_slide.setDuration(200)
        anim_slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.anim_group.addAnimation(anim_fade)
        self.anim_group.addAnimation(anim_slide)
        self.anim_group.start()

    def _handle_click(self, callback):
        self.setVisible(False)
        if callback:
            callback()

    def resizeEvent(self, event):
        if hasattr(self, "anim_group") and self.anim_group.state() == QParallelAnimationGroup.State.Running:
            self.anim_group.stop()
            self.opacity_effect.setOpacity(1.0)
        self._center_content()
        super().resizeEvent(event)
        
    def _center_content(self):
        if self.content:
            x = (self.width() - self.content.width()) // 2
            y = (self.height() - self.content.height()) // 2
            self.content.move(x, y)

class SnapGlow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.sides = set()
        self._opacity = 0.0
        
        self.anim = QPropertyAnimation(self, b"opacity_prop")
        self.anim.setDuration(600)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)

    def set_opacity(self, val):
        self._opacity = val
        self.update()

    def get_opacity(self):
        return self._opacity

    opacity_prop = pyqtProperty(float, get_opacity, set_opacity)

    def flash(self, sides):
        self.sides = sides
        self.anim.stop()
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.start()

    def paintEvent(self, event):
        if self._opacity <= 0:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self._opacity)
        
        # Clip to rounded corners of the container
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 16, 16)
        painter.setClipPath(path)
        
        rect = self.rect()
        color = QColor(GOLD)
        
        def draw_gradient(x1, y1, x2, y2, r):
            grad = QLinearGradient(x1, y1, x2, y2)
            grad.setColorAt(0, color)
            grad.setColorAt(1, Qt.GlobalColor.transparent)
            painter.fillRect(r, grad)

        if "left" in self.sides:
            draw_gradient(rect.left(), 0, rect.left() + 40, 0, rect)
            
        if "right" in self.sides:
            draw_gradient(rect.right(), 0, rect.right() - 40, 0, rect)
            
        if "top" in self.sides:
            draw_gradient(0, rect.top(), 0, rect.top() + 40, rect)
            
        if "bottom" in self.sides:
            draw_gradient(0, rect.bottom(), 0, rect.bottom() - 40, rect)


class SmoothProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._anim = QPropertyAnimation(self, b"value")
        self._anim.setDuration(400)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def setInitialValue(self, val):
        super().setValue(val)

    def setValueSmooth(self, val):
        if self.value() == val: return
        self._anim.stop()
        self._anim.setStartValue(self.value())
        self._anim.setEndValue(val)
        self._anim.start()


class AnimatedCheckbox(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._checked = False
        self._scale = 1.0
        
        self._anim = QPropertyAnimation(self, b"scale_prop")
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)

    def get_scale(self): return self._scale
    def set_scale(self, s): 
        self._scale = s
        self.update()
    scale_prop = pyqtProperty(float, get_scale, set_scale)

    def setChecked(self, checked):
        self._checked = checked
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._anim.stop()
            self._anim.setStartValue(0.8)
            self._anim.setEndValue(1.0)
            self._anim.start()
            self.clicked.emit()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        center = rect.center()
        
        painter.translate(center)
        painter.scale(self._scale, self._scale)
        painter.translate(-center)
        
        radius = 10
        if self._checked:
            painter.setBrush(QColor(GOLD))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, radius, radius)
            
            painter.setPen(QPen(QColor(DARK_BG), 2))
            font = painter.font()
            font.setBold(True)
            font.setPixelSize(14)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "✓")
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(GOLD), 2))
            painter.drawEllipse(center, radius, radius)


class ConfettiOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.particles = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update)

    def burst(self):
        self.particles.clear()
        cx = self.width() / 2
        cy = self.height() / 2
        for _ in range(60):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 9)
            self.particles.append({
                "x": cx, "y": cy,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed - 4, # Upward bias
                "color": QColor.fromHsv(random.randint(0, 359), 200, 255),
                "size": random.randint(4, 8),
                "decay": random.uniform(0.94, 0.98)
            })
        self.timer.start(16)

    def _update(self):
        if not self.particles:
            self.timer.stop()
            return
        
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.25 # Gravity
            p["vx"] *= p["decay"] # Air resistance
            
        self.particles = [p for p in self.particles if p["y"] < self.height() + 10]
        self.update()

    def paintEvent(self, event):
        if not self.particles:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for p in self.particles:
            painter.setBrush(p["color"])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(p["x"], p["y"]), p["size"]/2, p["size"]/2)


class QuickCaptureDialog(QDialog):
    submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(600, 70)

        self.container = QFrame(self)
        self.container.setGeometry(0, 0, 600, 70)
        self.container.setStyleSheet(
            f"background:{DARK_BG};border:1px solid {GOLD};border-radius:12px;"
        )
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

        self.input = QLineEdit(self.container)
        self.input.setGeometry(20, 10, 560, 50)
        self.input.setPlaceholderText("Quick Capture...")
        self.input.setStyleSheet(
            f"background:transparent;border:none;color:{TEXT_WHITE};font-size:18px;"
        )
        self.input.returnPressed.connect(self._submit)
        
    def _submit(self):
        text = self.input.text().strip()
        if text:
            self.submitted.emit(text)
        self.hide()
        self.input.clear()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.input.clear()
        else:
            super().keyPressEvent(event)

    def show_centered(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 3
        self.move(screen.x() + x, screen.y() + y)
        self.show()
        self.activateWindow()
        self.input.setFocus()


class PlanTaskDialog(QDialog):
    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plan Task")
        self.setFixedSize(300, 200)
        self.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};")
        
        layout = QFormLayout(self)
        
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        
        try:
            if task.get("due_time"):
                self.time_edit.setTime(datetime.strptime(task["due_time"], "%H:%M").time())
            else:
                raise ValueError("No time set")
        except ValueError:
            self.time_edit.setTime(datetime.now().time())
        
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(0, 480)
        self.duration_spin.setSuffix(" min")
        self.duration_spin.setValue(task.get("estimated_duration") or 0)
        
        layout.addRow("Start Time:", self.time_edit)
        layout.addRow("Duration:", self.duration_spin)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_data(self):
        return self.time_edit.time().toString("HH:mm"), self.duration_spin.value()


class TimelineTaskWidget(QFrame):
    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        
        # Color coding based on priority/emoji
        border_color = GOLD
        bg_color = CARD_BG
        emoji = task.get("emoji", "")
        if "🔥" in emoji or "important" in task.get("text", "").lower():
            border_color = "#ff4d4d" # Red
            bg_color = "#2a1a1a"
        elif "⭐" in emoji:
            border_color = "#aaff00" # Green
            bg_color = "#1a2a1a"
            
        self.setStyleSheet(f"background:{bg_color};border:1px solid {border_color};border-radius:4px;")
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(0)
        
        lbl = QLabel(task.get("text", ""))
        lbl.setStyleSheet(f"color:{TEXT_WHITE};font-size:11px;border:none;background:transparent;")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        
        # Resize handle area (bottom)
        self.resize_area_height = 10

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if e.pos().y() > self.height() - self.resize_area_height:
                self.parent().start_resize(self, e)
            else:
                self.parent().start_drag(self, e)
        super().mousePressEvent(e)

    def enterEvent(self, e):
        self.setStyleSheet(f"background:{HOVER_BG};border:1px solid {GOLD};border-radius:4px;")
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.setStyleSheet(f"background:{CARD_BG};border:1px solid {GOLD};border-radius:4px;")
        super().leaveEvent(e)

    def mouseMoveEvent(self, e):
        if e.pos().y() > self.height() - self.resize_area_height:
            self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        super().mouseMoveEvent(e)


class DayTimelineWidget(QWidget):
    taskChanged = pyqtSignal(str) # task_id

    def __init__(self, state_ref, parent=None):
        super().__init__(parent)
        self.state_ref = state_ref
        self.hour_height = 60
        self.setMinimumHeight(24 * self.hour_height)
        self.setAcceptDrops(True)
        self.current_date_str = _today_str()
        
        # Current time line timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(60000) # Update every minute
        
        # Scroll to now logic
        self._first_show = True

        self._dragging_task = None
        self._resizing_task = None
        self._drag_start_y = 0
        self._initial_geo = None

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setPen(QPen(QColor(HOVER_BG), 1))
        painter.setFont(QFont("Segoe UI", 8))
        
        for h in range(24):
            y = h * self.hour_height
            painter.drawLine(50, y, self.width(), y)
            painter.setPen(QColor(TEXT_GRAY))
            painter.drawText(5, y + 12, f"{h:02}:00")
            painter.setPen(QColor(HOVER_BG))
            
        # Draw Current Time Line
        if self.current_date_str == _today_str():
            now = datetime.now()
            total_mins = now.hour * 60 + now.minute
            y = int((total_mins / 60) * self.hour_height)
            
            painter.setPen(QPen(QColor("#ff4d4d"), 2))
            painter.drawLine(40, y, self.width(), y)
            
            # Draw indicator circle
            painter.setBrush(QColor("#ff4d4d"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(45, y), 4, 4)

    def showEvent(self, event):
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            # Delay slightly to allow layout to settle
            QTimer.singleShot(100, self.scroll_to_now)

    def scroll_to_now(self):
        now = datetime.now()
        total_mins = now.hour * 60 + now.minute
        y = int((total_mins / 60) * self.hour_height)
        
        # Center the view on current time
        scroll_area = self.parent().parent() # Viewport -> ScrollArea
        if isinstance(scroll_area, QScrollArea):
            target = max(0, y - scroll_area.height() // 2)
            scroll_area.verticalScrollBar().setValue(target)

    def refresh_tasks(self, date_str):
        self.current_date_str = date_str
        # Clear existing
        for c in self.children():
            if isinstance(c, TimelineTaskWidget):
                c.deleteLater()
        
        tasks = [t for t in self.state_ref["tasks"] if t.get("due_date") == date_str and not t.get("completed")]
        for t in tasks:
            if not t.get("due_time"): continue
            try:
                dt = datetime.strptime(t["due_time"], "%H:%M")
                minutes = dt.hour * 60 + dt.minute
                duration = t.get("estimated_duration", 30) or 30
                
                y = int((minutes / 60) * self.hour_height)
                h = int((duration / 60) * self.hour_height)
                
                w = TimelineTaskWidget(t, self)
                w.move(60, y)
                w.resize(self.width() - 70, max(20, h))
                w.show()
            except: pass

    def start_drag(self, widget, event):
        self._dragging_task = widget
        self._drag_start_y = event.globalPosition().y()
        self._initial_geo = widget.geometry()

    def start_resize(self, widget, event):
        self._resizing_task = widget
        self._drag_start_y = event.globalPosition().y()
        self._initial_geo = widget.geometry()

    def mouseMoveEvent(self, e):
        if self._dragging_task:
            dy = e.globalPosition().y() - self._drag_start_y
            new_y = max(0, min(self.height() - self._dragging_task.height(), self._initial_geo.y() + dy))
            self._dragging_task.move(self._initial_geo.x(), int(new_y))
            
        elif self._resizing_task:
            dy = e.globalPosition().y() - self._drag_start_y
            new_h = max(20, self._initial_geo.height() + dy)
            self._resizing_task.resize(self._initial_geo.width(), int(new_h))

    def mouseReleaseEvent(self, e):
        if self._dragging_task:
            # Snap to 15 mins
            y = self._dragging_task.y()
            total_mins = (y / self.hour_height) * 60
            snapped_mins = round(total_mins / 15) * 15
            snapped_mins = max(0, min(1439, snapped_mins)) # Clamp to 23:59
            
            h = snapped_mins // 60
            m = snapped_mins % 60
            time_str = f"{int(h):02}:{int(m):02}"
            
            self._dragging_task.task["due_time"] = time_str
            self.taskChanged.emit(self._dragging_task.task["id"])
            self._dragging_task = None
            self.refresh_tasks(self._dragging_task.task["due_date"] if self._dragging_task else _today_str()) # Refresh to snap visually
            
        elif self._resizing_task:
            h_px = self._resizing_task.height()
            mins = (h_px / self.hour_height) * 60
            snapped_mins = max(15, round(mins / 15) * 15)
            
            self._resizing_task.task["estimated_duration"] = int(snapped_mins)
            self.taskChanged.emit(self._resizing_task.task["id"])
            self._resizing_task = None

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat("application/taskflow-task"): e.accept()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat("application/taskflow-task"): e.accept()

    def dropEvent(self, e):
        if e.mimeData().hasFormat("application/taskflow-task"):
            task_id = e.mimeData().text()
            # Calculate time from drop position
            y = e.position().y()
            total_mins = (y / self.hour_height) * 60
            snapped_mins = round(total_mins / 15) * 15
            snapped_mins = max(0, min(1439, snapped_mins))
            
            h = int(snapped_mins // 60)
            m = int(snapped_mins % 60)
            time_str = f"{h:02}:{m:02}"
            
            t = next((x for x in self.state_ref["tasks"] if x["id"] == task_id), None)
            if t:
                t["due_time"] = time_str
                t["due_date"] = self.current_date_str
                t["section"] = "Scheduled"
                t["updated_at"] = _now_iso()
                self.taskChanged.emit(task_id)
                
            e.accept()
        else:
            super().dropEvent(e)

class TaskListWidget(QListWidget):
    taskMoved = pyqtSignal(str, str, int)
    heightChanged = pyqtSignal()

    def __init__(self, section_name: str, parent=None):
        super().__init__(parent)
        self.section_name = section_name
        self.real_height = 25
        self.setAcceptDrops(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropMode(QListWidget.DragDropMode.DropOnly)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSpacing(2)
        self.setStyleSheet(
            f"QListWidget{{background:transparent;border:1px solid transparent;border-radius:8px;}}"
            f"QListWidget:focus{{border:1px solid {GOLD};}}"
            f"QListWidget::item{{background:transparent;border:none;padding:4px;}}"
            f"QListWidget::item:selected{{background:{HOVER_BG};border-radius:8px;}}"
        )

    def update_height(self):
        h = 0
        for i in range(self.count()):
            if not self.item(i).isHidden():
                h += self.sizeHintForRow(i)
        self.real_height = max(h, 25)
        self.setFixedHeight(self.real_height)
        self.heightChanged.emit()

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat("application/taskflow-task"):
            e.accept()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat("application/taskflow-task"):
            e.setDropAction(Qt.DropAction.MoveAction)
            e.accept()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):
        if e.mimeData().hasFormat("application/taskflow-task"):
            task_id = e.mimeData().text()
            idx = self.indexAt(e.position().toPoint()).row()
            if idx == -1:
                idx = self.count()
            self.taskMoved.emit(task_id, self.section_name, idx)
            e.accept()
        elif e.mimeData().hasUrls():
            # Handle file drop -> Create task in this section
            mw = self.window()
            if isinstance(mw, QMainWindow) and hasattr(mw, "_create_task"):
                for url in e.mimeData().urls():
                    path = url.toLocalFile()
                    if path:
                        filename = os.path.basename(path)
                        mw._create_task(f"Review {filename}", self.section_name, "📁", note=path)
                mw._schedule_save()
                mw._refresh_tasks_ui()
                e.accept()
        else:
            super().dropEvent(e)


class SubtaskWidget(QFrame):
    toggled = pyqtSignal(str)
    editRequested = pyqtSignal(str)

    def __init__(self, st: dict, parent=None):
        super().__init__(parent)
        self.st = st
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(8)

        icon = "✓" if st.get("completed") else "○"
        color = GOLD if st.get("completed") else TEXT_GRAY
        self.chk = QLabel(icon)
        self.chk.setStyleSheet(f"color:{color};font-weight:bold;")

        text_style = f"color:{TEXT_GRAY if st.get('completed') else TEXT_WHITE};"
        if st.get("completed"):
            text_style += "text-decoration:line-through;"
        
        self.lbl = QLabel(st.get("text", ""))
        self.lbl.setStyleSheet(text_style)

        lay.addWidget(self.chk)
        lay.addWidget(self.lbl, 1)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.toggled.emit(self.st["id"])
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.editRequested.emit(self.st["id"])
            e.accept()
        else:
            super().mouseDoubleClickEvent(e)

class ProjectListItem(QWidget):
    def __init__(self, project, tasks, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)
        
        top = QHBoxLayout()
        top.setSpacing(8)
        lbl_dot = QLabel("●")
        lbl_dot.setStyleSheet(f"color:{project['color']};font-size:14px;")
        lbl_name = QLabel(project['name'])
        lbl_name.setStyleSheet(f"color:{TEXT_WHITE};font-size:15px;font-weight:bold;")
        
        top.addWidget(lbl_dot)
        top.addWidget(lbl_name)
        top.addStretch()
        
        # Stats
        p_tasks = [t for t in tasks if t.get("project_id") == project["id"] and not t.get("completed")]
        all_p_tasks = [t for t in tasks if t.get("project_id") == project["id"]]
        total = len(all_p_tasks)
        completed = len([t for t in all_p_tasks if t.get("completed")])
        
        if total > 0:
            lbl_stat = QLabel(f"{completed}/{total}")
            lbl_stat.setStyleSheet(f"color:{TEXT_GRAY};font-size:11px;")
            top.addWidget(lbl_stat)
            lay.addLayout(top)
            
            prog = QProgressBar()
            prog.setFixedHeight(4)
            prog.setTextVisible(False)
            prog.setRange(0, total)
            prog.setValue(completed)
            prog.setStyleSheet(f"QProgressBar{{border:none;background:{HOVER_BG};border-radius:2px;}} QProgressBar::chunk{{background:{project['color']};border-radius:2px;}}")
            lay.addWidget(prog)
        else:
            lay.addLayout(top)

class HabitManagerDialog(QDialog):
    def __init__(self, state_ref, parent=None):
        super().__init__(parent)
        self.state_ref = state_ref
        self.setWindowTitle("Manage Habits")
        self.setFixedSize(400, 500)
        self.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};")
        
        lay = QVBoxLayout(self)
        
        lbl = QLabel("Your Habits")
        lbl.setStyleSheet(f"color:{GOLD};font-size:16px;font-weight:bold;")
        lay.addWidget(lbl)
        
        self.list = QListWidget()
        self.list.setStyleSheet(f"background:{DARK_BG};border:1px solid {HOVER_BG};border-radius:8px;padding:5px;")
        lay.addWidget(self.list)
        
        h_lay = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("New habit...")
        self.input.setStyleSheet(f"background:{DARK_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};border-radius:6px;padding:6px;")
        
        btn_add = QPushButton("+")
        btn_add.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_add.clicked.connect(self._add)
        btn_add.setStyleSheet(f"background:{GOLD};color:{DARK_BG};border-radius:6px;padding:6px;font-weight:bold;")
        btn_add.setToolTip("Add Habit")
        
        h_lay.addWidget(self.input)
        h_lay.addWidget(btn_add)
        lay.addLayout(h_lay)
        
        btn_del = QPushButton("Delete Selected")
        btn_del.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_del.clicked.connect(self._delete)
        btn_del.setStyleSheet(f"background:{HOVER_BG};color:{TEXT_WHITE};border-radius:6px;padding:8px;")
        lay.addWidget(btn_del)
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet(f"background:{HOVER_BG};color:{TEXT_WHITE};border-radius:6px;padding:8px;")
        lay.addWidget(btn_close)
        
        self._refresh()

    def _refresh(self):
        self.list.clear()
        for h in self.state_ref.get("habits", []):
            item = QListWidgetItem(h["name"])
            item.setData(Qt.ItemDataRole.UserRole, h["id"])
            self.list.addItem(item)

    def _add(self):
        text = self.input.text().strip()
        if text:
            self.state_ref.setdefault("habits", []).append({
                "id": str(uuid.uuid4()),
                "name": text,
                "history": []
            })
            self.input.clear()
            self._refresh()

    def _delete(self):
        row = self.list.currentRow()
        if row >= 0:
            del self.state_ref["habits"][row]
            self._refresh()

class DailyBriefingWidget(QWidget):
    def __init__(self, state_ref, msg, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(10)
        
        lbl = QLabel(msg)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color:{TEXT_WHITE};font-size:14px;background:transparent;border:none;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)
        
        habits = state_ref.get("habits", [])
        if habits:
            line = QFrame()
            line.setFixedHeight(1)
            line.setStyleSheet(f"background:{HOVER_BG};")
            lay.addWidget(line)

            h_lbl = QLabel("Habit Tracker")
            h_lbl.setStyleSheet(f"color:{GOLD};font-size:14px;font-weight:bold;")
            h_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(h_lbl)
            
            today = _today_str()
            
            for h in habits:
                chk = QCheckBox(h["name"])
                chk.setStyleSheet(f"QCheckBox{{color:{TEXT_GRAY};}} QCheckBox::indicator{{border:1px solid {TEXT_GRAY};width:14px;height:14px;border-radius:3px;}} QCheckBox::indicator:checked{{background:{GOLD};border:1px solid {GOLD};}}")
                chk.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                if today in h.get("history", []):
                    chk.setChecked(True)
                
                chk.toggled.connect(lambda c, habit=h: self._toggle_habit(habit, c))
                lay.addWidget(chk)
                
    def _toggle_habit(self, habit, checked):
        today = _today_str()
        if "history" not in habit: habit["history"] = []
        
        if checked:
            if today not in habit["history"]:
                habit["history"].append(today)
        else:
            if today in habit["history"]:
                habit["history"].remove(today)

class TaskRow(QFrame):
    toggled = pyqtSignal(str)
    subtaskToggled = pyqtSignal(str)
    subtaskEdited = pyqtSignal(str, str) # parent_id, subtask_id
    resized = pyqtSignal()
    addStepRequested = pyqtSignal(str)
    focusRequested = pyqtSignal(str)
    menuRequested = pyqtSignal(QPoint)
    projectClicked = pyqtSignal(str)

    def __init__(self, task: dict, subtasks: list, number_text: str, project_info: dict = None, parent=None):
        super().__init__(parent)
        self.task = task
        self.subtasks = subtasks
        self.project_info = project_info
        self.setStyleSheet("TaskRow{background:transparent;border-radius:8px;margin-bottom:2px;}")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.expanded = False
        self._drag_start_pos = None
        self._dragged = False
        
        self._flash_opacity = 0.0
        self._flash_anim = QPropertyAnimation(self, b"flash_opacity")
        self._flash_anim.setDuration(450)
        self._flash_anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.main_lay = QVBoxLayout(self)
        self.main_lay.setContentsMargins(0, 0, 0, 0)
        self.main_lay.setSpacing(0)

        # Top row
        self.top_frame = QFrame()
        self.top_frame.setFixedHeight(46)
        lay = QHBoxLayout(self.top_frame)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(10)

        self.lbl_num = QLabel(number_text)
        self.lbl_num.setFixedWidth(28)
        self.lbl_num.setStyleSheet(f"color:{GOLD};font-weight:700;")

        self.lbl_recur = QLabel("↻")
        self.lbl_recur.setFixedWidth(14)
        self.lbl_recur.setStyleSheet(f"color:{TEXT_GRAY};font-weight:700;")
        self.lbl_recur.setVisible(bool(task.get("recur")))

        self.lbl_emoji = QLabel(task.get("emoji", "📝"))
        self.lbl_emoji.setFixedWidth(26)

        # Time Label
        time_str = task.get("due_time", "")
        display_time = time_str
        time_color = GOLD
        if task.get("due_date"):
             try:
                 d = datetime.strptime(task["due_date"], "%Y-%m-%d").date()
                 today = date.today()
                 delta = (d - today).days
                 
                 if delta < 0: date_str, time_color = "Overdue", "#ff4d4d"
                 elif delta == 0: date_str, time_color = "Today", "#ff9f43"
                 elif delta == 1: date_str = "Tomorrow"
                 elif delta < 7: date_str = d.strftime("%A")
                 else: date_str = d.strftime("%b %d")
                 
                 display_time = f"{date_str} {time_str}".strip()
             except: pass
        self.lbl_time = QLabel(display_time if display_time else "")
        self.lbl_time.setStyleSheet(f"color:{time_color};font-size:11px;font-weight:bold;margin-right:4px;")
        self.lbl_time.setVisible(bool(time_str))

        # Project Dot
        self.btn_proj = QPushButton("●")
        self.btn_proj.setFixedSize(16, 16)
        self.btn_proj.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        color = project_info['color'] if project_info else 'transparent'
        self.btn_proj.setStyleSheet(f"color:{color};background:transparent;border:none;font-size:10px;margin-right:4px;")
        self.btn_proj.setToolTip(f"Go to Project: {project_info['name']}") if project_info else None
        self.btn_proj.setVisible(bool(project_info))
        if project_info:
            self.btn_proj.clicked.connect(lambda: self.projectClicked.emit(project_info['id']))

        self.lbl_text = QLabel(task.get("text", ""))
        self.lbl_text.setWordWrap(True)

        # Link Button (URL or File)
        self.url = self._detect_link(task)
        self.btn_link = QPushButton("🔗")
        self.btn_link.setFixedSize(24, 24)
        self.btn_link.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_link.setStyleSheet(
            f"QPushButton{{color:{TEXT_GRAY};background:transparent;border:none;font-size:14px;}}"
            f"QPushButton:hover{{color:{GOLD};}}"
        )
        self.btn_link.setToolTip("Open Link/File")
        self.btn_link.clicked.connect(self._open_link)
        self.btn_link.setVisible(bool(self.url))

        self.btn_focus = QPushButton("👁")
        self.btn_focus.setFixedSize(24, 24)
        self.btn_focus.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_focus.setStyleSheet(
            f"QPushButton{{color:{TEXT_GRAY};background:transparent;border:none;font-size:14px;}}"
            f"QPushButton:hover{{color:{GOLD};}}"
        )
        self.btn_focus.setToolTip("Focus (Zen Mode)")
        self.btn_focus.clicked.connect(lambda: self.focusRequested.emit(self.task["id"]))

        self.lbl_note = QLabel("•")
        self.lbl_note.setFixedWidth(10)
        self.lbl_note.setStyleSheet(f"color:{TEXT_GRAY};font-size:20px;")
        has_note = bool((task.get("note") or "").strip()) or bool(self.subtasks)
        self.lbl_note.setVisible(has_note)

        # More Button (Visible on Hover)
        self.btn_more = QPushButton("⋮")
        self.btn_more.setFixedSize(24, 24)
        self.btn_more.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_more.setStyleSheet(
            f"QPushButton{{color:{TEXT_GRAY};background:transparent;border:none;font-size:16px;font-weight:bold;}}"
            f"QPushButton:hover{{color:{TEXT_WHITE};background:{HOVER_BG};border-radius:12px;}}"
        )
        self.btn_more.setToolTip("More Options")
        self.btn_more.clicked.connect(self._on_more_click)
        self.btn_more.setVisible(False)

        self.chk = AnimatedCheckbox()
        self.chk.clicked.connect(lambda: self.toggled.emit(self.task["id"]))

        lay.addWidget(self.lbl_num)
        lay.addWidget(self.lbl_recur)
        lay.addWidget(self.lbl_emoji)
        lay.addWidget(self.lbl_time)
        lay.addWidget(self.btn_proj)
        lay.addWidget(self.lbl_text, 1)
        lay.addWidget(self.btn_link)
        lay.addWidget(self.btn_focus)
        lay.addWidget(self.lbl_note)
        lay.addWidget(self.btn_more)
        lay.addWidget(self.chk)

        # Expansion area
        self.expansion = QWidget()
        self.expansion.setVisible(False)
        self.exp_lay = QVBoxLayout(self.expansion)
        self.exp_lay.setContentsMargins(42, 0, 12, 12)
        self.exp_lay.setSpacing(4)

        # Note content
        if task.get("note"):
            lbl = QLabel(task.get("note"))
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color:{TEXT_GRAY};font-size:13px;padding-bottom:6px;")
            self.exp_lay.addWidget(lbl)

        # Subtasks content
        for st in self.subtasks:
            sw = SubtaskWidget(st)
            sw.toggled.connect(self.subtaskToggled.emit)
            sw.editRequested.connect(lambda sid: self.subtaskEdited.emit(self.task["id"], sid))
            self.exp_lay.addWidget(sw)

        # Add Step Button
        self.btn_add_step = QPushButton("+ Add Step")
        self.btn_add_step.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_add_step.setStyleSheet(
            f"QPushButton{{background:transparent;color:{GOLD};border:1px dashed {GOLD};border-radius:6px;padding:4px;text-align:left;}}"
            f"QPushButton:hover{{background:{HOVER_BG};}}"
        )
        self.btn_add_step.clicked.connect(lambda: self.addStepRequested.emit(self.task["id"]))
        self.exp_lay.addWidget(self.btn_add_step)

        self.main_lay.addWidget(self.top_frame)
        self.main_lay.addWidget(self.expansion)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self._apply_state()

    def get_opacity(self): return self.opacity_effect.opacity()
    def set_opacity(self, o): self.opacity_effect.setOpacity(o)
    opacity_prop = pyqtProperty(float, get_opacity, set_opacity)

    def _detect_link(self, task):
        # Check text and note for URLs or file paths
        content = (task.get("text", "") + "\n" + (task.get("note") or ""))
        # Web URL
        url_match = re.search(r'(https?://\S+)', content)
        if url_match:
            return url_match.group(0)
        # Local File (simple check)
        if task.get("note") and os.path.exists(task.get("note").strip()):
            return task.get("note").strip()
        return None

    def _open_link(self):
        if self.url:
            if os.path.exists(self.url):
                QDesktopServices.openUrl(QUrl.fromLocalFile(self.url))
            else:
                QDesktopServices.openUrl(QUrl(self.url))

    def _on_more_click(self):
        self.menuRequested.emit(self.btn_more.mapToGlobal(QPoint(0, 24)))

    def get_flash_opacity(self): return self._flash_opacity
    def set_flash_opacity(self, v): 
        self._flash_opacity = v
        self.update()
    flash_opacity = pyqtProperty(float, get_flash_opacity, set_flash_opacity)

    def flash(self):
        self._flash_anim.stop()
        self._flash_anim.setStartValue(0.25)
        self._flash_anim.setEndValue(0.0)
        self._flash_anim.start()

    def setExpanded(self, expanded):
        self.expanded = expanded
        self.expansion.setVisible(expanded)
        if expanded: self.resized.emit()

    def _apply_state(self):
        done = bool(self.task.get("completed"))
        if done:
            self.lbl_text.setStyleSheet(f"color:{TEXT_GRAY};text-decoration:line-through;")
        else:
            self.lbl_text.setStyleSheet(f"color:{TEXT_WHITE};")
        self.chk.setChecked(done)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = e.pos()
            self._dragged = False
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if not (e.buttons() & Qt.MouseButton.LeftButton):
            return
        if not self._drag_start_pos:
            return
        if (e.pos() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
        
        self._dragged = True
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self.task["id"])
        mime.setData("application/taskflow-task", self.task["id"].encode())
        drag.setMimeData(mime)
        
        # Create a nice drag pixmap with background
        pix = QPixmap(self.size())
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(CARD_BG))
        painter.setPen(QPen(QColor(GOLD), 1))
        painter.drawRoundedRect(pix.rect().adjusted(0,0,-1,-1), 8, 8)
        painter.end()
        self.render(pix, QPoint(), QRegion(), QWidget.RenderFlag.DrawChildren)
        
        drag.setPixmap(pix)
        drag.setHotSpot(e.pos())
        drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and not self._dragged and self._drag_start_pos:
            if self.task.get("note") or self.subtasks:
                self.expanded = not self.expanded
                self.expansion.setVisible(self.expanded)
                self.resized.emit()
        super().mouseReleaseEvent(e)

    def enterEvent(self, e):
        self.setStyleSheet(f"TaskRow{{background:{HOVER_BG};border-radius:8px;margin-bottom:2px;}}")
        self.btn_more.setVisible(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.setStyleSheet("TaskRow{background:transparent;border-radius:8px;margin-bottom:2px;}")
        self.btn_more.setVisible(False)
        super().leaveEvent(e)

    def paintEvent(self, e):
        super().paintEvent(e)
        if self._flash_opacity > 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(GOLD))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setOpacity(self._flash_opacity)
            painter.drawRoundedRect(self.rect(), 8, 8)


class SectionBlock(QWidget):
    requestResize = pyqtSignal()
    renameRequested = pyqtSignal(str)
    deleteRequested = pyqtSignal(str)
    clearCompletedRequested = pyqtSignal(str)
    collapsedChanged = pyqtSignal(bool)

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.name = name
        self.collapsed = False
        self.setAcceptDrops(True)
        self.setStyleSheet("background:transparent;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 6)
        lay.setSpacing(0)

        # Header
        self.header = QFrame()
        self.header.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        h_lay = QHBoxLayout(self.header)
        h_lay.setContentsMargins(4, 4, 4, 4)
        
        self.btn_arrow = QLabel("▼")
        self.btn_arrow.setFixedSize(20, 20)
        self.btn_arrow.setStyleSheet(f"color:{TEXT_GRAY};font-size:10px;")
        
        self.lbl = QLabel(name)
        self.lbl.setStyleSheet(f"color:{TEXT_GRAY};font-size:12px;font-weight:800;letter-spacing:1px;text-transform:uppercase;")
        
        h_lay.addWidget(self.btn_arrow)
        h_lay.addWidget(self.lbl)
        h_lay.addStretch()

        self.header.mousePressEvent = self._on_header_click
        self.header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.header.customContextMenuRequested.connect(self._on_header_menu)

        self.progress = SmoothProgressBar()
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"QProgressBar{{border:none;background:{HOVER_BG};border-radius:1px;}} QProgressBar::chunk{{background:{GOLD};border-radius:1px;}}")
        lay.addWidget(self.progress)

        self.list = TaskListWidget(name)
        self.list.heightChanged.connect(self.requestResize.emit)

        lay.addWidget(self.header)
        lay.addWidget(self.list)

    def toggle_collapse(self):
        self.collapsed = not self.collapsed
        self.btn_arrow.setText("▶" if self.collapsed else "▼")
        
        # Animation logic
        if not hasattr(self, "_anim"):
            self._anim = QPropertyAnimation(self.list, b"maximumHeight")
            self._anim.setDuration(250)
            self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._anim.valueChanged.connect(lambda: self.requestResize.emit())

        self._anim.stop()
        
        if not self.collapsed:
            self.list.setVisible(True)
            self.list.update_height() # Ensure real_height is set
            start = 0
            end = self.list.real_height
        else:
            start = self.list.height()
            end = 0

        self.list.setMinimumHeight(0)
        self.list.setMaximumHeight(start)
        
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        
        def on_finished():
            if self.collapsed: self.list.setVisible(False)
            else: self.list.setFixedHeight(self.list.real_height)
            self.requestResize.emit()
            
        try: self._anim.finished.disconnect()
        except TypeError: pass
        self._anim.finished.connect(on_finished)
        self._anim.start()
        
        self.collapsedChanged.emit(self.collapsed)

    def _on_header_click(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.toggle_collapse()

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat("application/taskflow-task"):
            e.accept()
        elif e.mimeData().hasUrls():
            e.accept()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat("application/taskflow-task") or e.mimeData().hasUrls():
            e.setDropAction(Qt.DropAction.MoveAction)
            e.accept()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):
        if e.mimeData().hasFormat("application/taskflow-task"):
            task_id = e.mimeData().text()
            self.list.taskMoved.emit(task_id, self.name, 0)
            e.accept()
        else:
            super().dropEvent(e)

    def update_progress(self, total: int, completed: int):
        if total == 0:
            self.progress.setValue(0)
            self.progress.setVisible(False)
        else:
            self.progress.setVisible(True)
            self.progress.setMaximum(total)
            self.progress.setValueSmooth(completed)
            if self.progress.value() == 0 and completed > 0: self.progress.setInitialValue(completed)

    def _on_header_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};}}"
            f"QMenu::item{{padding:8px 22px;}}"
            f"QMenu::item:selected{{background:{HOVER_BG};}}"
            f"QMenu::separator{{background:{HOVER_BG};height:1px;margin:4px 0px;}}"
        )
        act_rename = menu.addAction("Rename")
        act_del = menu.addAction("Delete Section")
        menu.addSeparator()
        act_clear = menu.addAction("Clear Completed")
        act_sort = menu.addAction("Sort by Priority")
        
        chosen = menu.exec(self.header.mapToGlobal(pos))
        if chosen == act_rename:
            self.renameRequested.emit(self.name)
        elif chosen == act_del:
            self.deleteRequested.emit(self.name)
        elif chosen == act_clear:
            self.clearCompletedRequested.emit(self.name)
        elif chosen == act_sort:
            # We need to access the main window to sort
            # This is a bit hacky but works for the structure
            mw = self.window()
            if hasattr(mw, "_sort_section_by_priority"):
                mw._sort_section_by_priority(self.name)


class BoardListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.setStyleSheet(
            "QListWidget{background:transparent;border:none;}"
            "QListWidget::item{background:transparent;border:none;}"
        )
        self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def dropEvent(self, event):
        super().dropEvent(event)
        # Re-order sections in state
        # (Handled by parent checking order)


class ConflictDialog(QDialog):
    def __init__(self, local_task, remote_task, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sync Conflict")
        self.setFixedSize(500, 300)
        self.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};")
        
        self.chosen_task = local_task # Default
        
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Conflict detected! Two versions modified at the exact same time."))
        
        h = QHBoxLayout()
        
        # Local
        local_box = QFrame()
        local_box.setStyleSheet(f"background:{DARK_BG};border:1px solid {HOVER_BG};border-radius:8px;padding:10px;")
        l_lay = QVBoxLayout(local_box)
        l_lay.addWidget(QLabel("<b>Local Version</b>"))
        l_lay.addWidget(QLabel(f"Text: {local_task.get('text')}"))
        l_lay.addWidget(QLabel(f"Section: {local_task.get('section')}"))
        l_lay.addWidget(QLabel(f"Done: {'Yes' if local_task.get('completed') else 'No'}"))
        l_btn = QPushButton("Keep Local")
        l_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        l_btn.setStyleSheet(f"background:{HOVER_BG};color:{TEXT_WHITE};border-radius:6px;padding:6px;")
        l_btn.clicked.connect(lambda: self._resolve(local_task))
        l_lay.addWidget(l_btn)
        h.addWidget(local_box)
        
        # Remote
        remote_box = QFrame()
        remote_box.setStyleSheet(f"background:{DARK_BG};border:1px solid {GOLD};border-radius:8px;padding:10px;")
        r_lay = QVBoxLayout(remote_box)
        r_lay.addWidget(QLabel("<b>Remote Version</b>"))
        r_lay.addWidget(QLabel(f"Text: {remote_task.get('text')}"))
        r_lay.addWidget(QLabel(f"Section: {remote_task.get('section')}"))
        r_lay.addWidget(QLabel(f"Done: {'Yes' if remote_task.get('completed') else 'No'}"))
        r_btn = QPushButton("Keep Remote")
        r_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        r_btn.setStyleSheet(f"background:{GOLD};color:{DARK_BG};border-radius:6px;padding:6px;font-weight:bold;")
        r_btn.clicked.connect(lambda: self._resolve(remote_task))
        r_lay.addWidget(r_btn)
        h.addWidget(remote_box)
        
        lay.addLayout(h)

    def _resolve(self, task):
        self.chosen_task = task
        self.accept()

class DropButton(QPushButton):
    dropped = pyqtSignal(str)
    hover_switch = pyqtSignal()

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setAcceptDrops(True)
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self.hover_switch.emit)

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat("application/taskflow-task"):
            e.accept()
            self._hover_timer.start(600) # Switch tab after hovering for 600ms
        else:
            super().dragEnterEvent(e)

    def dragLeaveEvent(self, e):
        self._hover_timer.stop()
        super().dragLeaveEvent(e)

    def dropEvent(self, e):
        self._hover_timer.stop()
        if e.mimeData().hasFormat("application/taskflow-task"):
            task_id = e.mimeData().text()
            self.dropped.emit(task_id)
            e.accept()
        else:
            super().dropEvent(e)

class SyncHistoryDialog(QDialog):
    def __init__(self, history, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setWindowTitle("Sync History")
        self.setFixedSize(500, 400)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};")
        
        lay = QVBoxLayout(self)
        
        lbl = QLabel("Recent Sync Events")
        lbl.setStyleSheet(f"color:{GOLD};font-size:16px;font-weight:bold;")
        lay.addWidget(lbl)
        
        self.list = QListWidget()
        self.list.setStyleSheet(f"background:{DARK_BG};border:1px solid {HOVER_BG};border-radius:8px;padding:5px;")
        self.list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list.itemSelectionChanged.connect(self._on_selection)
        lay.addWidget(self.list)
        
        for entry in history:
            ts = entry.get("timestamp", "").replace("T", " ")[:16]
            src = entry.get("source", "Unknown")
            details = entry.get("details", "No details")
            item = QListWidgetItem(f"{ts} • {src}\n{details}")
            if "backup_file" in entry:
                item.setData(Qt.ItemDataRole.UserRole, entry["backup_file"])
                item.setToolTip("Click 'Restore' to revert to this state")
            self.list.addItem(item)

        self.btn_restore = QPushButton("Restore Selected State")
        self.btn_restore.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_restore.clicked.connect(self._restore_selected)
        self.btn_restore.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {GOLD};border-radius:6px;padding:8px;margin-top:5px;")
        self.btn_restore.setEnabled(False)
        lay.addWidget(self.btn_restore)

        btn_close = QPushButton("Close")
        btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet(f"background:{HOVER_BG};color:{TEXT_WHITE};border-radius:6px;padding:8px;")
        lay.addWidget(btn_close)

    def _on_selection(self):
        item = self.list.currentItem()
        has_backup = bool(item and item.data(Qt.ItemDataRole.UserRole))
        self.btn_restore.setEnabled(has_backup)
        if has_backup:
            self.btn_restore.setStyleSheet(f"background:{GOLD};color:{DARK_BG};border:1px solid {GOLD};border-radius:6px;padding:8px;margin-top:5px;font-weight:bold;")
        else:
            self.btn_restore.setStyleSheet(f"background:{CARD_BG};color:{TEXT_GRAY};border:1px solid {HOVER_BG};border-radius:6px;padding:8px;margin-top:5px;")

    def _restore_selected(self):
        item = self.list.currentItem()
        if not item: return
        
        backup_file = item.data(Qt.ItemDataRole.UserRole)
        if not backup_file: return
        
        if self.main_window:
            self.main_window._restore_from_backup(backup_file)
            self.accept()

class ProjectSelectionDialog(QDialog):
    def __init__(self, projects, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Project")
        self.setFixedSize(300, 400)
        self.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};")
        self.selected_project_id = None
        
        lay = QVBoxLayout(self)
        self.list = QListWidget()
        self.list.setStyleSheet(f"background:{DARK_BG};border:1px solid {HOVER_BG};border-radius:8px;padding:5px;")
        
        # "No Project" option
        item_none = QListWidgetItem("No Project")
        item_none.setData(Qt.ItemDataRole.UserRole, None)
        self.list.addItem(item_none)
        
        for p in projects:
            item = QListWidgetItem(f"● {p['name']}")
            item.setForeground(QColor(p['color']))
            item.setData(Qt.ItemDataRole.UserRole, p['id'])
            self.list.addItem(item)
            
        self.list.itemClicked.connect(self._on_click)
        lay.addWidget(self.list)

    def _on_click(self, item):
        self.selected_project_id = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

class BackupManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setWindowTitle("Backup Manager")
        self.setFixedSize(500, 400)
        self.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};")
        
        lay = QVBoxLayout(self)
        
        lbl = QLabel("Available Backups")
        lbl.setStyleSheet(f"color:{GOLD};font-size:16px;font-weight:bold;")
        lay.addWidget(lbl)
        
        self.list = QListWidget()
        self.list.setStyleSheet(f"background:{DARK_BG};border:1px solid {HOVER_BG};border-radius:8px;padding:5px;")
        self.list.itemSelectionChanged.connect(self._on_selection)
        lay.addWidget(self.list)
        
        btn_lay = QHBoxLayout()
        
        self.btn_restore = QPushButton("Restore")
        self.btn_restore.setEnabled(False)
        self.btn_restore.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_restore.clicked.connect(self._restore)
        self.btn_restore.setStyleSheet(f"background:{HOVER_BG};color:{TEXT_WHITE};border-radius:6px;padding:8px;")
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setEnabled(False)
        self.btn_delete.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_delete.clicked.connect(self._delete)
        self.btn_delete.setStyleSheet(f"background:{HOVER_BG};color:{TEXT_WHITE};border-radius:6px;padding:8px;")
        
        self.btn_close = QPushButton("Close")
        self.btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_close.clicked.connect(self.accept)
        self.btn_close.setStyleSheet(f"background:{HOVER_BG};color:{TEXT_WHITE};border-radius:6px;padding:8px;")
        
        btn_lay.addWidget(self.btn_restore)
        btn_lay.addWidget(self.btn_delete)
        btn_lay.addStretch()
        btn_lay.addWidget(self.btn_close)
        lay.addLayout(btn_lay)
        
        self._refresh_list()

    def _refresh_list(self):
        self.list.clear()
        backup_dir = os.path.join(DATA_DIR, "backups")
        if not os.path.exists(backup_dir):
            return
            
        files = sorted([f for f in os.listdir(backup_dir) if f.endswith(".json")], reverse=True)
        for f in files:
            # Parse timestamp from filename sync_backup_YYYYMMDD_HHMMSS.json
            display = f
            try:
                parts = f.replace("sync_backup_", "").replace(".json", "").split("_")
                if len(parts) == 2:
                    dt = datetime.strptime(f"{parts[0]}{parts[1]}", "%Y%m%d%H%M%S")
                    display = dt.strftime("%Y-%m-%d %H:%M:%S")
            except: pass
            
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, f)
            self.list.addItem(item)

    def _on_selection(self):
        has_sel = bool(self.list.selectedItems())
        self.btn_restore.setEnabled(has_sel)
        self.btn_delete.setEnabled(has_sel)
        
        if has_sel:
             self.btn_restore.setStyleSheet(f"background:{GOLD};color:{DARK_BG};border-radius:6px;padding:8px;font-weight:bold;")
             self.btn_delete.setStyleSheet(f"background:#c42b1c;color:{TEXT_WHITE};border-radius:6px;padding:8px;font-weight:bold;")
        else:
             self.btn_restore.setStyleSheet(f"background:{HOVER_BG};color:{TEXT_WHITE};border-radius:6px;padding:8px;")
             self.btn_delete.setStyleSheet(f"background:{HOVER_BG};color:{TEXT_WHITE};border-radius:6px;padding:8px;")

    def _restore(self):
        item = self.list.currentItem()
        if not item: return
        fname = item.data(Qt.ItemDataRole.UserRole)
        if self.main_window:
            self.main_window._restore_from_backup(fname)
            self.accept()

    def _delete(self):
        item = self.list.currentItem()
        if not item: return
        fname = item.data(Qt.ItemDataRole.UserRole)
        path = os.path.join(DATA_DIR, "backups", fname)
        
        confirm = QMessageBox.question(
            self, "Delete Backup",
            "Are you sure you want to delete this backup?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                os.remove(path)
                self._refresh_list()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

class RecurringTasksDialog(QDialog):
    def __init__(self, state_ref, parent=None):
        super().__init__(parent)
        self.state_ref = state_ref
        self.setWindowTitle("Recurring Tasks Manager")
        self.setFixedSize(500, 400)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};")
        
        lay = QVBoxLayout(self)
        
        lbl = QLabel("Active Recurring Tasks")
        lbl.setStyleSheet(f"color:{GOLD};font-size:16px;font-weight:bold;")
        lay.addWidget(lbl)
        
        self.list = QListWidget()
        self.list.setStyleSheet(f"background:{DARK_BG};border:1px solid {HOVER_BG};border-radius:8px;padding:5px;")
        self.list.itemDoubleClicked.connect(self._edit_recurrence)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context_menu)
        lay.addWidget(self.list)
        
        self.refresh_list()
        
        btn_close = QPushButton("Close")
        btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet(f"background:{HOVER_BG};color:{TEXT_WHITE};border-radius:6px;padding:8px;")
        lay.addWidget(btn_close)

    def refresh_list(self):
        self.list.clear()
        tasks = [t for t in self.state_ref["tasks"] if t.get("recur")]
        if not tasks:
            item = QListWidgetItem("No recurring tasks found.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(item)
            return

        for t in tasks:
            item = QListWidgetItem(f"{t.get('recur')} • {t.get('text')}")
            item.setData(Qt.ItemDataRole.UserRole, t["id"])
            item.setToolTip("Double-click to edit recurrence")
            self.list.addItem(item)

    def _edit_recurrence(self, item):
        tid = item.data(Qt.ItemDataRole.UserRole)
        if not tid: return
        
        task = next((t for t in self.state_ref["tasks"] if t["id"] == tid), None)
        if not task: return
        
        current = task.get("recur", "None")
        options = RECUR_OPTIONS
        
        idx = 0
        if current in options:
            idx = options.index(current)
            
        new_recur, ok = QInputDialog.getItem(self, "Edit Recurrence", f"Recurrence for '{task.get('text')}':", options, idx, False)
        
        if ok:
            task["recur"] = "" if new_recur == "None" else new_recur
            task["updated_at"] = _now_iso()
            self.refresh_list()
            if self.parent():
                self.parent()._schedule_save()
                self.parent()._refresh_tasks_ui()

    def _context_menu(self, pos):
        item = self.list.itemAt(pos)
        if not item: return
        tid = item.data(Qt.ItemDataRole.UserRole)
        if not tid: return

        menu = QMenu(self)
        menu.setStyleSheet(f"QMenu{{background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};}}")
        
        act_edit = menu.addAction("Edit Recurrence")
        act_stop = menu.addAction("Stop Recurring")
        
        chosen = menu.exec(self.list.mapToGlobal(pos))
        
        if chosen == act_edit:
            self._edit_recurrence(item)
        elif chosen == act_stop:
            self._stop_recurrence(tid)

    def _stop_recurrence(self, tid):
        task = next((t for t in self.state_ref["tasks"] if t["id"] == tid), None)
        if task:
            task["recur"] = ""
            task["updated_at"] = _now_iso()
            self.refresh_list()
            if self.parent():
                self.parent()._schedule_save()
                self.parent()._refresh_tasks_ui()

class DeviceSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sync Devices")
        self.setFixedSize(400, 350)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};")
        
        self.layout = QVBoxLayout(self)
        
        self.lbl_info = QLabel("Scanning for TaskFlow devices on local network...\n(Ensure this dialog is open on the other device too)")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setStyleSheet(f"color:{TEXT_GRAY};margin-bottom:10px;")
        self.layout.addWidget(self.lbl_info)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"background:{DARK_BG};border:1px solid {HOVER_BG};border-radius:8px;padding:5px;")
        self.layout.addWidget(self.list_widget)
        
        self.btn_scan = QPushButton("Rescan")
        self.btn_scan.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_scan.clicked.connect(self.scan)
        self.btn_scan.setStyleSheet(f"background:{HOVER_BG};color:{TEXT_WHITE};border-radius:6px;padding:6px;")
        self.layout.addWidget(self.btn_scan)
        
        self.btn_select = QPushButton("Select as Sync Target")
        self.btn_select.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_select.clicked.connect(self.accept)
        self.btn_select.setStyleSheet(f"background:{GOLD};color:{DARK_BG};border-radius:6px;padding:8px;font-weight:bold;margin-top:5px;")
        self.layout.addWidget(self.btn_select)

        self.btn_push = QPushButton("Push Data Now")
        self.btn_push.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_push.clicked.connect(lambda: self.done(2)) # Custom return code for Push
        self.btn_push.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {GOLD};border-radius:6px;padding:8px;margin-top:5px;")
        self.layout.addWidget(self.btn_push)
        
        self.port = 54545
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.bind(('', self.port))
        except:
            self.lbl_info.setText("Error: Could not bind discovery port (54545).")
            
        self.found_devices = {} # ip -> hostname
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_socket)
        self.timer.start(200)
        
        self.scan()

    def scan(self):
        self.list_widget.clear()
        self.found_devices.clear()
        msg = f"TASKFLOW_HELLO:{socket.gethostname()}".encode('utf-8')
        try:
            self.sock.sendto(msg, ('<broadcast>', self.port))
        except Exception as e:
            self.lbl_info.setText(f"Broadcast error: {e}")

    def _check_socket(self):
        while True:
            try:
                self.sock.setblocking(False)
                data, addr = self.sock.recvfrom(1024)
                msg = data.decode('utf-8', errors='ignore')
                if msg.startswith("TASKFLOW_HELLO:"):
                    parts = msg.split(":")
                    if len(parts) >= 2:
                        hostname = parts[1]
                        ip = addr[0]
                        if hostname != socket.gethostname() and ip not in self.found_devices:
                            self.found_devices[ip] = hostname
                            item = QListWidgetItem(f"{hostname} ({ip})")
                            item.setData(Qt.ItemDataRole.UserRole, ip)
                            self.list_widget.addItem(item)
            except:
                break

    def get_selected_device(self):
        item = self.list_widget.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole), item.text().split(" (")[0]
        return None, None
        
    def closeEvent(self, e):
        self.sock.close()
        super().closeEvent(e)


class ContributionGraph(QWidget):
    def __init__(self, state_ref, parent=None):
        super().__init__(parent)
        self.state_ref = state_ref
        self.setMouseTracking(True)
        self.cell_size = 14
        self.spacing = 3
        # 53 weeks * width + padding
        self.setMinimumSize(53 * (self.cell_size + self.spacing) + 40, 7 * (self.cell_size + self.spacing) + 40)
        self.hover_date = None
        self.hover_count = 0
        self.hover_pos = None

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        tasks = self.state_ref.get("tasks", [])
        counts = {}
        for t in tasks:
            if t.get("completed") and t.get("updated_at"):
                d = t["updated_at"][:10]
                counts[d] = counts.get(d, 0) + 1
        
        today = date.today()
        start_date = today - timedelta(days=365)
        # Align to Sunday
        idx = (start_date.weekday() + 1) % 7
        start_date -= timedelta(days=idx)

        max_count = max(counts.values()) if counts else 1

        # Draw Grid
        for col in range(53):
            for row in range(7):
                day_offset = col * 7 + row
                curr_date = start_date + timedelta(days=day_offset)
                if curr_date > today:
                    continue
                
                d_str = str(curr_date)
                count = counts.get(d_str, 0)
                
                x = col * (self.cell_size + self.spacing) + 10
                y = row * (self.cell_size + self.spacing) + 10
                
                if count == 0:
                    color = QColor(HOVER_BG)
                else:
                    # Interpolate opacity
                    alpha = min(255, 50 + int((count / max(5, max_count)) * 205))
                    c = QColor(GOLD)
                    c.setAlpha(alpha)
                    color = c
                
                painter.setBrush(color)
                painter.setPen(Qt.PenStyle.NoPen)
                rect = QRect(x, y, self.cell_size, self.cell_size)
                painter.drawRoundedRect(rect, 2, 2)
                
                if self.hover_pos and rect.contains(self.hover_pos):
                    self.hover_date = curr_date
                    self.hover_count = count
                    painter.setPen(QPen(QColor(TEXT_WHITE), 1))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRoundedRect(rect, 2, 2)

    def mouseMoveEvent(self, e):
        self.hover_pos = e.pos()
        self.update()
        super().mouseMoveEvent(e)
        
    def event(self, event):
        if event.type() == QEvent.Type.ToolTip:
            if self.hover_date:
                QToolTip.showText(event.globalPos(), f"{self.hover_date}: {self.hover_count} tasks", self)
            else:
                QToolTip.hideText()
            return True
        return super().event(event)

class ZenChartWidget(QWidget):
    def __init__(self, state_ref, parent=None):
        super().__init__(parent)
        self.state_ref = state_ref
        self.setMinimumHeight(150)

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Data prep
        sessions = self.state_ref.get("zen_stats", {}).get("sessions", [])
        daily_mins = {}
        today = date.today()
        
        for i in range(7):
            d = today - timedelta(days=i)
            daily_mins[d] = 0
            
        for s in sessions:
            try:
                s_date = datetime.fromisoformat(s["date"]).date()
                if s_date in daily_mins:
                    daily_mins[s_date] += s.get("duration", 0)
            except: pass
            
        # Draw
        w = self.width()
        h = self.height()
        bar_w = (w - 40) / 7
        max_val = max(daily_mins.values()) if daily_mins.values() else 1
        max_val = max(max_val, 60) # Minimum scale of 1 hour
        
        sorted_dates = sorted(daily_mins.keys())
        
        for i, d in enumerate(sorted_dates):
            val = daily_mins[d]
            bar_h = (val / max_val) * (h - 30)
            x = 20 + i * bar_w
            y = h - 20 - bar_h
            
            # Bar
            rect = QRectF(x + 5, y, bar_w - 10, bar_h)
            color = GOLD if d == today else QColor(TEXT_GRAY)
            if val > 0:
                painter.setBrush(color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(rect, 4, 4)
            
            # Label
            painter.setPen(QColor(TEXT_GRAY))
            painter.drawText(QRectF(x, h - 15, bar_w, 15), Qt.AlignmentFlag.AlignCenter, d.strftime("%a"))
            
            # Value
            if val > 0:
                painter.drawText(QRectF(x, y - 15, bar_w, 15), Qt.AlignmentFlag.AlignCenter, f"{val}m")
        
    def event(self, event):
        if event.type() == QEvent.Type.ToolTip:
            if self.hover_date:
                QToolTip.showText(event.globalPos(), f"{self.hover_date}: {self.hover_count} tasks", self)
            else:
                QToolTip.hideText()
            return True
        return super().event(event)


class UltimateTaskFlow(QMainWindow):
    request_quick_capture = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.state = load_state()
        self._rollover_if_new_day()
        self.zen_end_time = None

        self._zen_task_id = None
        self.input = None
        self.note_editor = None
        self.section_blocks = {}

        self._dragging = False
        self._drag_possible = False
        self._drag_offset = QPoint(0, 0)
        self._last_snap_state = set()
        self._last_expanded_geom = None

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_now)

        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._auto_collapse_if_needed)

        self._reminder_timer = QTimer(self)
        self._reminder_timer.timeout.connect(self._check_reminders)
        self._reminder_timer.start(60000) # Check every minute

        self._busy_until = 0
        self._active_task_id = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Window
        )
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(resource_path("icon.ico")))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(WIN_W, WIN_H)

        # Apply Glass Effect
        apply_glass_effect(self.winId())

        self._setup_tray()

        # Quick Capture Setup
        self.quick_capture = QuickCaptureDialog(self)
        self.quick_capture.submitted.connect(self._on_quick_capture)
        self.request_quick_capture.connect(self.quick_capture.show_centered)
        
        if keyboard:
            try:
                keyboard.add_hotkey('alt+space', self.request_quick_capture.emit)
            except Exception as e:
                print(f"Failed to register hotkey: {e}")

        root = QWidget()
        self.setCentralWidget(root)
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)

        self.container = QFrame()
        self.container.setObjectName("container")
        self.container.setStyleSheet(f"#container{{background:{DARK_BG};border-radius:16px;border:1px solid rgba(255,255,255,0.1);}}")
        self.container.installEventFilter(self)
        
        root_lay.addWidget(self.container)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(22)
        shadow.setColor(QColor(0, 0, 0, 130))
        shadow.setOffset(0, 6)
        self.container.setGraphicsEffect(shadow)

        # Startup Animation Setup (Apply to root to avoid conflict with shadow)
        self.startup_effect = QGraphicsOpacityEffect(root)
        self.startup_effect.setOpacity(0.0)
        root.setGraphicsEffect(self.startup_effect)

        self.main = QVBoxLayout(self.container)
        self.main.setContentsMargins(0, 0, 0, 0)
        self.main.setSpacing(0)

        self._build_header()
        self._build_stack()
        self._wire_shortcuts()
        self._update_streak_display()
        
        # Overlay (created after stack to sit on top)
        self._apply_global_stylesheet()
        self.overlay = OverlayDialog(self.container)
        self.snap_glow = SnapGlow(self.container)
        self.confetti = ConfettiOverlay(self.container)

        self._apply_ui_state()
        self._remember_expanded_geom()

        self._clamp_to_screen()
        if self.state.get("ui", {}).get("collapsed", False):
            self._snap(self._collapsed_geometry(), animated=False)

        # Show What's New if version changed
        if self.state.get("last_version") != VERSION:
            QTimer.singleShot(1000, self._show_whats_new)

        if getattr(self, "_pending_weekly_review", False):
            QTimer.singleShot(1500, self._show_weekly_review)
        elif getattr(self, "_pending_briefing", False):
            QTimer.singleShot(1500, self._show_daily_briefing)

        # Check for updates silently on startup (delayed slightly to let UI load)
        QTimer.singleShot(2000, lambda: self._check_for_updates(silent=True))

    
        # (Sound removed for this version)

        # Zen Timer Setup
        self.zen_timer = QTimer(self)
        self.zen_timer.timeout.connect(self._update_zen_timer_tick)
        self.zen_remaining = 25 * 60
        self.zen_running = False

        # Sync Listener
        self.sync_listener = SyncListener()
        self.sync_listener.data_received.connect(self._on_sync_data_received)
        self.sync_listener.start()

        # Sync Activity Timer
        self._sync_timer = QTimer(self)
        self._sync_timer.timeout.connect(self._hide_sync_activity)

    def _apply_global_stylesheet(self):
        self.setStyleSheet(f"""
            QWidget {{ font-family: 'Segoe UI', sans-serif; }}
            QToolTip {{ 
                color: {TEXT_WHITE}; 
                background-color: {CARD_BG}; 
                border: 1px solid {HOVER_BG}; 
                border-radius: 4px; 
                padding: 4px; 
            }}
            QMenu {{ 
                background-color: {CARD_BG}; 
                border: 1px solid {HOVER_BG}; 
                border-radius: 12px; 
                padding: 6px; 
            }}
            QMenu::item {{ 
                color: {TEXT_WHITE}; 
                padding: 8px 24px; 
                border-radius: 6px; 
                margin: 2px;
            }}
            QMenu::item:selected {{ 
                background-color: {HOVER_BG}; 
                color: {GOLD};
            }}
            QMenu::separator {{
                height: 1px;
                background: {HOVER_BG};
                margin: 4px 0px;
            }}
            QScrollBar:vertical {{ 
                border: none; 
                background: transparent; 
                width: 6px; 
                margin: 0px; 
            }}
            QScrollBar::handle:vertical {{ 
                background: {HOVER_BG}; 
                min-height: 20px; 
                border-radius: 3px; 
            }}
            QScrollBar::handle:vertical:hover {{ 
                background: {GOLD}; 
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            
            QScrollBar:horizontal {{ 
                border: none; 
                background: transparent; 
                height: 6px; 
                margin: 0px; 
            }}
            QScrollBar::handle:horizontal {{ 
                background: {HOVER_BG}; 
                min-width: 20px; 
                border-radius: 3px; 
            }}
            QScrollBar::handle:horizontal:hover {{ 
                background: {GOLD}; 
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
        """)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_startup_animated", False):
            self._startup_animated = True
            self.startup_anim = QPropertyAnimation(self.startup_effect, b"opacity", self)
            self.startup_anim.setStartValue(0.0)
            self.startup_anim.setEndValue(1.0)
            self.startup_anim.setDuration(500)
            self.startup_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.startup_anim.finished.connect(lambda: self.centralWidget().setGraphicsEffect(None))
            self.startup_anim.start()

    def _animate_tab_transition(self, widget, direction):
        if not self.isVisible():
            return

        # Stop any running animations
        if hasattr(self, "_tab_anim") and self._tab_anim.state() == QPropertyAnimation.State.Running:
            self._tab_anim.stop()
        
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        
        self._tab_anim = QParallelAnimationGroup(self)
        
        pos_anim = QPropertyAnimation(widget, b"pos")
        pos_anim.setStartValue(QPoint(direction * 40, 0))
        pos_anim.setEndValue(QPoint(0, 0))
        pos_anim.setDuration(250)
        pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        fade_anim = QPropertyAnimation(effect, b"opacity")
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        fade_anim.setDuration(220)
        fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self._tab_anim.addAnimation(pos_anim)
        self._tab_anim.addAnimation(fade_anim)
        self._tab_anim.finished.connect(lambda: widget.setGraphicsEffect(None) if widget else None)
        self._tab_anim.start()

    def _setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(resource_path("icon.ico")))
        
        tray_menu = QMenu()
        
        # Quick Actions
        quick_menu = tray_menu.addMenu("Quick Actions")
        act_capture = quick_menu.addAction("Quick Capture")
        act_capture.triggered.connect(self.request_quick_capture.emit)
        act_add = quick_menu.addAction("Focus & Add Task")
        act_add.triggered.connect(lambda: (self.show(), self.activateWindow(), self._focus_add()))
        act_sync = quick_menu.addAction("Sync Now")
        act_sync.triggered.connect(self._broadcast_sync)
        
        tray_menu.addSeparator()
        act_show = tray_menu.addAction("Show/Hide")
        act_show.triggered.connect(self.toggle_collapse)
        act_quit = tray_menu.addAction("Quit")
        act_quit.triggered.connect(self._force_quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    @pyqtSlot(QSystemTrayIcon.ActivationReason)
    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_collapse()

    def _open_header_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};}}"
            f"QMenu::item{{padding:8px 22px;}}"
            f"QMenu::item:selected{{background:{HOVER_BG};}}"
        )
        act_settings = menu.addAction("Settings...")
        act_archive = menu.addAction("Archive Completed Tasks")
        menu.addSeparator()
        act_update = menu.addAction("Check for Updates...")
        chosen = menu.exec(self.header_bar.mapToGlobal(pos))
        if chosen == act_update:
            self._check_for_updates()
        elif chosen == act_settings:
            self._open_settings()
        elif chosen == act_archive:
            self._archive_completed()

    def _show_whats_new(self):
        self.header_bar.setVisible(False)
        self.stack.setCurrentWidget(self.page_whats_new)
        self._animate_tab_transition(self.page_whats_new)

    def _close_whats_new(self):
        if self.chk_dont_show.isChecked():
            self.state["last_version"] = VERSION
            self._schedule_save()
        self.header_bar.setVisible(True)
        self._switch_tab(self.state.get("ui", {}).get("active_tab", "Tasks"))

    def _check_for_updates(self, silent=False):
        self._update_silent = silent
        self.update_thread = UpdateCheckThread()
        self.update_thread.finished.connect(self._on_update_check_finished)
        self.update_thread.start()

    def _on_update_check_finished(self, result):
        error = result.get("error")
        if error:
            if not getattr(self, "_update_silent", False):
                self._show_overlay("Update Failed", error, [("OK", None, "secondary")])
            return

        latest_version_str = result.get("latest_version")
        download_url = result.get("download_url")
        is_prerelease = result.get("is_prerelease", False)

        if not latest_version_str:
            if not getattr(self, "_update_silent", False):
                self._show_overlay("Update Failed", "Invalid version info from server.", [("OK", None, "secondary")])
            return

        try:
            latest_v = tuple(map(int, latest_version_str.split('.')))
            current_v = tuple(map(int, VERSION.split('.')))
        except ValueError:
            if not getattr(self, "_update_silent", False):
                self._show_overlay("Update Failed", f"Invalid version format: {latest_version_str}", [("OK", None, "secondary")])
            return

        if latest_v > current_v:
            # Check if production ready
            if is_prerelease:
                if not getattr(self, "_update_silent", False):
                    self._show_overlay("Update Available", f"A new pre-release (v{latest_version_str}) is available.\n(Not production ready)", [("OK", None, "secondary")])
                return

            if not download_url:
                if not getattr(self, "_update_silent", False):
                    self._show_overlay("Update Available", f"Version {latest_version_str} is available,\nbut no installer was found.", [("OK", None, "secondary")])
                return

            self._show_overlay(
                "Update Available",
                f"Version {latest_version_str} is available.\nDownload now?",
                [
                    ("Download", lambda: self._start_update_download(download_url), "primary"),
                    ("Later", None, "secondary")
                ]
            )
        else:
            if not getattr(self, "_update_silent", False):
                self._show_overlay("Up to Date", f"You're flowing with the newest version (v{VERSION}).", [("Awesome", None, "primary")])

    def _start_update_download(self, url):
        filename = url.split("/")[-1]
        if not filename or "." not in filename:
            filename = "TaskFlow_Update.exe"
        
        save_path = os.path.join(tempfile.gettempdir(), filename)
        
        self.progress_dialog = QProgressDialog("Downloading Update...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.show()
        
        self.down_thread = UpdateDownloadThread(url, save_path)
        self.down_thread.progress.connect(self.progress_dialog.setValue)
        self.down_thread.finished.connect(self._on_download_finished)
        self.down_thread.error.connect(self._on_download_error)
        self.progress_dialog.canceled.connect(self.down_thread.terminate)
        self.down_thread.start()

    def _check_reminders(self):
        now = datetime.now()
        today_iso = now.date().isoformat()
        current_time = now.time()
        
        for t in self.state["tasks"]:
            if t.get("completed") or t.get("reminder_sent"):
                continue
            
            d_date = t.get("due_date")
            d_time = t.get("due_time")
            
            if d_date == today_iso and d_time:
                try:
                    dt_time = datetime.strptime(d_time, "%H:%M").time()
                    # Notify 15 minutes before
                    diff = datetime.combine(date.min, dt_time) - datetime.combine(date.min, current_time)
                    
                    # Check window: 15 mins before, or up to 60 mins after (if missed due to sleep)
                    if timedelta(minutes=-60) <= diff <= timedelta(minutes=15):
                        msg = f"Upcoming task: {t.get('text')}\nDue at {d_time}"
                        if diff < timedelta(minutes=0):
                            msg = f"Overdue task: {t.get('text')}\nWas due at {d_time}"
                        self._show_overlay("Reminder", msg, [("Got it", None, "primary")])
                        t["reminder_sent"] = True
                        self._schedule_save()
                except: pass
        
        # Check for day rollover (if app left open overnight)
        if self.state.get("last_opened") != today_iso:
            self._rollover_if_new_day(refresh_ui=True)

    def _on_download_finished(self, path):
        self.progress_dialog.close()
        try:
            # Run the installer/executable and close the app
            if os.name == "nt":
                os.startfile(path)
            else:
                subprocess.Popen([path], shell=False)
            self._force_quit()
        except Exception as e:
            self._show_overlay("Update Error", f"Failed to launch installer:\n{e}", [("OK", None, "secondary")])

    def _on_download_error(self, msg):
        self.progress_dialog.close()
        self._show_overlay("Download Failed", msg, [("OK", None, "secondary")])

    def _open_settings(self):
        # Populate fields
        cfg = self.state.get("config", {})
        self.spin_zen.setValue(cfg.get("zen_duration", 25))
        self.chk_collapse.setChecked(cfg.get("auto_collapse", True))
        self.chk_snapping.setChecked(cfg.get("window_snapping", True))
        self.chk_hover_expand.setChecked(cfg.get("expand_on_hover", True))
        self.chk_compact.setChecked(cfg.get("compact_mode", False))
        self.chk_sound.setChecked(cfg.get("sound_enabled", True))
        self.chk_startup.setChecked(self._is_startup_enabled())
        
        self.header_bar.setVisible(False)
        self.stack.setCurrentWidget(self.page_settings)
        self._animate_tab_transition(self.page_settings, 1)

    def _close_settings(self):
        self.state["config"]["zen_duration"] = self.spin_zen.value()
        self.state["config"]["auto_collapse"] = self.chk_collapse.isChecked()
        self.state["config"]["window_snapping"] = self.chk_snapping.isChecked()
        self.state["config"]["expand_on_hover"] = self.chk_hover_expand.isChecked()
        self.state["config"]["compact_mode"] = self.chk_compact.isChecked()
        self.state["config"]["sound_enabled"] = self.chk_sound.isChecked()
        self._set_startup(self.chk_startup.isChecked())
        self._schedule_save()
        
        # Reset busy timer and schedule check so auto-collapse works immediately if enabled
        self._busy_until = 0
        self._schedule_autocollapse()
        self._reset_zen_timer()
        self._populate_zen_view(self._zen_task_id) if self._zen_task_id else None
        
        self.header_bar.setVisible(True)
        self._apply_ui_state() # Re-apply visibility settings
        self._switch_tab(self.state.get("ui", {}).get("active_tab", "Tasks"))

    def _archive_completed(self):
        completed = [t for t in self.state["tasks"] if t.get("completed")]
        if not completed:
            self._show_overlay("Archive", "No completed tasks to archive.", [("OK", None, "primary")])
            return
            
        self._show_overlay(
            "Archive Tasks",
            f"Permanently delete {len(completed)} completed tasks?",
            [
                ("Archive", self._do_archive_completed, "primary"),
                ("Cancel", None, "secondary")
            ]
        )

    def _do_archive_completed(self):
        self.state["tasks"] = [t for t in self.state["tasks"] if not t.get("completed")]
        self._schedule_save()
        self._refresh_tasks_ui()

    def _on_quick_capture(self, text):
        text, section, emoji, project_id, due_date, due_time, note = self._parse_task_input(text)
        self._create_task(text, section, emoji, project_id=project_id, due_date=due_date, due_time=due_time, note=note)
        self._schedule_save()
        self._refresh_tasks_ui()

    # ---------- Helpers ----------
    def _focus_is_text_entry(self) -> bool:
        fw = QApplication.focusWidget()
        return isinstance(fw, (QLineEdit, QTextEdit))

    # ---------- Close ----------
    def _quit(self):
        # Override close button to just hide/minimize
        self.hide()

    def _force_quit(self):
        try:
            self._save_now()
        except Exception:
            pass
        app = QApplication.instance()
        if app:
            app.quit()
        else:
            self.close()

    def closeEvent(self, event):
        try:
            self._save_now()
        except Exception:
            pass
        if hasattr(self, "sync_listener"):
            self.sync_listener.requestInterruption()
            self.sync_listener.wait(2000)
        event.ignore()
        self.hide()

    # ---------- Event handling ----------
    def eventFilter(self, obj, event):
        if obj == self.container and event.type() == event.Type.Resize:
            if hasattr(self, "overlay"):
                self.overlay.resize(self.container.size())
            if hasattr(self, "snap_glow"):
                self.snap_glow.resize(self.container.size())
            if hasattr(self, "confetti"):
                self.confetti.resize(self.container.size())

        watched = [w for w in (getattr(self, "input", None), getattr(self, "note_editor", None)) if w is not None]
        if watched and obj in tuple(watched):
            if event.type() in (event.Type.KeyPress, event.Type.MouseButtonPress, event.Type.FocusIn):
                self._mark_busy(2500)
        return super().eventFilter(obj, event)

    def enterEvent(self, event):
        self._auto_timer.stop()
        self._busy_until = 0 # Reset busy state on re-entry to ensure responsiveness
        if self.state.get("ui", {}).get("collapsed", False):
            if self.state.get("config", {}).get("expand_on_hover", True):
                self.toggle_collapse()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._schedule_autocollapse()
        super().leaveEvent(event)

    def focusOutEvent(self, event):
        self._schedule_autocollapse()
        super().focusOutEvent(event)

    def moveEvent(self, event):
        super().moveEvent(event)
        if not self.state.get("ui", {}).get("collapsed", False):
            self._remember_expanded_geom()

    # ---------- Dragging ----------
    def _header_widget_at(self, pos):
        if not hasattr(self, "header_bar") or self.header_bar is None:
            return None
        return self.header_bar.childAt(pos)

    def _drag_press(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        w = self._header_widget_at(e.position().toPoint())
        if isinstance(w, (QPushButton, QLineEdit, QComboBox)):
            return
        self._dragging = False
        self._drag_possible = True
        self._drag_start_global = e.globalPosition().toPoint()
        self._drag_offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        self._last_snap_state = set()
        self._mark_busy(2500)

    def _drag_move(self, e):
        if not self._drag_possible:
            return
        if not (e.buttons() & Qt.MouseButton.LeftButton):
            self._drag_possible = False
            self._dragging = False
            return
        
        if not self._dragging:
            moved = (e.globalPosition().toPoint() - self._drag_start_global).manhattanLength()
            if moved > QApplication.startDragDistance():
                self._dragging = True
            else:
                return

        pos = e.globalPosition().toPoint() - self._drag_offset
        
        if self.state.get("config", {}).get("window_snapping", True):
            scr = self.screen().availableGeometry()
            snap_dist = 25

            x, y = pos.x(), pos.y()
            w, h = self.width(), self.height()

            current_snaps = set()

            # Snap to vertical edges
            if abs(x - scr.left()) < snap_dist:
                x = scr.left()
                current_snaps.add("left")
            elif abs(x + w - scr.right()) < snap_dist:
                x = scr.right() - w
                current_snaps.add("right")

            # Snap to horizontal edges
            if abs(y - scr.top()) < snap_dist:
                y = scr.top()
                current_snaps.add("top")
            elif abs(y + h - scr.bottom()) < snap_dist:
                y = scr.bottom() - h
                current_snaps.add("bottom")

            new_snaps = current_snaps - self._last_snap_state
            if new_snaps:
                self.snap_glow.flash(new_snaps)
            self._last_snap_state = current_snaps

            self.move(x, y)
        else:
            self.move(pos)

    def _drag_release(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            was_dragging = self._dragging
            self._dragging = False
            self._drag_possible = False
            
            if self.state.get("ui", {}).get("collapsed", False):
                if not was_dragging and not self.state.get("config", {}).get("expand_on_hover", True):
                    self.toggle_collapse()
                else:
                    self._snap(self._collapsed_geometry(), animated=False)
            else:
                self._clamp_to_screen()
                self._remember_expanded_geom()

    # ---------- UI ----------
    def _build_header(self):
        self.header_bar = QFrame()
        self.header_bar.setFixedHeight(64)
        self.header_bar.setStyleSheet("background:transparent;")
        self.header_bar.mousePressEvent = self._drag_press
        self.header_bar.mouseMoveEvent = self._drag_move
        self.header_bar.mouseReleaseEvent = self._drag_release
        self.header_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.header_bar.customContextMenuRequested.connect(self._open_header_menu)

        lay = QHBoxLayout(self.header_bar)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(10)

        # Common style for all islands to support hover effects
        island_style = (
            f".QFrame{{background:{CARD_BG};border-radius:18px;border:1px solid {HOVER_BG};}}"
            f".QFrame:hover{{background:{HOVER_BG};border:1px solid {GOLD};}}"
        )

        # --- Island 1: Navigation ---
        self.nav_group = QFrame()
        self.nav_group.setStyleSheet(island_style)
        self.nav_group.setFixedHeight(36)
        nav_lay = QHBoxLayout(self.nav_group)
        nav_lay.setContentsMargins(12, 0, 12, 0)
        nav_lay.setSpacing(12)

        self.btn_tasks = DropButton("Tasks")
        self.btn_notes = DropButton("Notes")
        self.btn_projects = DropButton("Projects")
        self.btn_calendar = DropButton("Calendar")
        self.btn_calendar.setToolTip("Schedule & Timeline")
        
        # --- Search Group (Replaces Nav) ---
        self.search_group = QFrame()
        self.search_group.setVisible(False)
        self.search_group.setStyleSheet(island_style)
        self.search_group.setFixedHeight(36)
        search_lay = QHBoxLayout(self.search_group)
        search_lay.setContentsMargins(8, 0, 8, 0)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tasks & notes...")
        self.search_input.setStyleSheet(
            f"background:transparent;color:{TEXT_WHITE};border:none;font-size:14px;"
        )
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._perform_search)
        # Pressing Esc in search closes it
        self.search_shortcut_esc = QShortcut(QKeySequence("Esc"), self.search_input)
        self.search_shortcut_esc.activated.connect(self._toggle_search)
        
        search_lay.addWidget(self.search_input)

        for b in (self.btn_tasks, self.btn_notes, self.btn_projects, self.btn_calendar):
            b.setCheckable(True)
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            b.setStyleSheet(
                f"QPushButton{{color:{TEXT_GRAY};background:transparent;border:none;font-weight:800;}}"
                f"QPushButton:hover{{color:{TEXT_WHITE};}}"
                f"QPushButton:checked{{color:{GOLD};}}"
            )

        self.btn_tasks.clicked.connect(lambda: self._switch_tab("Tasks"))
        self.btn_notes.clicked.connect(lambda: self._switch_tab("Notes"))
        self.btn_projects.clicked.connect(lambda: self._switch_tab("Projects"))
        self.btn_calendar.clicked.connect(lambda: self._switch_tab("Calendar"))
        
        self.btn_tasks.setToolTip("Kanban Board")
        self.btn_notes.setToolTip("Quick Notes")

        # Drag & Drop Logic
        self.btn_tasks.dropped.connect(lambda tid: self._switch_tab("Tasks"))
        self.btn_tasks.hover_switch.connect(lambda: self._switch_tab("Tasks"))

        self.btn_notes.dropped.connect(self._on_task_dropped_on_notes)
        self.btn_notes.hover_switch.connect(lambda: self._switch_tab("Notes"))

        self.btn_calendar.dropped.connect(self._on_task_dropped_on_calendar)
        self.btn_calendar.hover_switch.connect(lambda: self._switch_tab("Calendar"))

        self.btn_projects.dropped.connect(self._on_task_dropped_on_projects)
        self.btn_projects.hover_switch.connect(lambda: self._switch_tab("Projects"))

        nav_lay.addWidget(self.btn_tasks)
        nav_lay.addWidget(self.btn_notes)
        nav_lay.addWidget(self.btn_projects)
        nav_lay.addWidget(self.btn_calendar)

        # --- Island 2: Streak ---
        self.streak_island = QFrame()
        self.streak_island.setStyleSheet(island_style)
        self.streak_island.setFixedHeight(36)
        streak_lay = QHBoxLayout(self.streak_island)
        streak_lay.setContentsMargins(12, 0, 12, 0)

        # Level Indicator
        self.lbl_level = QLabel("Lvl 1")
        self.lbl_level.setStyleSheet(f"color:{TEXT_WHITE};font-weight:bold;font-size:12px;")
        self.xp_bar = QProgressBar()
        self.xp_bar.setFixedSize(60, 6)
        self.xp_bar.setTextVisible(False)
        self.xp_bar.setStyleSheet(f"QProgressBar{{border:none;background:{HOVER_BG};border-radius:3px;}} QProgressBar::chunk{{background:{GOLD};border-radius:3px;}}")
        
        # Streak Indicator
        self.lbl_streak = QLabel("🔥 0")
        self.lbl_streak.setStyleSheet(f"color:{GOLD};font-weight:bold;font-size:14px;border:none;background:transparent;")
        self.lbl_streak.setToolTip("Daily Streak: Complete a task or Zen session to extend!")
        
        streak_lay.addWidget(self.lbl_level)
        streak_lay.addWidget(self.xp_bar)
        streak_lay.addWidget(self.lbl_streak)

        # --- Island 3: Tools (Search + Settings) ---
        self.tools_island = QFrame()
        self.tools_island.setStyleSheet(island_style)
        self.tools_island.setFixedHeight(36)
        tools_lay = QHBoxLayout(self.tools_island)
        tools_lay.setContentsMargins(8, 0, 8, 0)
        tools_lay.setSpacing(4)

        self.btn_search = QPushButton("🔍")
        self.btn_search.setFixedSize(28, 28)
        self.btn_search.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_search.setStyleSheet(
            f"QPushButton{{color:{TEXT_GRAY};background:transparent;border:none;font-weight:800;font-size:16px;}}"
            f"QPushButton:hover{{color:{TEXT_WHITE};}}"
        )
        self.btn_search.clicked.connect(self._toggle_search)
        self.btn_search.setToolTip("Search (Ctrl+F)")

        self.btn_cloud = QPushButton("☁")
        self.btn_cloud.setFixedSize(28, 28)
        self.btn_cloud.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_cloud.setStyleSheet(
            f"QPushButton{{color:{TEXT_GRAY};background:transparent;border:none;font-size:18px;}}"
        )
        self.btn_cloud.setToolTip("Cloud Sync Status")
        self.btn_cloud.clicked.connect(self._open_sync_devices)
        tools_lay.addWidget(self.btn_cloud)

        self.btn_stats = QPushButton("📊")
        self.btn_stats.setFixedSize(28, 28)
        self.btn_stats.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_stats.setStyleSheet(
            f"QPushButton{{color:{TEXT_GRAY};background:transparent;border:none;font-weight:800;font-size:16px;}}"
            f"QPushButton:hover{{color:{TEXT_WHITE};}}"
        )
        self.btn_stats.clicked.connect(self._open_stats)
        self.btn_stats.setToolTip("Statistics")

        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setFixedSize(28, 28)
        self.btn_settings.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_settings.setStyleSheet(
            f"QPushButton{{color:{TEXT_GRAY};background:transparent;border:none;font-weight:800;font-size:18px;}}"
            f"QPushButton:hover{{color:{TEXT_WHITE};}}"
        )
        self.btn_settings.clicked.connect(self._open_settings)
        self.btn_settings.setToolTip("Settings")

        tools_lay.addWidget(self.btn_search)
        tools_lay.addWidget(self.btn_stats)
        tools_lay.addWidget(self.btn_settings)

        # --- Island 4: Window Controls ---
        self.win_island = QFrame()
        self.win_island.setStyleSheet(island_style)
        self.win_island.setFixedHeight(36)
        win_lay = QHBoxLayout(self.win_island)
        win_lay.setContentsMargins(8, 0, 8, 0)
        win_lay.setSpacing(4)

        self.btn_collapse = QPushButton("<")
        self.btn_collapse.setFixedSize(28, 28)
        self.btn_collapse.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_collapse.setStyleSheet(
            f"QPushButton{{background:transparent;color:{TEXT_GRAY};border:none;font-weight:900;}}"
            f"QPushButton:hover{{background:{HOVER_BG};color:{TEXT_WHITE};}}"
        )
        self.btn_collapse.clicked.connect(self.toggle_collapse)
        self.btn_collapse.setToolTip("Collapse Window (Esc)")

        self.btn_minimize = QPushButton("−")
        self.btn_minimize.setFixedSize(28, 28)
        self.btn_minimize.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_minimize.setStyleSheet(
            f"QPushButton{{background:transparent;color:{TEXT_GRAY};border:none;font-weight:900;}}"
            f"QPushButton:hover{{background:{HOVER_BG};color:{TEXT_WHITE};}}"
        )
        self.btn_minimize.clicked.connect(self.showMinimized)
        self.btn_minimize.setToolTip("Minimize")

        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_close.setStyleSheet(
            f"QPushButton{{background:transparent;color:{TEXT_GRAY};border:none;font-weight:900;}}"
            f"QPushButton:hover{{color:#c42b1c;}}"
        )
        self.btn_close.clicked.connect(self._quit)
        self.btn_close.setToolTip("Close to Tray")

        win_lay.addWidget(self.btn_collapse)
        win_lay.addWidget(self.btn_minimize)
        win_lay.addWidget(self.btn_close)

        lay.addWidget(self.nav_group)
        lay.addWidget(self.search_group)
        lay.addWidget(self.streak_island)
        lay.addStretch()
        lay.addWidget(self.tools_island)
        lay.addWidget(self.win_island)

        self.main.addWidget(self.header_bar)

    def _build_stack(self):
        self.stack = QStackedWidget()
        self.main.addWidget(self.stack)

        self.page_tasks = QWidget()
        self.page_notes = QWidget()
        self.page_calendar = QWidget()
        self.page_projects = QWidget()
        self.page_zen = QWidget()
        self.page_stats = QWidget()
        self.page_settings = QWidget()
        self.page_whats_new = QWidget()

        self.stack.addWidget(self.page_tasks)
        self.stack.addWidget(self.page_notes)
        self.stack.addWidget(self.page_projects)
        self.stack.addWidget(self.page_calendar)
        self.stack.addWidget(self.page_zen)
        self.stack.addWidget(self.page_stats)
        self.stack.addWidget(self.page_settings)
        self.stack.addWidget(self.page_whats_new)

        self._build_tasks_page()
        self._build_notes_page()
        self._build_projects_page()
        self._build_calendar_page()
        self._build_zen_page()
        self._build_stats_page()
        self._build_settings_page()
        self._build_whats_new_page()

    def _build_tasks_page(self):
        lay = QVBoxLayout(self.page_tasks)
        lay.setContentsMargins(14, 0, 14, 12)
        lay.setSpacing(10)

        # Input Container to hold input + feedback
        input_container = QWidget()
        input_lay = QVBoxLayout(input_container)
        input_lay.setContentsMargins(0, 0, 0, 0)
        input_lay.setSpacing(2)

        self.input = QLineEdit()
        self.input.setPlaceholderText("✨ Add task…")
        self.input.setStyleSheet(
            f"QLineEdit{{background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};border-radius:12px;padding:12px;font-size:14px;}}"
            f"QLineEdit:focus{{border:1px solid {GOLD};}}"
        )
        self.input.setClearButtonEnabled(True)
        self.input.returnPressed.connect(self._quick_add_task)
        self.input.textChanged.connect(self._update_input_feedback)
        self.input.installEventFilter(self)
        input_lay.addWidget(self.input)

        self.input_feedback = QLabel("")
        self.input_feedback.setStyleSheet(f"color:{GOLD};font-size:11px;font-weight:bold;margin-left:4px;")
        self.input_feedback.setFixedHeight(0) # Hidden by default
        input_lay.addWidget(self.input_feedback)

        lay.addWidget(input_container)

        self.board_list = BoardListWidget()
        self.board_list.setStyleSheet(
            "QListWidget{border:none;background:transparent;}"
        )
        self.board_list.model().rowsMoved.connect(self._on_section_reordered)
        lay.addWidget(self.board_list, 1)
        
        self.board_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.board_list.customContextMenuRequested.connect(self._open_board_menu)

        # Scheduled Section Container (New Box)
        self.scheduled_container = QFrame()
        self.scheduled_container.setStyleSheet(f"background:{CARD_BG};border:1px solid {HOVER_BG};border-radius:12px;")
        self.scheduled_layout = QVBoxLayout(self.scheduled_container)
        self.scheduled_layout.setContentsMargins(10, 10, 10, 10)
        lay.insertWidget(1, self.scheduled_container) # Insert after input

        self.empty_state_lbl = QLabel("No tasks yet.\nType above to add one! 🚀")
        self.empty_state_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state_lbl.setStyleSheet(f"color:{TEXT_GRAY};font-size:16px;margin-top:40px;")
        self.empty_state_lbl.setVisible(False)
        lay.addWidget(self.empty_state_lbl)

        self._refresh_tasks_ui()

    def keyPressEvent(self, e):
        if e.matches(QKeySequence.StandardKey.Paste):
            self._paste_as_task()
        else:
            super().keyPressEvent(e)

    def _paste_as_task(self):
        cb = QApplication.clipboard()
        text = cb.text()
        if text:
            lines = text.strip().split('\n')
            if len(lines) > 1:
                title = lines[0][:60] + "..."
                note = text
                self._create_task(title, "Today", "📋", note=note)
            else:
                self._create_task(text.strip(), "Today", "📋")
            self._schedule_save()
            self._refresh_tasks_ui()
            self._show_overlay("Pasted", "Task created from clipboard.", [("OK", None, "primary")])

    def _build_calendar_page(self):
        lay = QVBoxLayout(self.page_calendar)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        # Day Switcher
        top = QHBoxLayout()
        btn_prev = QPushButton("<")
        btn_prev.setFixedSize(30, 30)
        btn_prev.clicked.connect(lambda: self._change_day(-1))
        btn_prev.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.cal_header = QLabel(_today_str())
        self.cal_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cal_header.setStyleSheet(f"color:{GOLD};font-size:16px;font-weight:bold;")
        self.cal_header.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cal_header.mousePressEvent = self._pick_date
        
        btn_next = QPushButton(">")
        btn_next.setFixedSize(30, 30)
        btn_next.clicked.connect(lambda: self._change_day(1))
        btn_next.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        top.addWidget(btn_prev)
        top.addWidget(self.cal_header, 1)
        top.addWidget(btn_next)
        lay.addLayout(top)

        # Timeline
        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setWidgetResizable(True)
        self.timeline = DayTimelineWidget(self.state)
        self.timeline.taskChanged.connect(self._on_timeline_task_changed)
        self.timeline_scroll.setWidget(self.timeline)
        
        # Floating "Now" button for timeline
        self.btn_now = QPushButton("Now", self.timeline_scroll)
        self.btn_now.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_now.setGeometry(10, 10, 50, 26)
        self.btn_now.setStyleSheet(
            f"background:{GOLD};color:{DARK_BG};border-radius:13px;font-weight:bold;border:none;"
        )
        self.btn_now.clicked.connect(self._go_to_today)
        
        lay.addWidget(self.timeline_scroll, 1)

        # Unscheduled list for this day
        lbl = QLabel("Tasks without time:")
        lbl.setStyleSheet(f"color:{TEXT_GRAY};font-size:12px;margin-top:10px;")
        lay.addWidget(self.cal_header)

        self.calendar_list = TaskListWidget("Calendar")
        self.calendar_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.calendar_list.customContextMenuRequested.connect(lambda pos: self._open_task_menu("Calendar", pos))
        self.calendar_list.taskMoved.connect(self._on_calendar_list_task_moved)
        lay.addWidget(self.calendar_list, 1)
        
        self._current_view_date = date.today()
        self._refresh_calendar_tasks()

    def _change_day(self, delta):
        self._current_view_date += timedelta(days=delta)
        self._refresh_calendar_tasks()

    def _go_to_today(self):
        self._current_view_date = date.today()
        self._refresh_calendar_tasks()
        self.timeline.scroll_to_now()

    def _pick_date(self, event):
        dlg = QDialog(self)
        dlg.setWindowTitle("Select Date")
        dlg.setWindowFlags(Qt.WindowType.Popup)
        lay = QVBoxLayout(dlg)
        cal = QCalendarWidget()
        cal.setSelectedDate(self._current_view_date)
        cal.activated.connect(lambda d: (self._set_view_date(d), dlg.accept()))
        lay.addWidget(cal)
        dlg.exec()

    def _set_view_date(self, qdate):
        self._current_view_date = qdate.toPyDate()
        self._refresh_calendar_tasks()

    def _on_timeline_task_changed(self, task_id):
        t = self._find_task(task_id)
        if t:
            t["updated_at"] = _now_iso()
            self._schedule_save()
            self._refresh_tasks_ui()

    def _on_calendar_drop(self, task_id, qdate):
        # Not used with timeline drop, but kept for compatibility if needed
        pass

    def _on_calendar_list_task_moved(self, task_id, section_name, index):
        # Dropped into the calendar list -> set date to selected date
        sel_date = self._current_view_date.isoformat()
        t = self._find_task(task_id)
        if t:
            t["due_date"] = sel_date
            t["due_time"] = None # Clear time when moving to list (unschedule time)
            t["section"] = "Scheduled"
            t["updated_at"] = _now_iso()
            self._schedule_save()
            self._refresh_calendar_tasks()
            self._refresh_tasks_ui()

    def _refresh_calendar_tasks(self):
        # Preserve scroll position
        scroll_pos = self.calendar_list.verticalScrollBar().value()

        sel_date = self._current_view_date.isoformat()
        
        # Update Header
        header_text = self._current_view_date.strftime("%A, %B %d")
        if sel_date == _today_str():
            header_text += " (Today)"
        self.cal_header.setText(header_text)

        # Refresh Timeline
        self.timeline.refresh_tasks(sel_date)

        # Refresh List (Tasks for this day but NO time set)
        self.calendar_list.clear()
        
        tasks = [t for t in self.state["tasks"] if t.get("due_date") == sel_date and not t.get("completed") and not t.get("due_time")]
        tasks.sort(key=lambda x: x.get("due_time") or "23:59")

        for i, t in enumerate(tasks):
            num = f"{i+1}."
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, t["id"])
            
            # Reuse TaskRow logic but simplified subtasks (empty list for calendar view to keep it compact)
            row = TaskRow(t, [], num)
            row.toggled.connect(self._toggle_task)
            row.focusRequested.connect(self.enter_zen_mode)
            row.addStepRequested.connect(self._add_step)
            
            item.setSizeHint(row.sizeHint())
            self.calendar_list.addItem(item)
            self.calendar_list.setItemWidget(item, row)
            
        # Restore scroll position
        self.calendar_list.verticalScrollBar().setValue(scroll_pos)

    def _build_projects_page(self):
        lay = QVBoxLayout(self.page_projects)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        # Stack to switch between List and Detail
        self.projects_stack = QStackedWidget()
        lay.addWidget(self.projects_stack)

        # --- Page 1: Project List ---
        self.p_page_list = QWidget()
        l_lay = QVBoxLayout(self.p_page_list)
        l_lay.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel("Projects")
        lbl.setStyleSheet(f"color:{GOLD};font-size:18px;font-weight:bold;")
        l_lay.addWidget(lbl)

        self.project_list_widget = QListWidget()
        self.project_list_widget.setStyleSheet(f"background:transparent;border:none;")
        self.project_list_widget.itemClicked.connect(self._open_project_detail)
        l_lay.addWidget(self.project_list_widget)

        btn_add = QPushButton("+ New Project")
        btn_add.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_add.setStyleSheet(f"background:{HOVER_BG};color:{TEXT_WHITE};border-radius:8px;padding:10px;font-weight:bold;")
        btn_add.clicked.connect(self._create_project)
        l_lay.addWidget(btn_add)

        self.projects_stack.addWidget(self.p_page_list)

        # --- Page 2: Project Detail ---
        self.p_page_detail = QWidget()
        d_lay = QVBoxLayout(self.p_page_detail)
        d_lay.setContentsMargins(0, 0, 0, 0)

        # Header
        h_lay = QHBoxLayout()
        btn_back = QPushButton("←")
        btn_back.setFixedSize(30, 30)
        btn_back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_back.setStyleSheet(f"background:transparent;color:{TEXT_GRAY};border:none;font-weight:bold;font-size:16px;")
        btn_back.clicked.connect(lambda: self.projects_stack.setCurrentWidget(self.p_page_list))
        
        self.lbl_p_name = QLabel("Project Name")
        self.lbl_p_name.setStyleSheet(f"color:{TEXT_WHITE};font-size:18px;font-weight:bold;")
        
        btn_del = QPushButton("🗑")
        btn_del.setFixedSize(30, 30)
        btn_del.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_del.setStyleSheet(f"background:transparent;color:{TEXT_GRAY};border:none;")
        btn_del.clicked.connect(self._delete_current_project)

        h_lay.addWidget(btn_back)
        h_lay.addWidget(self.lbl_p_name, 1)
        h_lay.addWidget(btn_del)
        d_lay.addLayout(h_lay)

        # Quick Add in Project
        self.p_input = QLineEdit()
        self.p_input.setPlaceholderText("Add task to this project...")
        self.p_input.setStyleSheet(
            f"background:{DARK_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};border-radius:8px;padding:8px;"
        )
        self.p_input.returnPressed.connect(self._add_project_task)
        d_lay.addWidget(self.p_input)
        d_lay.addSpacing(10)

        # Content
        self.p_detail_scroll = QScrollArea()
        self.p_detail_scroll.setWidgetResizable(True)
        self.p_detail_scroll.setStyleSheet("background:transparent;border:none;")
        
        self.p_detail_content = QWidget()
        self.p_detail_layout = QVBoxLayout(self.p_detail_content)
        self.p_detail_scroll.setWidget(self.p_detail_content)
        d_lay.addWidget(self.p_detail_scroll)

        self.projects_stack.addWidget(self.p_page_detail)
        
        self._refresh_projects_list()

    def _refresh_projects_list(self):
        self.project_list_widget.clear()
        tasks = self.state.get("tasks", [])
        for p in self.state.get("projects", []):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, p['id'])
            
            widget = ProjectListItem(p, tasks)
            item.setSizeHint(widget.sizeHint())
            
            self.project_list_widget.addItem(item)
            self.project_list_widget.setItemWidget(item, widget)

    def _open_project_detail(self, item):
        pid = item.data(Qt.ItemDataRole.UserRole)
        self._show_project_detail(pid)

    def _show_project_detail(self, pid):
        p = next((x for x in self.state["projects"] if x["id"] == pid), None)
        if not p: return
        self._current_project_id = pid
        self.lbl_p_name.setText(p["name"])
        self.lbl_p_name.setStyleSheet(f"color:{p['color']};font-size:20px;font-weight:bold;")
        
        # Clear detail layout
        while self.p_detail_layout.count():
            child = self.p_detail_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()

        # --- Tasks Section ---
        tasks = [t for t in self.state["tasks"] if t.get("project_id") == pid and not t.get("completed")]
        # Sort by order
        tasks.sort(key=lambda x: x.get("order", 0))
        
        lbl_t = QLabel(f"Tasks ({len(tasks)})")
        lbl_t.setStyleSheet(f"color:{TEXT_GRAY};font-weight:bold;margin-top:10px;margin-bottom:5px;")
        self.p_detail_layout.addWidget(lbl_t)
        
        if tasks:
            for i, t in enumerate(tasks):
                # Use TaskRow for full functionality
                # Pass None for project_info to hide the dot (redundant in project view)
                subtasks = [st for st in self.state["tasks"] if st.get("parent_id") == t["id"]]
                row = TaskRow(t, subtasks, f"{i+1}.", project_info=None)
                
                row.toggled.connect(lambda tid=t["id"]: self._toggle_task_from_project(tid))
                row.subtaskToggled.connect(self._toggle_task)
                row.subtaskEdited.connect(self._edit_subtask)
                row.focusRequested.connect(self.enter_zen_mode)
                row.addStepRequested.connect(self._add_step)
                row.menuRequested.connect(lambda pos, tid=t["id"]: self._open_task_context_menu(tid, pos))
                
                self.p_detail_layout.addWidget(row)
        else:
            lbl_empty = QLabel("No active tasks.")
            lbl_empty.setStyleSheet(f"color:{TEXT_GRAY};font-style:italic;margin-left:10px;")
            self.p_detail_layout.addWidget(lbl_empty)

        # --- Notes Section ---
        notes = []
        for g in self.state["notes"]["groups"].values():
            for n in g:
                if n.get("project_id") == pid:
                    notes.append(n)
        
        self.p_detail_layout.addSpacing(20)
        lbl_n = QLabel(f"Notes ({len(notes)})")
        lbl_n.setStyleSheet(f"color:{TEXT_GRAY};font-weight:bold;margin-top:10px;margin-bottom:5px;")
        self.p_detail_layout.addWidget(lbl_n)

        if notes:
            for n in notes:
                # Clickable Note Row
                btn = QPushButton()
                btn.setStyleSheet(
                    f"text-align:left;background:{DARK_BG};color:{TEXT_WHITE};border-radius:6px;padding:10px;border:1px solid transparent;"
                )
                # Add hover effect via stylesheet
                btn.setStyleSheet(btn.styleSheet() + f"QPushButton:hover{{border:1px solid {GOLD};}}")
                
                btn.setText(f"📄 {n.get('title', 'Untitled')}")
                btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                btn.clicked.connect(lambda _, nid=n["id"]: self._go_to_note(nid))
                
                self.p_detail_layout.addWidget(btn)
        else:
            lbl_empty = QLabel("No notes.")
            lbl_empty.setStyleSheet(f"color:{TEXT_GRAY};font-style:italic;margin-left:10px;")
            self.p_detail_layout.addWidget(lbl_empty)
            
        # Add Note Button
        btn_add_note = QPushButton("+ New Note")
        btn_add_note.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_add_note.setStyleSheet(f"background:transparent;color:{GOLD};border:1px dashed {GOLD};border-radius:6px;padding:6px;margin-top:5px;")
        btn_add_note.clicked.connect(self._add_project_note)
        self.p_detail_layout.addWidget(btn_add_note)

        self.p_detail_layout.addStretch()
        self.projects_stack.setCurrentWidget(self.p_page_detail)

    def _toggle_task_from_project(self, tid):
        self._toggle_task(tid)
        # Refresh project view to remove completed task or update state
        self._show_project_detail(self._current_project_id)

    def _go_to_note(self, nid):
        self._switch_tab("Notes")
        # Find group
        target_group = "General"
        for g, notes in self.state["notes"]["groups"].items():
            for n in notes:
                if n["id"] == nid:
                    target_group = g
                    break
        
        if hasattr(self, "note_group"):
            self.note_group.setCurrentText(target_group)
        self._refresh_notes_ui(select_note_id=nid, group=target_group)

    def _add_project_note(self):
        g = "General"
        self._ensure_group(g)
        note = {
            "id": str(uuid.uuid4()),
            "title": "New Project Note",
            "content": "",
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "project_id": self._current_project_id
        }
        self.state["notes"]["groups"][g].insert(0, note)
        self._schedule_save()
        self._go_to_note(note["id"])

    def _add_project_task(self):
        text = self.p_input.text().strip()
        if not text: return
        self.p_input.clear()
        self._create_task(text, "Today", "📝", project_id=self._current_project_id)
        self._schedule_save()
        self._show_project_detail(self._current_project_id)

    def _build_stats_page(self):
        lay = QVBoxLayout(self.page_stats)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(15)

        # Header
        top = QHBoxLayout()
        btn_back = QPushButton("← Back")
        btn_back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_back.setStyleSheet(f"color:{TEXT_GRAY};background:transparent;border:none;font-weight:bold;font-size:14px;")
        btn_back.clicked.connect(self._close_stats)
        
        lbl_title = QLabel("Statistics")
        lbl_title.setStyleSheet(f"color:{TEXT_WHITE};font-size:18px;font-weight:bold;")
        
        top.addWidget(btn_back)
        top.addStretch()
        top.addWidget(lbl_title)
        top.addStretch()
        dummy = QWidget()
        dummy.setFixedWidth(btn_back.sizeHint().width())
        top.addWidget(dummy)
        
        lay.addLayout(top)

        # Summary Stats
        self.lbl_stats_summary = QLabel()
        self.lbl_stats_summary.setStyleSheet(f"color:{TEXT_GRAY};font-size:14px;")
        self.lbl_stats_summary.setWordWrap(True)
        self.lbl_stats_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.lbl_stats_summary)

        # Zen Chart
        lbl_zen = QLabel("Focus Time (Last 7 Days)")
        lbl_zen.setStyleSheet(f"color:{GOLD};font-size:14px;font-weight:bold;margin-top:10px;")
        lay.addWidget(lbl_zen)
        self.zen_chart = ZenChartWidget(self.state)
        lay.addWidget(self.zen_chart)

        # Graph
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background:transparent;border:none;")
        self.stats_graph = ContributionGraph(self.state)
        scroll.setWidget(self.stats_graph)
        lay.addWidget(scroll, 1)

    def _build_zen_page(self):
        # Allow dragging on the Zen page background since header is hidden
        self.page_zen.mousePressEvent = self._drag_press
        self.page_zen.mouseMoveEvent = self._drag_move
        self.page_zen.mouseReleaseEvent = self._drag_release

        lay = QVBoxLayout(self.page_zen)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(20)

        # Top bar with Exit button
        top = QHBoxLayout()
        top.addStretch()

        self.zen_btn_collapse = QPushButton("<")
        self.zen_btn_collapse.setFixedSize(30, 30)
        self.zen_btn_collapse.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.zen_btn_collapse.setStyleSheet(
            f"QPushButton{{background:{CARD_BG};color:{TEXT_GRAY};border:none;border-radius:15px;font-weight:900;}}"
            f"QPushButton:hover{{background:{HOVER_BG};color:{TEXT_WHITE};}}"
        )
        self.zen_btn_collapse.clicked.connect(self.toggle_collapse)
        top.addWidget(self.zen_btn_collapse)

        self.zen_btn_minimize = QPushButton("−")
        self.zen_btn_minimize.setFixedSize(30, 30)
        self.zen_btn_minimize.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.zen_btn_minimize.setStyleSheet(
            f"QPushButton{{background:{CARD_BG};color:{TEXT_GRAY};border:none;border-radius:15px;font-weight:900;}}"
            f"QPushButton:hover{{background:{HOVER_BG};color:{TEXT_WHITE};}}"
        )
        self.zen_btn_minimize.clicked.connect(self.showMinimized)
        top.addWidget(self.zen_btn_minimize)

        self.zen_btn_close = QPushButton("×")
        self.zen_btn_close.setFixedSize(30, 30)
        self.zen_btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.zen_btn_close.setStyleSheet(
            f"QPushButton{{background:{CARD_BG};color:{TEXT_GRAY};border:none;border-radius:15px;font-weight:900;font-size:16px;}}"
            f"QPushButton:hover{{background:{HOVER_BG};color:{TEXT_WHITE};}}"
        )
        self.zen_btn_close.clicked.connect(self.exit_zen_mode)
        top.addWidget(self.zen_btn_close)
        lay.addLayout(top)

        # Center content
        self.zen_content = QVBoxLayout()
        self.zen_content.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.zen_emoji = QLabel("📝")
        self.zen_emoji.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zen_emoji.setStyleSheet("font-size: 64px; background: transparent;")
        
        self.zen_text = QLabel("Task Text")
        self.zen_text.setWordWrap(True)
        self.zen_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zen_text.setStyleSheet(f"color:{TEXT_WHITE}; font-size: 24px; font-weight: bold;")
        
        self.zen_content.addWidget(self.zen_emoji)
        self.zen_content.addWidget(self.zen_text)
        
        # Zen Stats
        self.lbl_zen_stats = QLabel("")
        self.lbl_zen_stats.setStyleSheet(f"color:{TEXT_GRAY}; font-size: 12px; margin-top: 5px;")
        self.zen_content.addWidget(self.lbl_zen_stats)

        # Timer UI
        self.lbl_timer = QLabel("25:00")
        self.lbl_timer.setStyleSheet(f"color:{GOLD}; font-size: 48px; font-weight: bold; margin-top: 20px;")
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        timer_controls = QHBoxLayout()
        timer_controls.setAlignment(Qt.AlignmentFlag.AlignCenter)
        timer_controls.setSpacing(20)
        
        self.btn_timer_toggle = QPushButton("▶ Start")
        self.btn_timer_toggle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_timer_toggle.setFixedSize(100, 40)
        self.btn_timer_toggle.setStyleSheet(
            f"QPushButton{{background:{HOVER_BG};color:{TEXT_WHITE};border-radius:20px;font-weight:bold;}}"
            f"QPushButton:hover{{background:{GOLD};color:{DARK_BG};}}"
        )
        self.btn_timer_toggle.clicked.connect(self._toggle_zen_timer)
        
        self.btn_timer_reset = QPushButton("↺")
        self.btn_timer_reset.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_timer_reset.setFixedSize(40, 40)
        self.btn_timer_reset.setStyleSheet(
            f"QPushButton{{background:{HOVER_BG};color:{TEXT_GRAY};border-radius:20px;font-weight:bold;font-size:18px;}}"
            f"QPushButton:hover{{color:{TEXT_WHITE};}}"
        )
        self.btn_timer_reset.clicked.connect(self._reset_zen_timer)
        
        timer_controls.addWidget(self.btn_timer_toggle)
        timer_controls.addWidget(self.btn_timer_reset)
        
        self.zen_content.addWidget(self.lbl_timer)
        self.zen_content.addLayout(timer_controls)
        
        # Timer Presets
        presets_lay = QHBoxLayout()
        presets_lay.setSpacing(10)
        
        for label, mins in [("Focus (25m)", 25), ("Short Break (5m)", 5), ("Long Break (15m)", 15)]:
            btn = QPushButton(label)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(f"background:{HOVER_BG};color:{TEXT_GRAY};border-radius:8px;padding:4px 8px;font-size:11px;")
            btn.clicked.connect(lambda _, m=mins: self._set_zen_duration(m))
            presets_lay.addWidget(btn)
        self.zen_content.addLayout(presets_lay)

        lay.addLayout(self.zen_content)
        
        # Subtasks area
        self.zen_subtasks_scroll = QScrollArea()
        self.zen_subtasks_scroll.setWidgetResizable(True)
        self.zen_subtasks_scroll.setStyleSheet("background: transparent; border: none;")
        self.zen_subtasks_container = QWidget()
        self.zen_subtasks_container.setStyleSheet("background: transparent;")
        self.zen_subtasks_layout = QVBoxLayout(self.zen_subtasks_container)
        self.zen_subtasks_scroll.setWidget(self.zen_subtasks_container)
        
        lay.addWidget(self.zen_subtasks_scroll, 1)

    def _build_settings_page(self):
        lay = QVBoxLayout(self.page_settings)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(15)

        # Header
        top = QHBoxLayout()
        btn_back = QPushButton("← Back")
        btn_back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_back.setStyleSheet(f"color:{TEXT_GRAY};background:transparent;border:none;font-weight:bold;font-size:14px;")
        btn_back.clicked.connect(self._close_settings)
        
        lbl_title = QLabel("Settings")
        lbl_title.setStyleSheet(f"color:{TEXT_WHITE};font-size:18px;font-weight:bold;")
        
        top.addWidget(btn_back)
        top.addStretch()
        top.addWidget(lbl_title)
        top.addStretch()
        # Dummy widget to balance layout
        dummy = QWidget()
        dummy.setFixedWidth(btn_back.sizeHint().width())
        top.addWidget(dummy)
        
        lay.addLayout(top)

        # Content
        # Zen Duration
        h1 = QHBoxLayout()
        lbl = QLabel("Zen Timer (minutes):")
        lbl.setStyleSheet(f"color:{TEXT_GRAY};")
        self.spin_zen = QSpinBox()
        self.spin_zen.setRange(1, 120)
        self.spin_zen.setStyleSheet(f"""
            QSpinBox {{
                background: {CARD_BG};
                border: 1px solid {HOVER_BG};
                border-radius: 8px;
                padding: 8px 12px;
                color: {TEXT_WHITE};
                font-weight: bold;
                selection-background-color: {GOLD};
                selection-color: {DARK_BG};
            }}
            QSpinBox:focus {{
                border: 1px solid {GOLD};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 24px;
                border-left: 1px solid {HOVER_BG};
                background: transparent;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background: {HOVER_BG};
                border-left: 1px solid {GOLD};
            }}
        """)
        h1.addWidget(lbl)
        h1.addWidget(self.spin_zen)
        lay.addLayout(h1)
        
        # Auto Collapse
        self.chk_collapse = QCheckBox("Auto-collapse when focus lost")
        self.chk_collapse.setStyleSheet(f"QCheckBox{{color:{TEXT_GRAY};}} QCheckBox::indicator{{border:1px solid {TEXT_GRAY};width:14px;height:14px;border-radius:3px;}} QCheckBox::indicator:checked{{background:{GOLD};border:1px solid {GOLD};}}")
        lay.addWidget(self.chk_collapse)

        # Expand on Hover
        self.chk_hover_expand = QCheckBox("Expand on hover (uncheck to click-to-expand)")
        self.chk_hover_expand.setStyleSheet(f"QCheckBox{{color:{TEXT_GRAY};}} QCheckBox::indicator{{border:1px solid {TEXT_GRAY};width:14px;height:14px;border-radius:3px;}} QCheckBox::indicator:checked{{background:{GOLD};border:1px solid {GOLD};}}")
        lay.addWidget(self.chk_hover_expand)

        # Compact Mode
        self.chk_compact = QCheckBox("Compact Mode (Hide Tabs)")
        self.chk_compact.setStyleSheet(f"QCheckBox{{color:{TEXT_GRAY};}} QCheckBox::indicator{{border:1px solid {TEXT_GRAY};width:14px;height:14px;border-radius:3px;}} QCheckBox::indicator:checked{{background:{GOLD};border:1px solid {GOLD};}}")
        lay.addWidget(self.chk_compact)

        # Sound Effects
        self.chk_sound = QCheckBox("Play Sound on Completion")
        self.chk_sound.setStyleSheet(f"QCheckBox{{color:{TEXT_GRAY};}} QCheckBox::indicator{{border:1px solid {TEXT_GRAY};width:14px;height:14px;border-radius:3px;}} QCheckBox::indicator:checked{{background:{GOLD};border:1px solid {GOLD};}}")
        lay.addWidget(self.chk_sound)

        # Window Snapping
        self.chk_snapping = QCheckBox("Window Snapping")
        self.chk_snapping.setStyleSheet(f"QCheckBox{{color:{TEXT_GRAY};}} QCheckBox::indicator{{border:1px solid {TEXT_GRAY};width:14px;height:14px;border-radius:3px;}} QCheckBox::indicator:checked{{background:{GOLD};border:1px solid {GOLD};}}")
        lay.addWidget(self.chk_snapping)

        # Start with Windows
        self.chk_startup = QCheckBox("Start with Windows")
        self.chk_startup.setStyleSheet(f"QCheckBox{{color:{TEXT_GRAY};}} QCheckBox::indicator{{border:1px solid {TEXT_GRAY};width:14px;height:14px;border-radius:3px;}} QCheckBox::indicator:checked{{background:{GOLD};border:1px solid {GOLD};}}")
        lay.addWidget(self.chk_startup)

        # Check for Updates
        self.btn_update = QPushButton("Check for Updates")
        self.btn_update.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_update.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};border-radius:6px;padding:6px;")
        self.btn_update.clicked.connect(self._check_for_updates)
        lay.addWidget(self.btn_update)

        # Cloud Sync / Data Location
        lbl_sync = QLabel("Cloud Sync / Data Location")
        lbl_sync.setStyleSheet(f"color:{GOLD};font-weight:bold;margin-top:10px;")
        lay.addWidget(lbl_sync)
        
        self.lbl_data_path = QLabel(DATA_DIR)
        self.lbl_data_path.setStyleSheet(f"color:{TEXT_GRAY};font-size:11px;font-style:italic;")
        self.lbl_data_path.setWordWrap(True)
        lay.addWidget(self.lbl_data_path)
        
        self.btn_move_data = QPushButton("Move Data to Cloud Folder...")
        self.btn_move_data.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_move_data.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};border-radius:6px;padding:6px;")
        self.btn_move_data.clicked.connect(self._move_data_folder)
        lay.addWidget(self.btn_move_data)

        # Recurring Tasks
        self.btn_recurring = QPushButton("Manage Recurring Tasks")
        self.btn_recurring.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_recurring.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};border-radius:6px;padding:6px;")
        self.btn_recurring.clicked.connect(self._open_recurring_manager)
        lay.addWidget(self.btn_recurring)

        # Habit Manager
        self.btn_habits = QPushButton("Manage Habits")
        self.btn_habits.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_habits.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};border-radius:6px;padding:6px;")
        self.btn_habits.clicked.connect(self._open_habit_manager)
        lay.addWidget(self.btn_habits)

        # Backup Manager
        self.btn_backups = QPushButton("Manage Backups")
        self.btn_backups.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_backups.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};border-radius:6px;padding:6px;")
        self.btn_backups.clicked.connect(self._open_backup_manager)
        lay.addWidget(self.btn_backups)

        # Sync Devices
        self.btn_sync_devices = QPushButton("Scan for Local Devices")
        self.btn_sync_devices.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_sync_devices.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};border-radius:6px;padding:6px;")
        self.btn_sync_devices.clicked.connect(self._open_sync_devices)
        lay.addWidget(self.btn_sync_devices)

        # Sync History
        self.btn_sync_history = QPushButton("View Sync History")
        self.btn_sync_history.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_sync_history.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};border-radius:6px;padding:6px;")
        self.btn_sync_history.clicked.connect(self._open_sync_history)
        lay.addWidget(self.btn_sync_history)

        # Export Data
        self.btn_export = QPushButton("Export Data")
        self.btn_export.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_export.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};border-radius:6px;padding:6px;")
        self.btn_export.clicked.connect(self._export_data)
        lay.addWidget(self.btn_export)

        # Import Data
        self.btn_import = QPushButton("Import Data")
        self.btn_import.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_import.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};border-radius:6px;padding:6px;")
        self.btn_import.clicked.connect(self._import_data)
        lay.addWidget(self.btn_import)

        # Save Button
        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_save.setStyleSheet(f"background:{GOLD};color:{DARK_BG};border-radius:6px;padding:8px;font-weight:bold;margin-top:10px;")
        self.btn_save.clicked.connect(self._close_settings)
        lay.addWidget(self.btn_save)

        # Reset Button
        self.btn_reset = QPushButton("Reset to Defaults")
        self.btn_reset.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_reset.setStyleSheet(f"background:transparent;color:{TEXT_GRAY};border:1px solid {TEXT_GRAY};border-radius:6px;padding:6px;margin-top:5px;")
        self.btn_reset.clicked.connect(self._reset_settings)
        lay.addWidget(self.btn_reset)

        lay.addStretch()

        # Version Label
        self.lbl_ver = QLabel(f"TaskFlow v{VERSION}")
        self.lbl_ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_ver.setStyleSheet(f"color:{TEXT_GRAY};font-size:12px;text-decoration:underline;")
        self.lbl_ver.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.lbl_ver.mousePressEvent = lambda e: self._show_whats_new()
        lay.addWidget(self.lbl_ver)

    def _move_data_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Cloud Folder (Dropbox, OneDrive, etc.)")
        if not folder: return
        
        if os.path.abspath(folder) == os.path.abspath(DATA_DIR): return

        confirm = QMessageBox.question(self, "Move Data", f"Move all data to:\n{folder}\n\nTaskFlow will restart.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm != QMessageBox.StandardButton.Yes: return
        
        self._save_now()
        
        try:
            # Copy files
            if os.path.exists(DATA_FILE):
                shutil.copy2(DATA_FILE, os.path.join(folder, "taskflow_data.json"))
            if os.path.exists(BACKUP_FILE):
                shutil.copy2(BACKUP_FILE, os.path.join(folder, "taskflow_data.backup.json"))
            
            # Update config
            with open(PATH_CONFIG, "w") as f:
                json.dump({"data_dir": folder}, f)
            
            self._show_overlay("Success", "Data moved. Restarting...", [])
            QTimer.singleShot(1500, self._restart_app)
            
        except Exception as e:
            self._show_overlay("Error", f"Failed to move data:\n{e}", [("OK", None, "secondary")])

    def _restart_app(self):
        self._force_quit()
        exe = sys.executable
        args = [exe] if getattr(sys, "frozen", False) else [exe, sys.argv[0]]
        subprocess.Popen(args)

    def _open_backup_manager(self):
        dlg = BackupManagerDialog(self)
        dlg.exec()

    def _open_recurring_manager(self):
        dlg = RecurringTasksDialog(self.state, self)
        dlg.exec()

    def _open_habit_manager(self):
        dlg = HabitManagerDialog(self.state, self)
        dlg.exec()

    def _open_sync_devices(self):
        dlg = DeviceSelectionDialog(self)
        res = dlg.exec()
        if res == 2: # Push Now
            self._broadcast_sync()
            self._show_overlay("Sync Started", "Pushing data to known devices...", [("OK", None, "primary")])
        elif res == QDialog.DialogCode.Accepted:
            ip, hostname = dlg.get_selected_device()
            if ip:
                devices = self.state.setdefault("sync_devices", [])
                # Check if already exists
                for d in devices:
                    if d["ip"] == ip:
                        return
                devices.append({"ip": ip, "hostname": hostname, "added_at": _now_iso()})
                self._schedule_save()
                self._show_overlay("Device Added", f"Added {hostname} ({ip})", [("OK", None, "primary")])

    def _open_sync_history(self):
        history = self.state.get("sync_history", [])
        dlg = SyncHistoryDialog(history, self)
        dlg.exec()

    def _show_sync_activity(self):
        self.btn_cloud.setStyleSheet(
            f"QPushButton{{color:{GOLD};background:transparent;border:none;font-size:18px;}}"
        )
        self._sync_timer.start(2000)

    def _hide_sync_activity(self):
        self.btn_cloud.setStyleSheet(
            f"QPushButton{{color:{TEXT_GRAY};background:transparent;border:none;font-size:18px;}}"
        )
        self._sync_timer.stop()

    def _broadcast_sync(self):
        devices = self.state.get("sync_devices", [])
        if not devices: return
        
        # Prepare clean state to send (exclude local UI state)
        sync_data = {
            "tasks": self.state.get("tasks", []),
            "notes": self.state.get("notes", {}),
            "sections": self.state.get("sections", []),
            "stats": self.state.get("stats", {}),
            "sender": socket.gethostname()
        }
        
        # Cleanup finished threads to prevent memory leak
        if hasattr(self, "_sync_senders"):
            self._sync_senders = [s for s in self._sync_senders if s.isRunning()]
        else:
            self._sync_senders = []

        for d in devices:
            sender = SyncSender(d["ip"], sync_data)
            self._sync_senders.append(sender)
            sender.start()
        self._show_sync_activity()

    def _on_sync_data_received(self, remote_data, sender_ip):
        self._show_sync_activity()
        # Merge Logic (Additive / Last Write Wins)
        changed = False
        changes_log = []
        
        # 1. Merge Tasks
        local_tasks = {t["id"]: t for t in self.state["tasks"]}
        tasks_added = 0
        tasks_updated = 0
        
        for r_task in remote_data.get("tasks", []):
            tid = r_task["id"]
            if tid not in local_tasks:
                self.state["tasks"].append(r_task)
                changed = True
                tasks_added += 1
            else:
                l_task = local_tasks[tid]
                # Compare updated_at strings (ISO format sorts correctly)
                if r_task.get("updated_at", "") > l_task.get("updated_at", ""):
                    # Update in place
                    l_task.update(r_task)
                    changed = True
                    tasks_updated += 1
                elif r_task.get("updated_at", "") == l_task.get("updated_at", ""):
                    # Conflict: Same time, check content
                    if r_task != l_task:
                        dlg = ConflictDialog(l_task, r_task, self)
                        if dlg.exec():
                            # User chose one
                            winner = dlg.chosen_task
                            winner["updated_at"] = _now_iso() # Bump time to resolve future conflicts
                            l_task.update(winner)
                            changed = True
                            tasks_updated += 1
        
        if tasks_added: changes_log.append(f"+{tasks_added} tasks")
        if tasks_updated: changes_log.append(f"~{tasks_updated} tasks")
        
        # 2. Merge Notes
        r_notes = remote_data.get("notes", {}).get("groups", {})
        l_groups = self.state["notes"]["groups"]
        notes_added = 0
        notes_updated = 0
        
        for gname, r_group_notes in r_notes.items():
            if gname not in l_groups:
                l_groups[gname] = []
                if gname not in self.state["notes"]["order"]:
                    self.state["notes"]["order"].append(gname)
                changed = True
            
            l_group_notes = {n["id"]: n for n in l_groups[gname]}
            for r_note in r_group_notes:
                nid = r_note["id"]
                if nid not in l_group_notes:
                    l_groups[gname].append(r_note)
                    changed = True
                    notes_added += 1
                else:
                    l_note = l_group_notes[nid]
                    if r_note.get("updated_at", "") > l_note.get("updated_at", ""):
                        l_note.update(r_note)
                        changed = True
                        notes_updated += 1

        if notes_added: changes_log.append(f"+{notes_added} notes")
        if notes_updated: changes_log.append(f"~{notes_updated} notes")

        # 3. Merge Sections
        sections_added = 0
        for sec in remote_data.get("sections", []):
            if sec not in self.state["sections"]:
                self.state["sections"].append(sec)
                changed = True
                sections_added += 1
        
        if sections_added: changes_log.append(f"+{sections_added} sections")

        if changed:
            # Create backup before saving new state (snapshot of the NEW state)
            backup_dir = os.path.join(DATA_DIR, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"sync_backup_{timestamp}.json"
            
            # Add to history
            details = ", ".join(changes_log) if changes_log else "Synced data"
            entry = {
                "timestamp": _now_iso(),
                "source": sender_ip,
                "details": details,
                "backup_file": backup_filename
            }
            self.state.setdefault("sync_history", []).insert(0, entry)
            
            # Cleanup old history and backups
            while len(self.state["sync_history"]) > 50:
                removed = self.state["sync_history"].pop()
                if "backup_file" in removed:
                    try: os.remove(os.path.join(backup_dir, removed["backup_file"]))
                    except: pass

            # Save backup
            try:
                with open(os.path.join(backup_dir, backup_filename), "w", encoding="utf-8") as f:
                    json.dump(self.state, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Backup failed: {e}")

            self._refresh_tasks_ui()
            self._refresh_notes_ui()
            self._schedule_save() # Save merged result

    def _restore_from_backup(self, filename):
        backup_dir = os.path.join(DATA_DIR, "backups")
        path = os.path.join(backup_dir, filename)
        
        if not os.path.exists(path):
            self._show_overlay("Error", "Backup file not found.", [("OK", None, "secondary")])
            return

        confirm = QMessageBox.question(
            self, "Restore State",
            "Are you sure you want to restore this state?\nCurrent data will be overwritten.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                self.state = data
                self._refresh_tasks_ui()
                self._refresh_notes_ui()
                self._refresh_calendar_tasks()
                self._update_streak_display()
                self._schedule_save()
                
                self._show_overlay("Restored", "State restored from history.", [("OK", None, "primary")])
            except Exception as e:
                self._show_overlay("Error", f"Failed to restore:\n{e}", [("OK", None, "secondary")])

    def _export_data(self):
        default_name = f"TaskFlow_Backup_{date.today()}.json"
        path, _ = QFileDialog.getSaveFileName(self, "Export Data", default_name, "JSON Files (*.json)")
        if path:
            try:
                shutil.copy2(DATA_FILE, path)
                self._show_overlay("Export Successful", f"Data saved to:\n{os.path.basename(path)}", [("OK", None, "primary")])
            except Exception as e:
                self._show_overlay("Export Failed", str(e), [("OK", None, "secondary")])

    def _import_data(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Data", "", "JSON Files (*.json)")
        if not path:
            return
            
        confirm = QMessageBox.question(
            self, "Import Data",
            "This will overwrite your current tasks and notes.\n\nA backup of your current data will be created.\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                # Backup current
                shutil.copy2(DATA_FILE, DATA_FILE + ".pre_import_backup")
                
                # Copy new
                shutil.copy2(path, DATA_FILE)
                
                # Reload
                self.state = load_state()
                self._refresh_tasks_ui()
                self._refresh_notes_ui()
                self._refresh_calendar_tasks()
                self._update_streak_display()
                
                self._show_overlay("Import Successful", "Data loaded successfully.", [("OK", None, "primary")])
                
            except Exception as e:
                self._show_overlay("Import Failed", str(e), [("OK", None, "secondary")])

    def _reset_settings(self):
        confirm = QMessageBox.question(self, "Reset Settings", "Are you sure you want to reset all settings to default?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.spin_zen.setValue(25)
            self.chk_collapse.setChecked(True)
            self.chk_snapping.setChecked(True)
            self.chk_hover_expand.setChecked(True)
            self.chk_compact.setChecked(False)
            self.chk_sound.setChecked(True)
            self.chk_startup.setChecked(False)
            self._show_overlay("Settings Reset", "Settings have been restored to defaults.", [("OK", None, "primary")])

    def _build_whats_new_page(self):
        lay = QVBoxLayout(self.page_whats_new)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(15)

        lbl_title = QLabel(f"Welcome to TaskFlow v{VERSION}!")
        lbl_title.setStyleSheet(f"color:{GOLD};font-size:18px;font-weight:bold;")
        lay.addWidget(lbl_title)
        
        self.wn_content = QTextEdit()
        self.wn_content.setReadOnly(True)
        self.wn_content.setHtml(WHATS_NEW_HTML)
        self.wn_content.setStyleSheet(f"border:none;background:{CARD_BG};border-radius:8px;padding:10px;font-size:14px;color:{TEXT_WHITE};")
        lay.addWidget(self.wn_content)
        
        self.chk_dont_show = QCheckBox("Don't show again until next update")
        self.chk_dont_show.setChecked(True)
        self.chk_dont_show.setStyleSheet(
            f"QCheckBox{{color:{TEXT_GRAY};}} QCheckBox::indicator{{border:1px solid {TEXT_GRAY};width:14px;height:14px;border-radius:3px;}} QCheckBox::indicator:checked{{background:{GOLD};border:1px solid {GOLD};}}"
        )
        lay.addWidget(self.chk_dont_show)
        
        btn = QPushButton("Let's Flow")
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.clicked.connect(self._close_whats_new)
        btn.setStyleSheet(f"background:{GOLD};color:{DARK_BG};border-radius:6px;padding:8px;font-weight:bold;")
        lay.addWidget(btn)

    def _open_stats(self):
        self._refresh_stats_ui()
        self.header_bar.setVisible(False)
        self.stack.setCurrentWidget(self.page_stats)
        self._animate_tab_transition(self.page_stats)

    def _close_stats(self):
        self.header_bar.setVisible(True)
        self._switch_tab(self.state.get("ui", {}).get("active_tab", "Tasks"))

    def _refresh_stats_ui(self):
        tasks = self.state.get("tasks", [])
        completed = [t for t in tasks if t.get("completed")]
        total = len(tasks)
        rate = int((len(completed) / total * 100)) if total > 0 else 0
        self.lbl_stats_summary.setText(
            f"<span style='color:{GOLD};font-size:24px;font-weight:bold;'>{len(completed)}</span> Tasks Completed<br>"
            f"<span style='color:{TEXT_WHITE};'>{rate}%</span> Completion Rate"
        )
        self.stats_graph.update()
        self.zen_chart.update()

    def _show_overlay(self, title, msg, buttons, content_widget=None):
        self.overlay.show_msg(title, msg, buttons, content_widget)

    def enter_zen_mode(self, task_id: str):
        self._zen_task_id = task_id
        # Set started_at if not set
        t = self._find_task(task_id)
        if t and not t.get("started_at"):
            t["started_at"] = _now_iso()
            self._schedule_save()
        self._populate_zen_view(task_id)
        self.header_bar.setVisible(False)
        self.stack.setCurrentWidget(self.page_zen)
        self._animate_tab_transition(self.page_zen)

        # If timer is running (e.g. re-entering), restart the pulse
        if self.zen_running:
            self._start_zen_pulse()

    def exit_zen_mode(self):
        if self.zen_running:
            self._toggle_zen_timer()
        self._zen_task_id = None
        self.header_bar.setVisible(True)
        self.stack.setCurrentWidget(self.page_tasks)
        self._animate_tab_transition(self.page_tasks)

    def _populate_zen_view(self, task_id: str):
        t = self._find_task(task_id)
        if not t:
            # Task might have been deleted or completed/archived externally
            self._zen_task_id = None
            self.exit_zen_mode()
            return
        
        self.zen_emoji.setText(t.get("emoji", "📝"))
        self.zen_text.setText(t.get("text", ""))

        # Update stats display
        sessions = self.state.get("zen_stats", {}).get("sessions", [])
        now = datetime.now()
        today_str = now.date().isoformat()
        week_start = now.date() - timedelta(days=now.weekday())
        
        mins_today = 0
        mins_week = 0
        
        for s in sessions:
            try:
                s_dt = datetime.fromisoformat(s["date"])
                s_date = s_dt.date()
                dur = s.get("duration", 0)
                
                if s_date.isoformat() == today_str:
                    mins_today += dur
                if s_date >= week_start:
                    mins_week += dur
            except: pass

        total_mins = self.state.get("zen_stats", {}).get("total_minutes", 0)
        self.lbl_zen_stats.setText(f"Today: {mins_today}m  •  Week: {mins_week}m  •  Total: {total_mins}m")
        
        # Clear subtasks
        while self.zen_subtasks_layout.count():
            item = self.zen_subtasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        subtasks = [st for st in self.state["tasks"] if st.get("parent_id") == task_id]
        subtasks.sort(key=lambda x: x.get("order", 0))
        
        for st in subtasks:
            sw = SubtaskWidget(st)
            sw.toggled.connect(self._toggle_task)
            # Larger font for zen mode
            style = f"color:{TEXT_GRAY if st.get('completed') else TEXT_WHITE};font-size:16px;"
            if st.get("completed"):
                style += "text-decoration:line-through;"
            sw.lbl.setStyleSheet(style)
            self.zen_subtasks_layout.addWidget(sw)

    def _toggle_zen_timer(self):
        if self.zen_running:
            self.zen_timer.stop()
            self.zen_running = False
            self._stop_zen_pulse()
            self.btn_timer_toggle.setText("▶ Start")
            self.btn_timer_toggle.setStyleSheet(
                f"QPushButton{{background:{HOVER_BG};color:{TEXT_WHITE};border-radius:20px;font-weight:bold;}}"
                f"QPushButton:hover{{background:{GOLD};color:{DARK_BG};}}"
            )
            # Pause logic: calculate remaining
            if self.zen_end_time:
                rem = (self.zen_end_time - datetime.now()).total_seconds()
                self.zen_remaining = max(0, int(rem))
        else:
            self.zen_timer.start(1000)
            self.zen_running = True
            self._prevent_sleep()
            self._start_zen_pulse()
            self.btn_timer_toggle.setText("⏸ Pause")
            self.btn_timer_toggle.setStyleSheet(
                f"QPushButton{{background:{GOLD};color:{DARK_BG};border-radius:20px;font-weight:bold;}}"
                f"QPushButton:hover{{background:#fcd34d;}}"
            )
            # Resume/Start logic
            self.zen_end_time = datetime.now() + timedelta(seconds=self.zen_remaining)
            self.zen_timer.start(100) # Faster tick for smoothness

    def _set_zen_duration(self, mins):
        if self.zen_running: return
        self.zen_remaining = mins * 60
        self._update_timer_display()

    def _reset_zen_timer(self):
        self.zen_timer.stop()
        self.zen_running = False
        self._allow_sleep()
        self._stop_zen_pulse()
        cfg_mins = self.state.get("config", {}).get("zen_duration", 25)
        self.zen_remaining = cfg_mins * 60
        self._update_timer_display()
        self.btn_timer_toggle.setText("▶ Start")
        self.btn_timer_toggle.setStyleSheet(
            f"QPushButton{{background:{HOVER_BG};color:{TEXT_WHITE};border-radius:20px;font-weight:bold;}}"
            f"QPushButton:hover{{background:{GOLD};color:{DARK_BG};}}"
        )

    def _update_zen_timer_tick(self):
        try:
            if not self.zen_running or not self.zen_end_time:
                return
                
            remaining = (self.zen_end_time - datetime.now()).total_seconds()
            
            if remaining > 0:
                self.zen_remaining = int(remaining)
                self._update_timer_display()
            else:
                self.zen_remaining = 0
                self._update_timer_display()
                self.zen_timer.stop()
                self.zen_running = False
                self._allow_sleep()
                self._stop_zen_pulse()
                self.btn_timer_toggle.setText("▶ Start")
                self.showNormal()
                self.activateWindow()
                
                # Play sound
                if self.state.get("config", {}).get("sound_enabled", True) and winsound:
                    try: winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
                    except: pass

                # Rewards & Stats
                duration = self.state.get("config", {}).get("zen_duration", 25)
                self._update_streak()
                
                # XP for Zen
                self._add_xp(int(duration))
                
                self.state["zen_stats"]["total_minutes"] += duration
                self.state["zen_stats"]["sessions"].append({
                    "date": _now_iso(),
                    "duration": duration,
                    "task_id": self._zen_task_id
                })
                self._schedule_save()
                
                self._show_overlay("Flow Complete", "Focus session finished!", [("Awesome", None, "primary")])
        except KeyboardInterrupt:
            self.zen_timer.stop()
            self._allow_sleep()
        except Exception:
            pass

    def _update_timer_display(self):
        m = self.zen_remaining // 60
        s = self.zen_remaining % 60
        self.lbl_timer.setText(f"{m:02}:{s:02}")

    def _start_zen_pulse(self):
        # Ensure clean state
        self._stop_zen_pulse()
        # Glow effect
        self._zen_pulse_effect = QGraphicsDropShadowEffect(self.lbl_timer)
        self._zen_pulse_effect.setBlurRadius(0)
        self._zen_pulse_effect.setColor(QColor(GOLD))
        self._zen_pulse_effect.setOffset(0, 0)
        self.lbl_timer.setGraphicsEffect(self._zen_pulse_effect)
        
        self._zen_pulse_anim = QPropertyAnimation(self._zen_pulse_effect, b"blurRadius")
        self._zen_pulse_anim.setDuration(1500)
        self._zen_pulse_anim.setStartValue(0)
        self._zen_pulse_anim.setEndValue(30)
        self._zen_pulse_anim.setLoopCount(-1)
        self._zen_pulse_anim.setEasingCurve(QEasingCurve.Type.SineCurve)
        self._zen_pulse_anim.start()

    def _stop_zen_pulse(self):
        if hasattr(self, "_zen_pulse_anim"):
            self._zen_pulse_anim.stop()
            self._zen_pulse_anim.deleteLater()
            del self._zen_pulse_anim
            
        if hasattr(self, "_zen_pulse_effect"):
            self.lbl_timer.setGraphicsEffect(None)
            try:
                self._zen_pulse_effect.deleteLater()
            except RuntimeError:
                # Object already deleted by C++
                pass
            del self._zen_pulse_effect

    def _prevent_sleep(self):
        if os.name == 'nt':
            try:
                # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001 | 0x00000002)
            except: pass

    def _allow_sleep(self):
        if os.name == 'nt':
            try:
                # ES_CONTINUOUS
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            except: pass

    def _is_startup_enabled(self):
        if not winreg: return False
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except:
            return False

    def _set_startup(self, enabled: bool):
        if not winreg: return
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            if enabled:
                exe = sys.executable
                if getattr(sys, "frozen", False):
                    cmd = f'"{exe}"'
                else:
                    script = os.path.abspath(sys.argv[0])
                    cmd = f'"{exe}" "{script}"'
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            self._show_overlay("Settings Error", f"Could not change startup setting:\n{e}", [("OK", None, "secondary")])
            # Revert checkbox to reflect reality
            self.chk_startup.setChecked(self._is_startup_enabled())
            print(f"Startup registry error: {e}")

    def _create_section_item(self, name: str):
        blk = SectionBlock(name)
        blk.list.taskMoved.connect(self._on_task_moved)
        blk.list.itemSelectionChanged.connect(self._on_selection_changed)
        blk.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        blk.list.customContextMenuRequested.connect(lambda pos, sec=name: self._open_task_menu(sec, pos))
        
        blk.renameRequested.connect(self._rename_section)
        blk.deleteRequested.connect(self._delete_section)
        blk.clearCompletedRequested.connect(self._clear_completed_in_section)
        blk.collapsedChanged.connect(lambda c, n=name: self._on_section_collapsed(n, c))
        
        item = QListWidgetItem()
        item.setSizeHint(blk.sizeHint())
        
        # Connect resize
        blk.requestResize.connect(lambda: item.setSizeHint(blk.sizeHint()))
        
        self.section_blocks[name] = blk
        return item, blk

    def _on_section_collapsed(self, name: str, collapsed: bool):
        self.state["ui"].setdefault("section_states", {})
        self.state["ui"]["section_states"][name] = {"collapsed": collapsed}
        self._schedule_save()

    def _open_board_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};}}"
            f"QMenu::item{{padding:8px 22px;}}"
            f"QMenu::item:selected{{background:{HOVER_BG};}}"
            f"QMenu::separator{{background:{HOVER_BG};height:1px;margin:4px 0px;}}"
        )
        act_sort = menu.addAction("Sort All by Priority")
        act_archive = menu.addAction("Archive Completed Tasks")
        act_clear_all = menu.addAction("Clear All Completed")
        menu.addSeparator()
        act_collapse = menu.addAction("Collapse All")
        act_expand = menu.addAction("Expand All")
        menu.addSeparator()
        act_add = menu.addAction("Add section")
        chosen = menu.exec(self.board_list.mapToGlobal(pos))
        if chosen == act_add:
            self._add_custom_section()
        elif chosen == act_sort:
            self._sort_all_sections()
        elif chosen == act_archive:
            self._archive_completed()
        elif chosen == act_clear_all:
            for sec in self.state["sections"]:
                self._clear_completed_in_section(sec)
            self._clear_completed_in_section("Scheduled")
        elif chosen == act_collapse:
            for blk in self.section_blocks.values():
                if not blk.collapsed: blk.toggle_collapse()
        elif chosen == act_expand:
            for blk in self.section_blocks.values():
                if blk.collapsed: blk.toggle_collapse()

    def _add_custom_section(self):
        name, ok = QInputDialog.getText(self, "New Section", "Section name:")
        if ok and name.strip():
            name = name.strip()
            if name not in self.state["sections"]:
                self.state["sections"].append(name)
                self._schedule_save()
                self._refresh_tasks_ui()

    def _rename_section(self, old_name: str):
        new_name, ok = QInputDialog.getText(self, "Rename Section", "New name:", text=old_name)
        if ok and new_name.strip() and new_name != old_name:
            new_name = new_name.strip()
            if new_name in self.state["sections"]:
                return
            
            # Update state
            idx = self.state["sections"].index(old_name)
            self.state["sections"][idx] = new_name
            
            for t in self.state["tasks"]:
                if t.get("section") == old_name:
                    t["section"] = new_name
            
            self._schedule_save()
            self._refresh_tasks_ui()

    def _delete_section(self, name: str):
        if name in ("Today", "Scheduled"):
            self._show_overlay("Error", f"Cannot delete '{name}'.", [("OK", None, "secondary")])
            return
        
        # Move tasks to Today
        for t in self.state["tasks"]:
            if t.get("section") == name:
                t["section"] = "Today"
        
        if name in self.state["sections"]:
            self.state["sections"].remove(name)
        
        self._schedule_save()
        self._refresh_tasks_ui()

    def _clear_completed_in_section(self, section_name: str):
        tasks_to_remove = []
        
        # If it's the virtual "Scheduled" section, we need to be careful
        # But _tasks_in_section handles the logic of what is "in" it.
        # However, deleting from "Scheduled" might delete from "Today" if it appears in both.
        # That is usually desired behavior (clearing completed tasks).
        
        # We iterate all tasks and check if they belong to the section AND are completed
        # Using _tasks_in_section logic might be complex for deletion, simpler to check state directly
        # But for "Scheduled", we rely on the same logic.
        
        # Simpler approach: Filter self.state["tasks"]
        # If section is "Scheduled", remove completed tasks that have due_date or section=Scheduled
        # If section is normal, remove completed tasks with section=NAME
        
        initial_count = len(self.state["tasks"])
        
        if section_name == "Scheduled":
            self.state["tasks"] = [
                t for t in self.state["tasks"] 
                if not (t.get("completed") and (t.get("due_date") or t.get("section") == "Scheduled"))
            ]
        else:
            self.state["tasks"] = [
                t for t in self.state["tasks"] 
                if not (t.get("completed") and t.get("section") == section_name)
            ]
            
        removed_count = initial_count - len(self.state["tasks"])
        
        if removed_count > 0:
            self._schedule_save()
            self._refresh_tasks_ui()
            self._show_overlay("Cleared", f"Removed {removed_count} completed tasks.", [("OK", None, "primary")])
        else:
            self._show_overlay("Info", "No completed tasks found in this section.", [("OK", None, "secondary")])

    def _on_section_reordered(self):
        new_order = []
        for i in range(self.board_list.count()):
            item = self.board_list.item(i)
            w = self.board_list.itemWidget(item)
            if isinstance(w, SectionBlock):
                new_order.append(w.name)
        
        if new_order:
            if "Scheduled" not in new_order:
                new_order.append("Scheduled")
            self.state["sections"] = new_order
            self._schedule_save()

    def _build_notes_page(self):
        lay = QVBoxLayout(self.page_notes)
        lay.setContentsMargins(14, 0, 14, 12)
        lay.setSpacing(10)

        top = QHBoxLayout()
        top.setAlignment(Qt.AlignmentFlag.AlignVCenter) # Fix alignment of delete button
        self.note_group = QComboBox()
        self.note_group.setStyleSheet(
            f"QComboBox{{background:{CARD_BG};color:{TEXT_WHITE};border:none;border-radius:10px;padding:8px;}}"
        )
        self.note_group.currentTextChanged.connect(self._notes_group_changed)

        self.btn_add_group = QPushButton("+")
        self.btn_add_group.setFixedSize(30, 30)
        self.btn_add_group.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_add_group.setStyleSheet(
            f"QPushButton{{background:{CARD_BG};color:{GOLD};border:none;border-radius:10px;font-weight:900;}}"
            f"QPushButton:hover{{background:{HOVER_BG};}}"
        )
        self.btn_add_group.clicked.connect(self._add_note_group)

        self.btn_del_group = QPushButton("−")
        self.btn_del_group.setFixedSize(30, 30)
        self.btn_del_group.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_del_group.setStyleSheet(
            f"QPushButton{{background:{CARD_BG};color:{TEXT_GRAY};border:none;border-radius:10px;font-weight:900;}}"
            f"QPushButton:hover{{background:#3a2a2a;color:{TEXT_WHITE};}}"
        )
        self.btn_del_group.clicked.connect(self._delete_note_group)

        self.btn_new_note = QPushButton("New")
        self.btn_new_note.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_new_note.setStyleSheet(
            f"QPushButton{{background:{GOLD};color:{DARK_BG};border:none;border-radius:10px;padding:6px 12px;font-weight:900;}}"
            f"QPushButton:hover{{background:#fcd34d;}}"
        )
        self.btn_new_note.clicked.connect(self._new_note)

        top.addWidget(self.note_group, 1)
        top.addWidget(self.btn_add_group)
        top.addWidget(self.btn_del_group)
        top.addWidget(self.btn_new_note)
        lay.addLayout(top)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setStyleSheet("QSplitter::handle{background:transparent;}")
        lay.addWidget(splitter, 1)

        self.note_list = QListWidget()
        self.note_list.setStyleSheet(
            f"QListWidget{{background:transparent;border:none;color:{TEXT_WHITE};}}"
            f"QListWidget::item{{padding:8px;}}"
            f"QListWidget::item:selected{{background:{HOVER_BG};border-radius:10px;}}"
        )
        self.note_list.itemSelectionChanged.connect(self._note_selected)
        self.note_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.note_list.customContextMenuRequested.connect(self._open_note_menu)
        splitter.addWidget(self.note_list)

        self.note_editor = QTextEdit()
        self.note_editor.setPlaceholderText("Write…")
        self.note_editor.setStyleSheet(
            f"QTextEdit{{background:{CARD_BG};color:{TEXT_WHITE};border:none;border-radius:12px;padding:10px;}}"
        )
        self.note_editor.textChanged.connect(self._note_edited)
        self.note_editor.installEventFilter(self)
        splitter.addWidget(self.note_editor)

        splitter.setSizes([300, 520])
        self._refresh_notes_ui()

    def _wire_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Shift+T"), self, self.toggle_collapse)
        QShortcut(QKeySequence("Ctrl+N"), self, self._focus_add)
        QShortcut(QKeySequence("Ctrl+Q"), self, self._quit)
        QShortcut(QKeySequence("Ctrl+W"), self, self.toggle_collapse)
        QShortcut(QKeySequence("Ctrl+F"), self, self._toggle_search)

        # Refined: Esc only collapses/expands when NOT typing.
        QShortcut(QKeySequence("Esc"), self, self._esc_behavior)

        # Refined: list shortcuts should not fire while typing.
        QShortcut(QKeySequence("Space"), self, self._toggle_selected_task)
        QShortcut(QKeySequence("Delete"), self, self._delete_selected_any)
        QShortcut(QKeySequence("Alt+Up"), self, lambda: self._move_selected_task(-1))
        QShortcut(QKeySequence("Alt+Down"), self, lambda: self._move_selected_task(1))
        
        QShortcut(QKeySequence("Ctrl+D"), self, self._toggle_selected_task)
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self._switch_tab("Tasks"))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self._switch_tab("Notes"))
        QShortcut(QKeySequence("Ctrl+3"), self, lambda: self._switch_tab("Calendar"))

    def _esc_behavior(self):
        if self._focus_is_text_entry():
            # If search is focused, toggle it off
            if self.search_input.hasFocus():
                self._toggle_search()
            return
        self.toggle_collapse()

    def _toggle_search(self):
        is_searching = self.search_group.isVisible()
        if is_searching:
            # Close search
            self.search_group.setVisible(False)
            self.nav_group.setVisible(True)
            self.search_input.clear() # Clears filter
            self.btn_search.setText("🔍")
        else:
            # Open search
            self.nav_group.setVisible(False)
            self.search_group.setVisible(True)
            self.search_input.setFocus()
            self.btn_search.setText("×")

    def _perform_search(self, text):
        text = text.lower().strip()
        
        # Filter Tasks
        for blk in self.section_blocks.values():
            lst = blk.list
            for i in range(lst.count()):
                item = lst.item(i)
                widget = lst.itemWidget(item)
                match = text in widget.task['text'].lower() or text in (widget.task.get('note') or "").lower()
                item.setHidden(not match)
            blk.list.update_height()
        self.board_list.doItemsLayout()
            
        # Filter Notes
        for i in range(self.note_list.count()):
            item = self.note_list.item(i)
            nid = item.data(Qt.ItemDataRole.UserRole)
            n = self._find_note(nid)
            content = n.get("content", "") if n else ""
            
            match = text in item.text().lower() or text in content.lower()
            item.setHidden(not match)

    # ---------- Auto-collapse ----------
    def _mark_busy(self, ms: int):
        self._busy_until = int(datetime.now().timestamp() * 1000) + ms

    def _is_busy(self) -> bool:
        return int(datetime.now().timestamp() * 1000) < self._busy_until

    def _schedule_autocollapse(self):
        # Always start timer; _auto_collapse_if_needed handles busy check/reschedule
        self._auto_timer.start(AUTO_COLLAPSE_DELAY_MS)

    def _auto_collapse_if_needed(self):
        if self._is_busy():
            self._auto_timer.start(AUTO_COLLAPSE_DELAY_MS)
            return
        if not self.state.get("config", {}).get("auto_collapse", True):
            return
        if QApplication.activePopupWidget():
            return
        if not self.underMouse() and not self.isActiveWindow():
            if not self.state.get("ui", {}).get("collapsed", False):
                self.toggle_collapse()

    # ---------- Geometry ----------
    def _remember_expanded_geom(self):
        if self.state.get("ui", {}).get("collapsed", False):
            return
        self._last_expanded_geom = self.geometry()

    def _clamp_to_screen(self):
        scr = self.screen().availableGeometry()
        g = self.geometry()
        x = max(scr.left(), min(g.x(), scr.right() - g.width()))
        y = max(scr.top(), min(g.y(), scr.bottom() - g.height()))
        self.move(x, y)

    def _collapse_side(self) -> str:
        scr = self.screen().availableGeometry()
        g = self._last_expanded_geom or self.geometry()
        center_x = g.x() + g.width() / 2
        return "left" if center_x < (scr.x() + scr.width() / 2) else "right"

    def _collapsed_geometry(self) -> QRect:
        scr = self.screen().availableGeometry()
        g = self._last_expanded_geom or self.geometry()
        y = max(scr.top(), min(g.y(), scr.bottom() - PILL_HEIGHT))
        side = self._collapse_side()

        if side == "left":
            x = scr.left()
        else:
            x = scr.right() - COLLAPSED_WIDTH

        return QRect(int(x), int(y), COLLAPSED_WIDTH, PILL_HEIGHT)

    def _expanded_geometry(self) -> QRect:
        scr = self.screen().availableGeometry()
        if self._last_expanded_geom is None:
            x = scr.right() - WIN_W + 10
            y = scr.top() + 50
            return QRect(int(x), int(y), WIN_W, WIN_H)

        g = self._last_expanded_geom
        x = max(scr.left(), min(g.x(), scr.right() - WIN_W))
        y = max(scr.top(), min(g.y(), scr.bottom() - WIN_H))
        return QRect(int(x), int(y), WIN_W, WIN_H)

    def _snap(self, target: QRect, animated: bool = True):
        if not animated:
            self.setGeometry(target)
            return
        self.geom_anim = QPropertyAnimation(self, b"geometry")
        self.geom_anim.setDuration(260)
        self.geom_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.geom_anim.setStartValue(self.geometry())
        self.geom_anim.setEndValue(target)
        self.geom_anim.start()

    # ---------- Tasks ----------
    def _tasks_in_section(self, section: str):
        if section == "Scheduled":
            # Virtual section: All tasks with a due_date OR explicitly in Scheduled section
            ts = [t for t in self.state["tasks"] if t.get("due_date") or t.get("section") == "Scheduled"]
            
            def sort_key(x):
                d = x.get("due_date") or "9999-99-99"
                t = x.get("due_time") or ""
                return (d, t, x.get("text", ""))
            
            ts.sort(key=sort_key)
            return ts

        ts = [t for t in self.state["tasks"] if t.get("section") == section]
        ts.sort(key=lambda x: (x.get("order", 0), x.get("created_at", "")))
        return ts

    def _refresh_tasks_ui(self):
        if getattr(self, "section_blocks", None) is None or getattr(self, "scheduled_container", None) is None:
            return

        if getattr(self, "board_list", None):
            board_scroll_pos = self.board_list.verticalScrollBar().value()
        else:
            board_scroll_pos = 0

        # Refinement: preserve selection + scroll + expansion positions per section.
        preserve = {}
        saved_states = self.state.get("ui", {}).get("section_states", {})
        
        # Capture expanded tasks
        expanded_tasks = set()
        for blk in self.section_blocks.values():
            lst = blk.list
            for i in range(lst.count()):
                w = lst.itemWidget(lst.item(i))
                if isinstance(w, TaskRow) and w.expanded:
                    expanded_tasks.add(w.task["id"])

        # Pre-fetch project info
        proj_map = {p["id"]: p for p in self.state.get("projects", [])}

        current_board_index = 0
        for sec in self.state["sections"]:
            if sec in self.section_blocks:
                blk = self.section_blocks[sec]
                lst = blk.list
                sel = lst.currentItem().data(Qt.ItemDataRole.UserRole) if lst.currentItem() else None
                preserve[sec] = {
                    "selected": sel,
                    "collapsed": blk.collapsed
                }

        # We need to clear board_list to re-order, but we can try to reuse blocks?
        # For simplicity and to fix the flicker, we will reuse blocks if they exist.
        # But board_list.clear() destroys them.
        # We will NOT clear board_list. We will remove items that shouldn't be there and add new ones.
        
        # Handle Scheduled Section (Special Box)
        if "Scheduled" not in self.section_blocks:
            blk = SectionBlock("Scheduled")
            blk.list.taskMoved.connect(self._on_task_moved)
            blk.list.itemSelectionChanged.connect(self._on_selection_changed)
            blk.list.customContextMenuRequested.connect(lambda pos: self._open_task_menu("Scheduled", pos))
            
            blk.renameRequested.connect(self._rename_section)
            blk.deleteRequested.connect(self._delete_section)
            blk.clearCompletedRequested.connect(self._clear_completed_in_section)
            blk.collapsedChanged.connect(lambda c, n="Scheduled": self._on_section_collapsed(n, c))

            # Custom styling for Scheduled
            blk.header.setStyleSheet("background:transparent;")
            blk.lbl.setStyleSheet(f"color:{GOLD};font-size:14px;font-weight:bold;text-transform:uppercase;")
            self.scheduled_layout.addWidget(blk)
            self.section_blocks["Scheduled"] = blk
        
        # Update Scheduled Content
        self._update_section_block("Scheduled", expanded_tasks, proj_map)
        
        # Hide Scheduled container if empty to keep UI clean
        scheduled_tasks = self._tasks_in_section("Scheduled")
        self.scheduled_container.setVisible(len(scheduled_tasks) > 0)

        # Empty State Logic
        has_tasks = len(self.state["tasks"]) > 0
        if hasattr(self, "empty_state_lbl"):
            self.empty_state_lbl.setVisible(not has_tasks)
            self.board_list.setVisible(has_tasks)

        for sec in self.state["sections"]:
            if sec == "Scheduled": continue # Handled separately
            
            # Ensure block exists
            if sec not in self.section_blocks:
                item, blk = self._create_section_item(sec)
                self.board_list.insertItem(current_board_index, item)
                self.board_list.setItemWidget(item, blk)
            else:
                blk = self.section_blocks[sec]
                # Ensure it is at the correct index in board_list
                found_at = -1  
                for i in range(self.board_list.count()):
                    it = self.board_list.item(i)
                    if self.board_list.itemWidget(it) == blk:
                        found_at = i
                        break
                
                if found_at != -1 and found_at != current_board_index:
                    # Move to correct position
                    it = self.board_list.takeItem(found_at)
                    self.board_list.insertItem(current_board_index, it)
                    self.board_list.setItemWidget(it, blk)
                elif found_at == -1:
                    # Should exist but not in list? Re-add
                    item, _ = self._create_section_item(sec) # Re-create item wrapper
                    self.section_blocks[sec] = blk # Keep block ref
                    self.board_list.insertItem(current_board_index, item)
                    self.board_list.setItemWidget(item, blk)
            
            self._update_section_block(sec, expanded_tasks, proj_map)
            saved = preserve.get(sec, {})
            if saved.get("collapsed", False):
                blk.collapsed = True
                blk.list.setVisible(False)
                blk.btn_arrow.setText("▶")
                # item.setSizeHint(blk.sizeHint()) # Need item ref

            # Restore selection
            if saved.get("selected"):
                for i in range(blk.list.count()):
                    it = blk.list.item(i)
                    if it.data(Qt.ItemDataRole.UserRole) == saved["selected"]:
                        blk.list.setCurrentItem(it)
                        break
            
            current_board_index += 1

        # Cleanup removed sections
        active_sections = set(self.state["sections"])
        active_sections.add("Scheduled")
        
        to_remove = [name for name in self.section_blocks if name not in active_sections]
        
        for name in to_remove:
            blk = self.section_blocks.pop(name)
            # Find and remove from board_list
            for i in range(self.board_list.count()):
                it = self.board_list.item(i)
                if self.board_list.itemWidget(it) == blk:
                    self.board_list.takeItem(i)
                    break
            blk.deleteLater()

        if getattr(self, "board_list", None):
            self.board_list.verticalScrollBar().setValue(board_scroll_pos)

    def _update_section_block(self, sec, expanded_tasks, proj_map):
        blk = self.section_blocks[sec]
        tasks = self._tasks_in_section(sec)
        
        # Update progress
        completed = len([t for t in tasks if t.get("completed")])
        blk.update_progress(len(tasks), completed)

        # Save scroll position to prevent jumping
        scroll_pos = blk.list.verticalScrollBar().value()

        lst = blk.list
        lst.blockSignals(True)
        lst.clear()
        
        # Prevent visual flashing by disabling updates during rebuild
        lst.setUpdatesEnabled(False)
        try:
            # Separate top-level tasks and subtasks
            top_level = [t for t in tasks if not t.get("parent_id")]
            subtasks_map = {}
            for t in tasks:
                if t.get("parent_id"):
                    subtasks_map.setdefault(t["parent_id"], []).append(t)

            top_index = {t["id"]: i + 1 for i, t in enumerate(top_level)}

            for t in top_level:
                num = f"{top_index.get(t['id'], 0)}."
                t_item = QListWidgetItem()
                t_item.setData(Qt.ItemDataRole.UserRole, t["id"])

                subs = subtasks_map.get(t["id"], [])
                p_info = proj_map.get(t.get("project_id"))
                row = TaskRow(t, subs, num, project_info=p_info)
                row.toggled.connect(self._toggle_task)
                row.subtaskToggled.connect(self._toggle_task)
                row.subtaskEdited.connect(self._edit_subtask)
                row.resized.connect(lambda: self._on_task_resize(lst, t_item, row))
                row.focusRequested.connect(self.enter_zen_mode)
                row.addStepRequested.connect(self._add_step)
                row.menuRequested.connect(lambda pos, s=sec: self._open_task_menu(s, pos))
                row.projectClicked.connect(lambda pid: (
                    self._switch_tab("Projects"),
                    self._show_project_detail(pid)
                ))
                
                if t["id"] in expanded_tasks:
                    row.setExpanded(True)

                t_item.setSizeHint(row.sizeHint())
                lst.addItem(t_item)
                lst.setItemWidget(t_item, row)
            
            lst.update_height()
            # If in board_list, update item size
            if sec != "Scheduled":
                # Find item in board_list
                for i in range(self.board_list.count()):
                    it = self.board_list.item(i)
                    if self.board_list.itemWidget(it) == blk:
                        it.setSizeHint(blk.sizeHint())
                        break
        finally:
            lst.blockSignals(False)
            lst.setUpdatesEnabled(True)
            # Restore scroll position
            blk.list.verticalScrollBar().setValue(scroll_pos)

    def _on_task_resize(self, lst, item, widget):
        item.setSizeHint(widget.sizeHint())
        lst.update_height()

    def _get_task_row(self, task_id):
        for blk in self.section_blocks.values():
            lst = blk.list
            for i in range(lst.count()):
                item = lst.item(i)
                w = lst.itemWidget(item)
                if isinstance(w, TaskRow) and w.task["id"] == task_id:
                    return w
        return None

    def _find_task(self, task_id: str):
        for t in self.state["tasks"]:
            if t.get("id") == task_id:
                return t
        return None

    def _parse_task_input(self, text: str):
        text = text.strip()
        section = "Today"
        emoji = "📝"
        project_id = None
        due_date = None
        due_time = None
        note = ""

        # Quick Note detection (e.g. "Task > Note content")
        if ">" in text:
            parts = text.split(">", 1)
            text = parts[0].strip()
            note = parts[1].strip()

        # Priority detection
        if re.search(r'\b(important|urgent)\b', text, re.IGNORECASE):
            emoji = "🔥"
            text = re.sub(r'\b(important|urgent)\b', '', text, flags=re.IGNORECASE)
        
        if re.search(r'\bstar\b', text, re.IGNORECASE):
            emoji = "⭐"
            text = re.sub(r'\bstar\b', '', text, flags=re.IGNORECASE)
        
        if text.endswith("!"):
            emoji = "🔥"
            text = text.rstrip("!")

        # Section detection
        if re.search(r'\btoday\b', text, re.IGNORECASE):
            section = "Today"
            text = re.sub(r'\btoday\b', '', text, flags=re.IGNORECASE)
        elif re.search(r'\btomorrow\b', text, re.IGNORECASE):
            section = "Tomorrow"
            text = re.sub(r'\btomorrow\b', '', text, flags=re.IGNORECASE)
        elif re.search(r'\b(later|someday)\b', text, re.IGNORECASE):
            section = "Someday"
            text = re.sub(r'\b(later|someday)\b', '', text, flags=re.IGNORECASE)

        # Project detection (+ProjectName)
        if "+" in text:
            sorted_projects = sorted(self.state.get("projects", []), key=lambda p: len(p["name"]), reverse=True)
            for p in sorted_projects:
                # Check for +Name (case insensitive)
                pattern = re.compile(r'\+' + re.escape(p["name"]), re.IGNORECASE)
                if pattern.search(text):
                    project_id = p["id"]
                    text = pattern.sub("", text)
                    break

        # "Next week" detection (Schedules for next Monday)
        if re.search(r'\bnext week\b', text, re.IGNORECASE):
            today = date.today()
            days_ahead = (0 - today.weekday() + 7) % 7
            if days_ahead == 0: days_ahead = 7
            due_date = (today + timedelta(days=days_ahead)).isoformat()
            section = "Scheduled"
            text = re.sub(r'\bnext week\b', '', text, flags=re.IGNORECASE)

        # Weekday detection (e.g. "on Friday")
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        short_weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        
        lower_text = text.lower()
        for i, day in enumerate(weekdays):
            # Check for full name or short name, optionally preceded by "on "
            pattern = r'\b(?:on\s+)?(' + day + r'|' + short_weekdays[i] + r')\b'
            match = re.search(pattern, lower_text)
            if match:
                today = date.today()
                days_ahead = (i - today.weekday() + 7) % 7
                if days_ahead == 0: days_ahead = 7
                due_date = (today + timedelta(days=days_ahead)).isoformat()
                section = "Scheduled"
                
                # Remove from text (case insensitive)
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
                break

        # Time detection (e.g. "at 5pm", "17:00")
        # Match 12h (5pm, 5:30pm) or 24h (17:00)
        time_pattern = r'\b(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b'
        time_match = re.search(time_pattern, text, re.IGNORECASE)
        if time_match:
            h_str, m_str, ampm = time_match.groups()
            try:
                h = int(h_str)
                m = int(m_str) if m_str else 0
                
                if ampm:
                    ampm = ampm.lower()
                    if ampm == "pm" and h < 12: h += 12
                    if ampm == "am" and h == 12: h = 0
                
                if 0 <= h <= 23 and 0 <= m <= 59:
                    due_time = f"{h:02}:{m:02}"
                    if not due_date:
                        due_date = _today_str() # Default to today if time set but no date
                    section = "Scheduled"
                    text = re.sub(time_pattern, '', text, flags=re.IGNORECASE)
            except: pass

        # Time of day keywords
        time_keywords = {
            "morning": "09:00",
            "afternoon": "14:00",
            "evening": "18:00",
            "tonight": "20:00",
            "noon": "12:00"
        }
        for kw, time_val in time_keywords.items():
            pattern = r'\b(?:in the |at )?' + kw + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                due_time = time_val
                if not due_date: due_date = _today_str()
                section = "Scheduled"
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
                break

        # Cleanup whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text, section, emoji, project_id, due_date, due_time, note

    def _update_input_feedback(self, text):
        if not text:
            self.input_feedback.setFixedHeight(0)
            return
            
        _, section, emoji, project_id, due_date, due_time, note = self._parse_task_input(text)
        parts = []
        if section != "Today": parts.append(f"📅 {section}")
        if due_date: parts.append(f"📅 {due_date}")
        if due_time: parts.append(f"⏰ {due_time}")
        if emoji != "📝": parts.append(f"{emoji} Priority")
        if project_id:
            p = next((x for x in self.state["projects"] if x["id"] == project_id), None)
            if p: parts.append(f"📂 {p['name']}")
        if note: parts.append("📝 Note")
            
        if parts:
            self.input_feedback.setText("  ".join(parts))
            self.input_feedback.setFixedHeight(20)
        else:
            self.input_feedback.setFixedHeight(0)

    def _create_task(self, text: str, section: str, emoji: str, recur: str = "", parent_id=None, project_id=None, note: str = "", due_date: str = None, due_time: str = None):
        text = (text or "").strip()
        if not text:
            return
        if section not in self.state["sections"]:
            section = "Today"
        existing = self._tasks_in_section(section)
        max_order = max([t.get("order", 0) for t in existing], default=0)

        if due_date is None:
            due_date = _today_str() if section == "Scheduled" else None

        task_id = str(uuid.uuid4())
        self.state["tasks"].append({
            "id": task_id,
            "text": text[:500],
            "emoji": emoji or "📝",
            "completed": False,
            "section": section,
            "order": max_order + 10,
            "note": note,
            "recur": recur or "",
            "parent_id": parent_id,
            "linked_note_id": None,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "due_date": due_date,
            "due_time": due_time,
            "project_id": project_id,
        })
        return task_id

    def _toggle_task(self, task_id: str):
        if self._focus_is_text_entry():
            return
        t = self._find_task(task_id)
        if not t:
            return

        is_completing = not bool(t.get("completed"))

        # Update state immediately
        t["completed"] = is_completing
        t["updated_at"] = _now_iso()

        if is_completing:
            row = self._get_task_row(task_id)
            if row:
                # Animate out, then run post-completion logic
                self._animate_task_out_and_finalize(row, task_id)
            else:
                # Not visible, just run post-completion logic
                self._post_completion_logic(task_id)
        else:
            # Un-completing, just save and refresh
            self._schedule_save()
            self._refresh_tasks_ui()
            self._refresh_calendar_tasks()

    def _animate_task_out_and_finalize(self, row, task_id):
        group = QParallelAnimationGroup(self)
        
        op_anim = QPropertyAnimation(row, b"opacity_prop")
        op_anim.setEndValue(0.0)
        op_anim.setDuration(200)
        op_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        
        size_anim = QPropertyAnimation(row, b"maximumHeight")
        size_anim.setStartValue(row.height())
        size_anim.setEndValue(0)
        size_anim.setDuration(250)
        size_anim.setEasingCurve(QEasingCurve.Type.InCubic)

        group.addAnimation(op_anim)
        group.addAnimation(size_anim)
        group.finished.connect(lambda: self._post_completion_logic(task_id))
        group.finished.connect(row.hide)
        group.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _post_completion_logic(self, task_id):
        t = self._find_task(task_id)
        if not t or not t.get("completed"): return

        if t.get("recur"):
            freq = t.get("recur")
            next_date = None
            if t.get("due_date"):
                try:
                    curr = date.fromisoformat(t["due_date"])
                    if freq == "Daily": next_date = (curr + timedelta(days=1)).isoformat()
                    elif freq == "Weekly": next_date = (curr + timedelta(weeks=1)).isoformat()
                    elif freq == "Monthly":
                        y, m = curr.year, curr.month
                        m += 1
                        if m > 12: m, y = 1, y + 1
                        d = min(curr.day, calendar.monthrange(y, m)[1])
                        next_date = date(y, m, d).isoformat()
                except: pass
            next_section = "Tomorrow" if freq == "Daily" else ("This Week" if freq == "Weekly" else "Someday")
            if next_date: next_section = "Scheduled"
            self._create_task(text=t.get("text", ""), section=next_section, emoji=t.get("emoji", "📝"), recur=freq, project_id=t.get("project_id"), due_date=next_date)
        
        xp = 10
        if "🔥" in t.get("emoji", ""): xp += 10
        elif "⭐" in t.get("emoji", ""): xp += 5
        self._add_xp(xp)

        if t.get("estimated_duration") and t.get("started_at"):
            try:
                start = datetime.fromisoformat(t["started_at"])
                end = datetime.now()
                duration_mins = (end - start).total_seconds() / 60
                est = t["estimated_duration"]
                if duration_mins < (est / 2):
                    self._show_overlay("Incredible Flow!", f"You crushed it!\nEstimated: {est}m\nActual: {int(duration_mins)}m", [("I am Speed", None, "primary")])
                    self.confetti.burst()
            except: pass
        
        self._update_streak()
        self._schedule_save()
        self._refresh_tasks_ui()
        self._refresh_calendar_tasks()

        if self._zen_task_id:
            self._populate_zen_view(self._zen_task_id)
        
        # Confetti is now triggered after the refresh to feel more responsive
        self.confetti.burst()

    def _on_task_moved(self, task_id: str, new_section: str, new_index: int):
        t = self._find_task(task_id)
        if not t:
            return

        old_section = t.get("section")

        # Get the list of IDs in the destination section, correctly ordered
        dest_tasks = self._tasks_in_section(new_section)
        dest_ids = [task['id'] for task in dest_tasks]

        # If the task was already in this section, remove it from its old position
        if task_id in dest_ids:
            dest_ids.remove(task_id)

        # Insert the task at the new index
        dest_ids.insert(new_index, task_id)

        # Update the order for all tasks in the destination section
        for i, tid in enumerate(dest_ids):
            task = self._find_task(tid)
            if task:
                task['order'] = (i + 1) * 10
                task['section'] = new_section

        # If the task was moved from a different section, re-order the source section
        if old_section != new_section:
            source_tasks = self._tasks_in_section(old_section)
            source_ids = [task['id'] for task in source_tasks if task['id'] != task_id]
            for i, tid in enumerate(source_ids):
                task = self._find_task(tid)
                if task:
                    task['order'] = (i + 1) * 10

        # Enforce Scheduled rule: Must have a date
        if new_section == "Scheduled":
            t = self._find_task(task_id)
            if t and not t.get("due_date"):
                t["due_date"] = _today_str()

        t["updated_at"] = _now_iso()
        self._schedule_save()
        self._refresh_tasks_ui()

    def _on_selection_changed(self):
        sender = self.sender()
        if not sender: return

        # If this list has a selection, clear others to ensure single focus
        if sender.selectedItems():
            for sec in self.state["sections"]:
                if sec not in self.section_blocks: continue
                lst = self.section_blocks[sec].list
                if lst != sender:
                    lst.blockSignals(True)
                    lst.clearSelection()
                    lst.setCurrentItem(None)
                    lst.blockSignals(False)
            
            if sender.currentItem():
                self._active_task_id = sender.currentItem().data(Qt.ItemDataRole.UserRole)

    def _selected_task_id(self):
        for sec in self.state["sections"]:
            if sec not in self.section_blocks:
                continue
            lst = self.section_blocks[sec].list
            item = lst.currentItem()
            if item:
                return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _toggle_selected_task(self):
        if self._focus_is_text_entry():
            return
        tid = self._selected_task_id() or self._active_task_id
        if tid:
            self._toggle_task(tid)

    def _delete_selected_task(self):
        if self._focus_is_text_entry():
            return False
        tid = self._selected_task_id() or self._active_task_id
        if not tid:
            return False
        self.state["tasks"] = [x for x in self.state["tasks"] if x.get("id") != tid and x.get("parent_id") != tid]
        self._schedule_save()
        self._refresh_tasks_ui()
        return True

    def _move_selected_task(self, delta: int):
        if self._focus_is_text_entry():
            return
        tid = self._selected_task_id() or self._active_task_id
        if not tid:
            return
        t = self._find_task(tid)
        if not t:
            return
        sec = t.get("section", "Today")
        lst = self.section_blocks[sec].list
        item = lst.currentItem()
        if not item:
            return
        row = lst.row(item)
        new_row = max(0, min(lst.count() - 1, row + delta))
        if new_row == row:
            return
        it = lst.takeItem(row)
        lst.insertItem(new_row, it)
        lst.setCurrentItem(it)
        self._on_task_moved(tid, sec, new_row)

    def _open_task_menu(self, section: str, pos):
        if section == "Calendar":
            lst = self.calendar_list
        else:
            lst = self.section_blocks[section].list
        item = lst.itemAt(pos)
        if not item:
            return
        tid = item.data(Qt.ItemDataRole.UserRole)
        self._open_task_context_menu(tid, lst.mapToGlobal(pos))

    def _open_task_context_menu(self, tid, global_pos):
        if not tid: return
        t = self._find_task(tid)
        if not t: return

        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};}}"
            f"QMenu::item{{padding:8px 22px;}}"
            f"QMenu::item:selected{{background:{HOVER_BG};}}"
        )

        act_note = menu.addAction("Quick note…")
        act_step = menu.addAction("Add step…")
        act_plan = menu.addAction("Plan (Time & Duration)...")
        act_dup = menu.addAction("Duplicate")
        act_proj = menu.addAction("Assign Project...")
        act_copy = menu.addAction("Copy Text")

        menu.addSeparator()
        recur = menu.addMenu("Repeat")
        for opt in RECUR_OPTIONS:
            a = recur.addAction(opt)
            a.triggered.connect(lambda _, o=opt, tid=tid: self._set_recur(tid, o))

        menu.addSeparator()
        act_delete = menu.addAction("Delete")

        chosen = menu.exec(global_pos)
        if chosen == act_delete:
            self._delete_selected_task()
        elif chosen == act_note:
            self._edit_task_note(tid)
        elif chosen == act_step:
            self._add_step(tid)
        elif chosen == act_plan:
            self._plan_task(tid)
        elif chosen == act_dup:
            self._duplicate_task(tid)
        elif chosen == act_proj:
            self._assign_project(tid)
        elif chosen == act_copy:
            QApplication.clipboard().setText(t.get("text", ""))

    def _plan_task(self, task_id):
        t = self._find_task(task_id)
        if not t: return
        
        dlg = PlanTaskDialog(t, self)
        if dlg.exec():
            time_str, duration = dlg.get_data()
            t["due_time"] = time_str
            t["estimated_duration"] = duration
            
            # Auto-schedule logic
            if not t.get("due_date"):
                t["due_date"] = _today_str()
            t["section"] = "Scheduled"

            t["updated_at"] = _now_iso()
            self._schedule_save()
            self._refresh_tasks_ui()
            self._refresh_calendar_tasks()

    def _assign_project(self, task_id):
        t = self._find_task(task_id)
        if not t: return
        
        dlg = ProjectSelectionDialog(self.state.get("projects", []), self)
        if dlg.exec():
            t["project_id"] = dlg.selected_project_id
            self._schedule_save()
            self._refresh_tasks_ui()

    def _duplicate_task(self, task_id):
        t = self._find_task(task_id)
        if not t: return
        
        new_task = t.copy()
        new_task["id"] = str(uuid.uuid4())
        new_task["text"] = f"{t.get('text', '')} (Copy)"
        new_task["created_at"] = _now_iso()
        new_task["updated_at"] = _now_iso()
        new_task["order"] = t.get("order", 0) + 1
        
        self.state["tasks"].append(new_task)
        self._schedule_save()
        self._refresh_tasks_ui()

    def _sort_all_sections(self):
        def priority_key(t):
            emoji = t.get("emoji", "")
            if "🔥" in emoji: return 0
            if "⭐" in emoji: return 1
            return 2

        for sec in self.state["sections"]:
            tasks = self._tasks_in_section(sec)
            if not tasks: continue
            tasks.sort(key=lambda t: (priority_key(t), t.get("order", 0)))
            for i, t in enumerate(tasks):
                t["order"] = i * 10
        
        self._schedule_save()
        self._refresh_tasks_ui()

    def _sort_section_by_priority(self, section_name):
        tasks = self._tasks_in_section(section_name)
        if not tasks: return
        
        def priority_key(t):
            emoji = t.get("emoji", "")
            if "🔥" in emoji: return 0
            if "⭐" in emoji: return 1
            return 2
            
        tasks.sort(key=lambda t: (priority_key(t), t.get("order", 0)))
        
        for i, t in enumerate(tasks):
            t["order"] = i * 10
            
        self._schedule_save()
        self._refresh_tasks_ui()

    def _move_task_to_section(self, task_id: str, new_section: str):
        t = self._find_task(task_id)
        if not t or t.get("section") == new_section:
            return
        t["section"] = new_section
        t["updated_at"] = _now_iso()
        self._schedule_save()
        self._refresh_tasks_ui()

    def _set_recur(self, task_id: str, option: str):
        t = self._find_task(task_id)
        if not t:
            return
        t["recur"] = "" if option == "None" else option
        t["updated_at"] = _now_iso()
        self._schedule_save()
        self._refresh_tasks_ui()

    def _add_step(self, parent_id: str):
        parent = self._find_task(parent_id)
        if not parent: return
        
        text, ok = QInputDialog.getText(self, "Add Step", "Step:")
        if ok and text.strip():
            self._create_task(text.strip(), section=parent.get("section", "Today"), emoji="•", parent_id=parent_id)
            self._schedule_save()
            self._refresh_tasks_ui()

    def _edit_subtask(self, parent_id: str, subtask_id: str):
        parent = self._find_task(parent_id)
        if not parent: return
        
        # Find subtask (it's a separate task in state)
        st = self._find_task(subtask_id)
        if not st: return
        
        text, ok = QInputDialog.getText(self, "Edit Step", "Step:", text=st.get("text", ""))
        if ok and text.strip():
            st["text"] = text.strip()
            st["updated_at"] = _now_iso()
            self._schedule_save()
            self._refresh_tasks_ui()

    def _create_project(self):
        name, ok = QInputDialog.getText(self, "New Project", "Project Name:")
        if ok and name.strip():
            color = random.choice(PROJECT_COLORS)
            self.state["projects"].append({
                "id": str(uuid.uuid4()),
                "name": name.strip(),
                "color": color,
                "created_at": _now_iso()
            })
            self._schedule_save()
            self._refresh_projects_list()

    def _delete_current_project(self):
        if not hasattr(self, "_current_project_id") or not self._current_project_id: return
        
        pid = self._current_project_id
        p = next((x for x in self.state["projects"] if x["id"] == pid), None)
        if not p: return

        confirm = QMessageBox.question(self, "Delete Project", f"Delete project '{p['name']}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm != QMessageBox.StandardButton.Yes: return

        # Remove from tasks
        for t in self.state["tasks"]:
            if t.get("project_id") == pid:
                t["project_id"] = None
        
        # Remove from notes
        for g in self.state["notes"]["groups"].values():
            for n in g:
                if n.get("project_id") == pid:
                    n["project_id"] = None
        
        self.state["projects"] = [p for p in self.state["projects"] if p["id"] != pid]
        self._schedule_save()
        self._refresh_projects_list()
        self._refresh_tasks_ui()
        self.projects_stack.setCurrentWidget(self.p_page_list)

    def _edit_task_note(self, task_id: str):
        t = self._find_task(task_id)
        if not t:
            return
        text, ok = QInputDialog.getMultiLineText(self, "Quick note", "Note:", t.get("note", ""))
        if ok:
            t["note"] = text
            t["updated_at"] = _now_iso()
            self._schedule_save()
            self._refresh_tasks_ui()

    def _quick_add_task(self):
        raw = (self.input.text() if self.input else "").strip()
        if not raw:
            self._shake_input()
            return
        self.input.clear()
        self.input_feedback.setFixedHeight(0)
        text, section, emoji, project_id, due_date, due_time, note = self._parse_task_input(raw)
        tid = self._create_task(text=text, section=section, emoji=emoji, project_id=project_id, due_date=due_date, due_time=due_time, note=note)
        self._schedule_save()
        self._refresh_tasks_ui()
        
        # Flash the new task
        row = self._get_task_row(tid)
        if row: row.flash()

    def _on_task_dropped_on_notes(self, task_id):
        self._switch_tab("Notes")
        t = self._find_task(task_id)
        if not t: return
        
        # Append to current note or create new
        if not self.note_list.currentItem():
            self._new_note()
        
        # Append text
        current_text = self.note_editor.toPlainText()
        new_text = current_text + f"\n- {t['text']}" if current_text else f"- {t['text']}"
        self.note_editor.setPlainText(new_text)
        self._note_edited() # Save
        
        self._show_overlay("Task Added to Note", "Task text appended to current note.", [("OK", None, "primary")])

    def _on_task_dropped_on_calendar(self, task_id):
        self._switch_tab("Calendar")
        self._plan_task(task_id) # Opens dialog

    def _on_task_dropped_on_projects(self, task_id):
        self._switch_tab("Projects")
        self._assign_project(task_id) # Opens dialog

    def _shake_input(self):
        if not self.input: return
        anim = QPropertyAnimation(self.input, b"geometry")
        anim.setDuration(500)
        anim.setLoopCount(1)
        anim.setEasingCurve(QEasingCurve.Type.OutElastic)
        start = self.input.geometry()
        anim.setKeyValueAt(0, start.adjusted(-3,0,3,0))
        anim.setKeyValueAt(0.2, start + QPoint(-5, 0))
        anim.setKeyValueAt(0.5, start + QPoint(5, 0))
        anim.setKeyValueAt(0.8, start + QPoint(-2, 0))
        anim.setKeyValueAt(1, start)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    # ---------- Notes ----------
    def _ensure_group(self, name: str):
        groups = self.state["notes"]["groups"]
        if name not in groups:
            groups[name] = []
            if name not in self.state["notes"]["order"]:
                self.state["notes"]["order"].append(name)

    def _refresh_notes_ui(self, select_note_id=None, group=None):
        current_group = group or (self.note_group.currentText() if hasattr(self, "note_group") else "") or "General"
        order = self.state["notes"].get("order", [])
        groups = list(dict.fromkeys([g for g in order if g in self.state["notes"]["groups"]]))
        for g in self.state["notes"]["groups"].keys():
            if g not in groups:
                groups.append(g)

        self.note_group.blockSignals(True)
        self.note_group.clear()
        self.note_group.addItems(groups)
        if current_group in groups:
            self.note_group.setCurrentText(current_group)
        self.note_group.blockSignals(False)

        self._fill_note_list(select_note_id=select_note_id)

    def _fill_note_list(self, select_note_id=None):
        # Refinement: preserve scroll when switching/refreshing.
        scroll = self.note_list.verticalScrollBar().value()

        g = self.note_group.currentText() or "General"
        notes = self.state["notes"]["groups"].get(g, [])

        self.note_list.blockSignals(True)
        self.note_list.clear()
        for n in notes:
            title = (n.get("title") or "Untitled").strip() or "Untitled"
            it = QListWidgetItem(title)
            it.setData(Qt.ItemDataRole.UserRole, n.get("id"))
            self.note_list.addItem(it)
        self.note_list.blockSignals(False)

        if notes:
            target_id = select_note_id or notes[0].get("id")
            for i in range(self.note_list.count()):
                it = self.note_list.item(i)
                if it.data(Qt.ItemDataRole.UserRole) == target_id:
                    self.note_list.setCurrentItem(it)
                    break
        else:
            self.note_editor.blockSignals(True)
            self.note_editor.setPlainText("")
            self.note_editor.blockSignals(False)

        self.note_list.verticalScrollBar().setValue(scroll)

    def _notes_group_changed(self, _):
        self._fill_note_list()

    def _find_note(self, note_id: str):
        for g, notes in self.state["notes"]["groups"].items():
            for n in notes:
                if n.get("id") == note_id:
                    return n
        return None

    def _note_selected(self):
        it = self.note_list.currentItem()
        if not it:
            return
        nid = it.data(Qt.ItemDataRole.UserRole)
        n = self._find_note(nid)
        self.note_editor.blockSignals(True)
        self.note_editor.setPlainText(n.get("content", "") if n else "")
        self.note_editor.blockSignals(False)

    def _note_edited(self):
        it = self.note_list.currentItem()
        if not it:
            return
        nid = it.data(Qt.ItemDataRole.UserRole)
        n = self._find_note(nid)
        if not n:
            return
        n["content"] = self.note_editor.toPlainText()
        n["updated_at"] = _now_iso()
        self._schedule_save()

    def _add_note_group(self):
        name, ok = QInputDialog.getText(self, "New group", "Group name:")
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            return
        if name in self.state["notes"]["groups"]:
            return
        self._ensure_group(name)
        self._schedule_save()
        self._refresh_notes_ui(group=name)

    def _delete_note_group(self):
        g = self.note_group.currentText() or "General"
        if g == "General":
            self._show_overlay("Can't Delete", "The 'General' group cannot be deleted.", [("OK", None, "secondary")])
            return

        notes_count = len(self.state["notes"]["groups"].get(g, []))
        self._show_overlay(
            "Delete Group",
            f"Delete group '{g}' and its {notes_count} notes?",
            [
                ("Delete", lambda: self._do_delete_note_group(g), "primary"),
                ("Cancel", None, "secondary")
            ]
        )

    def _do_delete_note_group(self, g):
        self.state["notes"]["groups"].pop(g, None)
        if g in self.state["notes"]["order"]:
            self.state["notes"]["order"].remove(g)

        self._schedule_save()
        self._refresh_notes_ui(group="General")

    def _new_note(self):
        g = self.note_group.currentText() or "General"
        self._ensure_group(g)
        note = {
            "id": str(uuid.uuid4()),
            "title": "New Note",
            "content": "",
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        self.state["notes"]["groups"][g].insert(0, note)
        self._schedule_save()
        self._refresh_notes_ui(select_note_id=note["id"], group=g)

    def _rename_selected_note(self):
        it = self.note_list.currentItem()
        if not it:
            return
        nid = it.data(Qt.ItemDataRole.UserRole)
        n = self._find_note(nid)
        if not n:
            return
        
        text, ok = QInputDialog.getText(self, "Rename note", "Title:", text=n.get("title", ""))
        if ok and text.strip():
            n["title"] = text.strip()
            n["updated_at"] = _now_iso()
            it.setText(n["title"])
            self._schedule_save()

    def _delete_selected_note(self) -> bool:
        if self.stack.currentWidget() != self.page_notes:
            return False
        it = self.note_list.currentItem()
        if not it:
            return False
        nid = it.data(Qt.ItemDataRole.UserRole)
        g = self.note_group.currentText() or "General"

        notes = self.state["notes"]["groups"].get(g, [])
        before = len(notes)
        self.state["notes"]["groups"][g] = [n for n in notes if n.get("id") != nid]

        if len(self.state["notes"]["groups"][g]) != before:
            self._schedule_save()
            self._refresh_notes_ui(group=g)
            return True
        return False

    def _open_note_menu(self, pos):
        it = self.note_list.itemAt(pos)
        if not it:
            return
        self.note_list.setCurrentItem(it)

        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};}}"
            f"QMenu::item{{padding:8px 22px;}}"
            f"QMenu::item:selected{{background:{HOVER_BG};}}"
        )
        act_rename = menu.addAction("Rename note")
        act_del = menu.addAction("Delete note")
        act_proj = menu.addAction("Assign Project...")
        chosen = menu.exec(self.note_list.mapToGlobal(pos))
        if chosen == act_rename:
            self._rename_selected_note()
        elif chosen == act_del:
            self._delete_selected_note()
        elif chosen == act_proj:
            self._assign_project_note(it.data(Qt.ItemDataRole.UserRole))

    def _assign_project_note(self, note_id):
        n = self._find_note(note_id)
        if not n: return
        
        dlg = ProjectSelectionDialog(self.state.get("projects", []), self)
        if dlg.exec():
            n["project_id"] = dlg.selected_project_id
            self._schedule_save()
            # Maybe refresh UI if we show project indicators in notes list
            # For now, just save
            self._show_overlay("Project Assigned", "Note updated.", [("OK", None, "primary")])

    # ---------- Delete any ----------
    def _delete_selected_any(self):
        if self._focus_is_text_entry():
            return
        if self.stack.currentWidget() == self.page_notes and (self.note_list.hasFocus() or self.note_list.currentItem()):
            if self._delete_selected_note():
                return
        self._delete_selected_task()

    # ---------- App ----------
    def _switch_tab(self, name: str, save: bool = True):
        # Handle leaving Zen mode via shortcuts (Ctrl+1/2/3)
        if self.stack.currentWidget() == self.page_zen:
            self.header_bar.setVisible(True)
            # Stop pulse to prevent graphics artifacts while hidden
            self._stop_zen_pulse()

        if self.stack.currentWidget() == self.page_stats:
            self.header_bar.setVisible(True)

        old_widget = self.stack.currentWidget()
        new_widget = None

        if name == "Notes":
            new_widget = self.page_notes
            self.btn_notes.setChecked(True)
            self.btn_tasks.setChecked(False)
            self.btn_projects.setChecked(False)
            self.btn_calendar.setChecked(False)
            self._refresh_notes_ui()
        elif name == "Tasks":
            new_widget = self.page_tasks
            self.btn_tasks.setChecked(True)
            self.btn_notes.setChecked(False)
            self.btn_projects.setChecked(False)
            self.btn_calendar.setChecked(False)
        elif name == "Projects":
            new_widget = self.page_projects
            self.btn_projects.setChecked(True)
            self.btn_tasks.setChecked(False)
            self.btn_notes.setChecked(False)
            self.btn_calendar.setChecked(False)
        elif name == "Calendar":
            new_widget = self.page_calendar
            self.btn_calendar.setChecked(True)
            self.btn_tasks.setChecked(False)
            self.btn_notes.setChecked(False)
            self._refresh_calendar_tasks()

        if new_widget and old_widget != new_widget:
            tab_names = ["Tasks", "Notes", "Projects", "Calendar"]
            try:
                old_idx = tab_names.index(self.state.get("ui", {}).get("active_tab", "Tasks"))
                new_idx = tab_names.index(name)
                direction = 1 if new_idx > old_idx else -1
            except (ValueError, KeyError):
                direction = 1
            self.stack.setCurrentWidget(new_widget)
            self._animate_tab_transition(new_widget, direction)

        if save:
            self.state.setdefault("ui", {})
            self.state["ui"]["active_tab"] = name
            self._schedule_save()

    def toggle_collapse(self):
        collapsed = not bool(self.state.get("ui", {}).get("collapsed", False))

        if collapsed: self._remember_expanded_geom()
        else: self.clearMask()

        self.btn_collapse.setText(">" if collapsed else "<")
        if hasattr(self, "zen_btn_collapse"):
            self.zen_btn_collapse.setText(">" if collapsed else "<")
        
        # Toggle visibility of main content and header controls
        self.stack.setVisible(not collapsed)
        
        self.nav_group.setVisible(not collapsed)
        self.streak_island.setVisible(not collapsed)
        self.tools_island.setVisible(not collapsed)
        
        self.btn_minimize.setVisible(not collapsed)
        self.btn_close.setVisible(not collapsed)
        
        if collapsed:
            self.search_group.setVisible(False)
            self.header_bar.layout().setContentsMargins(5, 0, 5, 0)
        else:
            self.header_bar.layout().setContentsMargins(10, 0, 10, 0)
            # Restore search state if text exists, otherwise show nav
            if self.search_input.text():
                self.search_group.setVisible(True)
                self.nav_group.setVisible(False)
            else:
                self.search_group.setVisible(False)
                self.nav_group.setVisible(True)
        
        if collapsed:
            target_geom = self._collapsed_geometry()
            mask_path = QPainterPath()
            mask_path.addRoundedRect(QRectF(0, 0, target_geom.width(), target_geom.height()), target_geom.height() / 2, target_geom.height() / 2)
            self.setMask(QRegion(mask_path.toFillPolygon().toPolygon()))
        else:
            target_geom = self._expanded_geometry()

        self.state.setdefault("ui", {})
        self.state["ui"]["collapsed"] = collapsed
        self._schedule_save()
        self._snap(target_geom, animated=True)

    def _focus_add(self):
        if self.state.get("ui", {}).get("collapsed", False):
            self.toggle_collapse()
        self._switch_tab("Tasks")
        self.input.setFocus()

    def _schedule_save(self):
        self._save_timer.start(SAVE_DEBOUNCE_MS)

    def _save_now(self):
        save_state(self.state)
        self._broadcast_sync() # Auto-sync on save

    def _apply_ui_state(self):
        tab = self.state.get("ui", {}).get("active_tab", "Tasks")
        self._switch_tab(tab, save=False)

        collapsed = self.state.get("ui", {}).get("collapsed", False)
        self.btn_collapse.setText(">" if collapsed else "<")
        self.stack.setVisible(not collapsed)
        self.nav_group.setVisible(not collapsed)
        self.btn_settings.setVisible(not collapsed)
        self.btn_close.setVisible(not collapsed)

        # Apply Compact Mode
        cfg = self.state.get("config", {})
        compact = cfg.get("compact_mode", False)
        self.btn_notes.setVisible(not compact)
        self.btn_calendar.setVisible(not compact)

    def _rollover_if_new_day(self, refresh_ui=False):
        last = self.state.get("last_opened", _today_str())
        now_str = _today_str()
        is_new_day = (last != now_str)
        
        # Check if we need a weekly review (Sunday & not done today)
        needs_review = (date.today().weekday() == 6 and self.state.get("last_weekly_review") != now_str)
        
        if not is_new_day and not refresh_ui and not needs_review:
            return
        
        now_date = date.today()
        changed = False
        for t in self.state["tasks"]:
            if t.get("completed"):
                continue
            
            # Move "Tomorrow" tasks
            if t.get("section") == "Tomorrow":
                t["section"] = "Today"
                t["updated_at"] = _now_iso()
                changed = True
                
            # Move past due tasks to Today
            due = t.get("due_date")
            if due:
                try:
                    if date.fromisoformat(due) < now_date:
                        t["section"] = "Today"
                        t["updated_at"] = _now_iso()
                        changed = True
                except: pass

        self.state["last_opened"] = now_str
        if changed:
            save_state(self.state)
            if refresh_ui:
                self._refresh_tasks_ui()
                self._refresh_calendar_tasks()
        
        if needs_review:
            if hasattr(self, "overlay"):
                self._show_weekly_review()
            else:
                self._pending_weekly_review = True
        elif is_new_day:
            if hasattr(self, "overlay"):
                self._show_daily_briefing()
            else:
                self._pending_briefing = True

    def _update_streak(self):
        stats = self.state.setdefault("stats", {})
        last_date = stats.get("last_activity_date")
        today = _today_str()
        
        if last_date == today:
            return # Already counted for today

        yesterday = str(date.today() - timedelta(days=1))
        current = stats.get("current_streak", 0)
        
        if last_date == yesterday:
            current += 1
            self._show_overlay("Streak Extended!", f"{current} days in a row!", [("Keep Flowing", None, "primary")])
            self.confetti.burst()
        else:
            current = 1 # Start new streak
            
        stats["current_streak"] = current
        stats["last_activity_date"] = today
        self._update_streak_display()
        self._schedule_save()
    
    def _update_streak_display(self):
        if hasattr(self, "lbl_streak"):
            stats = self.state.get("stats", {})
            streak = stats.get("current_streak", 0)
            last_date = stats.get("last_activity_date")
            
            # Visual check: is streak broken? (If last activity was before yesterday)
            if last_date:
                yesterday = str(date.today() - timedelta(days=1))
                if last_date < yesterday:
                    streak = 0
            
            self.lbl_streak.setText(f"🔥 {streak}")
            
            # Update Level UI
            lvl = stats.get("level", 1)
            xp = stats.get("xp", 0)
            self.lbl_level.setText(f"Lvl {lvl}")
            self.xp_bar.setMaximum(lvl * 100)
            self.xp_bar.setValue(xp)

    def _show_weekly_review(self):
        # Calculate stats
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        week_ago_iso = week_ago.isoformat()
        
        # Tasks
        completed_count = 0
        for t in self.state["tasks"]:
            if t.get("completed") and t.get("updated_at") >= week_ago_iso:
                completed_count += 1
                
        # Zen
        zen_mins = 0
        for s in self.state.get("zen_stats", {}).get("sessions", []):
            if s.get("date") >= week_ago_iso:
                zen_mins += s.get("duration", 0)
        
        hours = zen_mins // 60
        mins = zen_mins % 60
        time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
        
        streak = self.state.get("stats", {}).get("current_streak", 0)
        quote = random.choice(MOTIVATIONAL_QUOTES)
        
        msg = (f"<b>Tasks Completed:</b> {completed_count}<br><b>Focus Time:</b> {time_str}<br><b>Current Streak:</b> {streak} days<br><br><i>{quote}</i>")
        
        self._show_overlay("Weekly Review 📅", msg, [("Awesome", None, "primary")])
        self.state["last_weekly_review"] = _today_str()
        self._schedule_save()

    def _show_daily_briefing(self):
        today_tasks = self._tasks_in_section("Today")
        incomplete = [t for t in today_tasks if not t.get("completed")]
        count = len(incomplete)
        
        quote = random.choice(MOTIVATIONAL_QUOTES)
        
        if count == 0:
            msg = f"Your agenda is clear for today.\n\n<i>{quote}</i>"
            title = "Good Morning!"
        else:
            task_word = "task" if count == 1 else "tasks"
            msg = f"You have {count} {task_word} planned for today.\nBe proud that you showed up.\n\n<i>{quote}</i>"
            title = "Ready to Flow?"
            
        widget = DailyBriefingWidget(self.state, msg)
        self._show_overlay(title, "", [("Let's Go", None, "primary")], content_widget=widget)

if __name__ == "__main__":
    try:
        print("Starting TaskFlow...")
        app = QApplication(sys.argv)
        app.setFont(QFont("Segoe UI", 10))

        if os.name == "nt":
            try:
                import ctypes
                # Single Instance Check to prevent data corruption
                kernel32 = ctypes.windll.kernel32
                mutex = kernel32.CreateMutexW(None, False, "TaskFlow_Instance_Mutex_v6")
                if kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
                    ctypes.windll.user32.MessageBoxW(0, "TaskFlow is already running.", "TaskFlow", 0x40 | 0x1)
                    sys.exit(0)

                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
            except Exception:
                pass

        w = UltimateTaskFlow()
        w.show()
        sys.exit(app.exec())
    except Exception as e:
        # Use a native Windows message box so the error is visible 
        # even if the console is hidden (e.g. in the .exe)
        import traceback
        err_msg = f"Failed to start TaskFlow:\n\n{e}\n\n{traceback.format_exc()}"
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, err_msg, "TaskFlow Error", 0x10)
        except:
            print(err_msg)
            input("Press Enter to close...")