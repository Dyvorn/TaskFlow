import sys
import os
import json
import shutil
import uuid
import webbrowser
import traceback
import re
import subprocess
import tempfile

# Global exception handler to catch startup crashes (defined early)
def global_exception_handler(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(f"CRITICAL ERROR:\n{error_msg}", file=sys.stderr)
    try:
        import ctypes
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

from datetime import datetime, date

from PyQt6.QtCore import (
    Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve,
    pyqtSignal, QThread, QRect, QPoint, QUrl, QParallelAnimationGroup
)
from PyQt6.QtGui import (
    QFont, QCursor, QKeySequence, QShortcut, QColor, QDrag, QPixmap, QIcon
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QScrollArea,
    QGraphicsDropShadowEffect, QMenu,
    QListWidget, QListWidgetItem, QStackedWidget, QTextEdit,
    QComboBox, QInputDialog, QSplitter, QMessageBox, QProgressBar,
    QDialog, QSystemTrayIcon, QProgressDialog, QSpinBox, QCheckBox,
    QGraphicsOpacityEffect
)
from PyQt6.QtCore import QMimeData



APP_NAME = "TaskFlow"
APP_ID = "taskflow.ultimate.desktop"
VERSION = "4.0"
UPDATE_URL = "https://raw.githubusercontent.com/Dyvorn/TaskFlow/main/version.json"

WHATS_NEW_HTML = (
    "<p>This is a major release packed with power-user features:</p>"
    "<ul>"
    "<li><b>Global Quick Capture:</b> Press <code>Alt+Space</code> anywhere to add tasks instantly.</li>"
    "<li><b>Zen Mode:</b> Focus on one task with a built-in Pomodoro timer.</li>"
    "<li><b>Smart Search:</b> Press <code>Ctrl+F</code> to filter tasks and notes.</li>"
    "<li><b>Notes Tab:</b> A dedicated space for your thoughts.</li>"
    "<li><b>Settings:</b> Customize timer duration and auto-collapse.</li>"
    "<li><b>Archive:</b> Clean up completed tasks easily.</li>"
    "</ul>"
    "<p>Enjoy your flow!</p>"
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

DATA_FILE = os.path.join(BASE_DIR, "taskflow_data.json")
BACKUP_FILE = os.path.join(BASE_DIR, "taskflow_data.backup.json")

# Window geometry (includes shadow margin)
WIN_W = 440
WIN_H = 940
MARGIN = 20
COLLAPSED_W = 88
COLLAPSED_VISIBLE = 18

# Styling
DARK_BG = "#1c1c1e"
CARD_BG = "#2c2c2e"
HOVER_BG = "#3a3a3c"
TEXT_WHITE = "#ffffff"
TEXT_GRAY = "#8e8e93"
GOLD = "#fbbf24"

AUTO_COLLAPSE_DELAY_MS = 1200
SAVE_DEBOUNCE_MS = 320

SECTIONS = ["Today", "Tomorrow", "This Week", "Someday"]
RECUR_OPTIONS = ["None", "Daily", "Weekly", "Monthly"]


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _today_str():
    return str(date.today())


def _atomic_write_json(path: str, backup_path: str, data: dict):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    if os.path.exists(path):
        try:
            shutil.copy2(path, backup_path)
        except Exception:
            pass
    os.replace(tmp, path)


def load_state() -> dict:
    default = {
        "schema": 1,
        "last_version": "0.0",
        "last_opened": _today_str(),
        "tasks": [],
        "notes": {"groups": {"General": []}, "order": ["General"]},
        "sections": SECTIONS.copy(),
        "ui": {"collapsed": False, "active_tab": "Tasks", "section_states": {}},
        "config": {"zen_duration": 25, "auto_collapse": True},
    }

    def _read(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    data = None
    if os.path.exists(DATA_FILE):
        try:
            data = _read(DATA_FILE)
        except Exception:
            data = None

    if data is None and os.path.exists(BACKUP_FILE):
        try:
            data = _read(BACKUP_FILE)
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
    data["sections"] = unique_sections

    return data


def save_state(state: dict):
    _atomic_write_json(DATA_FILE, BACKUP_FILE, state)


class UpdateCheckThread(QThread):
    finished = pyqtSignal(dict)

    def run(self):
        if not requests:
            self.finished.emit({"error": "The 'requests' library is not installed.\nPlease run: pip install requests"})
            return

        if "your-server.com" in UPDATE_URL:
            self.finished.emit({"error": "The update URL has not been configured in the source code."})
            return

        try:
            res = requests.get(UPDATE_URL, timeout=10)
            res.raise_for_status()
            data = res.json()
            self.finished.emit(data)
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
            response = requests.get(self.url, stream=True, timeout=30)
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
        self.content.setFixedSize(320, 190)
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
        
        self.lbl_msg = QLabel("Message")
        self.lbl_msg.setWordWrap(True)
        self.lbl_msg.setStyleSheet(f"color:{TEXT_WHITE};font-size:14px;background:transparent;border:none;")
        self.lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.lbl_msg, 1)
        
        self.btn_layout = QHBoxLayout()
        lay.addLayout(self.btn_layout)

    def show_msg(self, title, msg, buttons):
        self.lbl_title.setText(title)
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


class TaskListWidget(QListWidget):
    taskMoved = pyqtSignal(str, str, int)
    heightChanged = pyqtSignal()

    def __init__(self, section_name: str, parent=None):
        super().__init__(parent)
        self.section_name = section_name
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
        self.setFixedHeight(max(h, 25))
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
        else:
            super().dropEvent(e)


class SubtaskWidget(QFrame):
    toggled = pyqtSignal(str)

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


class TaskRow(QFrame):
    toggled = pyqtSignal(str)
    subtaskToggled = pyqtSignal(str)
    resized = pyqtSignal()
    focusRequested = pyqtSignal(str)

    def __init__(self, task: dict, subtasks: list, number_text: str, parent=None):
        super().__init__(parent)
        self.task = task
        self.subtasks = subtasks
        self.setStyleSheet("background:transparent;")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.expanded = False
        self._drag_start_pos = None
        self._dragged = False

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

        self.lbl_text = QLabel(task.get("text", ""))
        self.lbl_text.setWordWrap(True)

        self.btn_focus = QPushButton("👁")
        self.btn_focus.setFixedSize(24, 24)
        self.btn_focus.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_focus.setStyleSheet(
            f"QPushButton{{color:{TEXT_GRAY};background:transparent;border:none;font-size:14px;}}"
            f"QPushButton:hover{{color:{GOLD};}}"
        )
        self.btn_focus.clicked.connect(lambda: self.focusRequested.emit(self.task["id"]))

        self.lbl_note = QLabel("•")
        self.lbl_note.setFixedWidth(10)
        self.lbl_note.setStyleSheet(f"color:{TEXT_GRAY};font-size:20px;")
        has_note = bool((task.get("note") or "").strip()) or bool(self.subtasks)
        self.lbl_note.setVisible(has_note)

        self.chk = QLabel("✓")
        self.chk.setFixedSize(22, 22)
        self.chk.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lay.addWidget(self.lbl_num)
        lay.addWidget(self.lbl_recur)
        lay.addWidget(self.lbl_emoji)
        lay.addWidget(self.lbl_text, 1)
        lay.addWidget(self.btn_focus)
        lay.addWidget(self.lbl_note)
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
            self.exp_lay.addWidget(sw)

        self.main_lay.addWidget(self.top_frame)
        self.main_lay.addWidget(self.expansion)

        self._apply_state()

    def _apply_state(self):
        done = bool(self.task.get("completed"))
        if done:
            self.lbl_text.setStyleSheet(f"color:{TEXT_GRAY};text-decoration:line-through;")
            self.chk.setStyleSheet(f"background:{GOLD};color:{DARK_BG};border-radius:11px;font-weight:800;")
        else:
            self.lbl_text.setStyleSheet(f"color:{TEXT_WHITE};")
            self.chk.setStyleSheet(f"border:2px solid {GOLD};border-radius:11px;color:transparent;")

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = e.pos()
            self._dragged = False
            # Check if clicked on checkbox area
            if self.chk.geometry().contains(self.top_frame.mapFrom(self, e.pos())):
                self.toggled.emit(self.task["id"])
                self._drag_start_pos = None
                return
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
        drag.setPixmap(self.grab())
        drag.setHotSpot(e.pos())
        drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and not self._dragged and self._drag_start_pos:
            if self.task.get("note") or self.subtasks:
                self.expanded = not self.expanded
                self.expansion.setVisible(self.expanded)
                self.resized.emit()
        super().mouseReleaseEvent(e)


class SectionBlock(QWidget):
    requestResize = pyqtSignal()
    renameRequested = pyqtSignal(str)
    deleteRequested = pyqtSignal(str)
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

        self.progress = QProgressBar()
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"QProgressBar{{border:none;background:{HOVER_BG};border-radius:1px;}} QProgressBar::chunk{{background:{GOLD};border-radius:1px;}}")
        lay.addWidget(self.progress)

        self.list = TaskListWidget(name)
        self.list.heightChanged.connect(self.requestResize.emit)

        lay.addWidget(self.header)
        lay.addWidget(self.list)

    def _on_header_click(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.collapsed = not self.collapsed
            self.list.setVisible(not self.collapsed)
            self.btn_arrow.setText("▶" if self.collapsed else "▼")
            self.requestResize.emit()
            self.collapsedChanged.emit(self.collapsed)

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
            self.progress.setValue(completed)

    def _on_header_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};}}"
            f"QMenu::item{{padding:8px 22px;}}"
            f"QMenu::item:selected{{background:{HOVER_BG};}}"
        )
        act_rename = menu.addAction("Rename")
        act_del = menu.addAction("Delete Section")
        
        chosen = menu.exec(self.header.mapToGlobal(pos))
        if chosen == act_rename:
            self.renameRequested.emit(self.name)
        elif chosen == act_del:
            self.deleteRequested.emit(self.name)


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


class UltimateTaskFlow(QMainWindow):
    request_quick_capture = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.state = load_state()
        self._rollover_if_new_day()

        self._zen_task_id = None
        self.input = None
        self.note_editor = None

        self._dragging = False
        self._drag_offset = QPoint(0, 0)
        self._last_expanded_geom = None

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_now)

        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._auto_collapse_if_needed)

        self._busy_until = 0
        self._active_task_id = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Window
        )
        self.setWindowTitle(APP_NAME)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(WIN_W, WIN_H)

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
        self.container.setStyleSheet(f"#container{{background:{DARK_BG};border-radius:16px;}}")
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
        
        # Overlay (created after stack to sit on top)
        self.overlay = OverlayDialog(self.container)

        self._apply_ui_state()
        self._remember_expanded_geom()

        self._clamp_to_screen()
        if self.state.get("ui", {}).get("collapsed", False):
            self._snap(self._collapsed_geometry(), animated=False)

        # Show What's New if version changed
        if self.state.get("last_version") != VERSION:
            QTimer.singleShot(1000, self._show_whats_new)

        # Check for updates silently on startup (delayed slightly to let UI load)
        QTimer.singleShot(2000, lambda: self._check_for_updates(silent=True))

    
        # (Sound removed for this version)

        # Zen Timer Setup
        self.zen_timer = QTimer(self)
        self.zen_timer.timeout.connect(self._update_zen_timer)
        self.zen_remaining = 25 * 60
        self.zen_running = False

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

    def _animate_tab_transition(self, widget):
        if not self.isVisible():
            return

        # Stop any running animations
        if hasattr(self, "_tab_anim") and self._tab_anim.state() == QPropertyAnimation.State.Running:
            self._tab_anim.stop()

        # Ensure widget is in the correct layout position (0,0) to fix hitbox offset bugs
        widget.move(0, 0)
        
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        
        self._tab_anim = QPropertyAnimation(effect, b"opacity", widget)
        self._tab_anim.setStartValue(0.0)
        self._tab_anim.setEndValue(1.0)
        self._tab_anim.setDuration(180)
        self._tab_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._tab_anim.finished.connect(lambda: widget.setGraphicsEffect(None))
        self._tab_anim.start()

    def _setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        # Create a simple gold pixmap for the icon
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(GOLD))
        self.tray_icon.setIcon(QIcon(pixmap))
        
        tray_menu = QMenu()
        act_show = tray_menu.addAction("Show/Hide")
        act_show.triggered.connect(self.toggle_collapse)
        act_quit = tray_menu.addAction("Quit")
        act_quit.triggered.connect(self._force_quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

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

        if not latest_version_str or not download_url:
            if not getattr(self, "_update_silent", False):
                self._show_overlay("Update Failed", "Invalid version info.", [("OK", None, "secondary")])
            return

        try:
            latest_v = tuple(map(int, latest_version_str.split('.')))
            current_v = tuple(map(int, VERSION.split('.')))
        except ValueError:
            if not getattr(self, "_update_silent", False):
                self._show_overlay("Update Failed", "Invalid version format.", [("OK", None, "secondary")])
            return

        if latest_v > current_v:
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
                self._show_overlay("No Updates", f"You are on the latest version (v{VERSION}).", [("OK", None, "primary")])

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
        self.chk_startup.setChecked(self._is_startup_enabled())
        
        self.header_bar.setVisible(False)
        self.stack.setCurrentWidget(self.page_settings)
        self._animate_tab_transition(self.page_settings)

    def _close_settings(self):
        self.state["config"]["zen_duration"] = self.spin_zen.value()
        self.state["config"]["auto_collapse"] = self.chk_collapse.isChecked()
        self._set_startup(self.chk_startup.isChecked())
        self._schedule_save()
        self._reset_zen_timer()
        
        self.header_bar.setVisible(True)
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
        text, section, emoji = self._parse_task_input(text)
        self._create_task(text, section, emoji)
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
        event.ignore()
        self.hide()

    # ---------- Event handling ----------
    def eventFilter(self, obj, event):
        if obj == self.container and event.type() == event.Type.Resize:
            if hasattr(self, "overlay"):
                self.overlay.resize(self.container.size())

        watched = [w for w in (getattr(self, "input", None), getattr(self, "note_editor", None)) if w is not None]
        if watched and obj in tuple(watched):
            if event.type() in (event.Type.KeyPress, event.Type.MouseButtonPress, event.Type.FocusIn):
                self._mark_busy(2500)
        return super().eventFilter(obj, event)

    def enterEvent(self, event):
        self._auto_timer.stop()
        if self.state.get("ui", {}).get("collapsed", False):
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
        self._dragging = True
        self._drag_offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        self._mark_busy(2500)

    def _drag_move(self, e):
        if not self._dragging:
            return
        if not (e.buttons() & Qt.MouseButton.LeftButton):
            self._dragging = False
            return
        self.move(e.globalPosition().toPoint() - self._drag_offset)

    def _drag_release(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            if self.state.get("ui", {}).get("collapsed", False):
                # allow repositioning the collapsed handle too
                self._snap(self._collapsed_geometry(), animated=False)
            else:
                self._clamp_to_screen()
                self._remember_expanded_geom()

    # ---------- UI ----------
    def _build_header(self):
        self.header_bar = QFrame()
        self.header_bar.setFixedHeight(58)
        self.header_bar.setStyleSheet("background:transparent;")
        self.header_bar.mousePressEvent = self._drag_press
        self.header_bar.mouseMoveEvent = self._drag_move
        self.header_bar.mouseReleaseEvent = self._drag_release
        self.header_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.header_bar.customContextMenuRequested.connect(self._open_header_menu)

        lay = QHBoxLayout(self.header_bar)
        lay.setContentsMargins(14, 0, 12, 0)
        lay.setSpacing(10)

        # Navigation Group (Tasks/Notes)
        self.nav_group = QWidget()
        nav_lay = QHBoxLayout(self.nav_group)
        nav_lay.setContentsMargins(0, 0, 0, 0)
        nav_lay.setSpacing(10)

        self.btn_tasks = QPushButton("Tasks")
        self.btn_notes = QPushButton("Notes")
        
        # Search Group
        self.search_group = QWidget()
        self.search_group.setVisible(False)
        search_lay = QHBoxLayout(self.search_group)
        search_lay.setContentsMargins(0, 0, 0, 0)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tasks & notes...")
        self.search_input.setStyleSheet(
            f"background:{HOVER_BG};color:{TEXT_WHITE};border:none;border-radius:15px;padding:4px 12px;font-size:14px;"
        )
        self.search_input.textChanged.connect(self._perform_search)
        # Pressing Esc in search closes it
        self.search_shortcut_esc = QShortcut(QKeySequence("Esc"), self.search_input)
        self.search_shortcut_esc.activated.connect(self._toggle_search)
        
        search_lay.addWidget(self.search_input)

        for b in (self.btn_tasks, self.btn_notes):
            b.setCheckable(True)
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            b.setStyleSheet(
                f"QPushButton{{color:{TEXT_GRAY};background:transparent;border:none;font-weight:800;}}"
                f"QPushButton:hover{{color:{TEXT_WHITE};}}"
                f"QPushButton:checked{{color:{GOLD};}}"
            )

        self.btn_tasks.clicked.connect(lambda: self._switch_tab("Tasks"))
        self.btn_notes.clicked.connect(lambda: self._switch_tab("Notes"))

        self.btn_search = QPushButton("🔍")
        self.btn_search.setFixedSize(30, 30)
        self.btn_search.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_search.setStyleSheet(
            f"QPushButton{{color:{TEXT_GRAY};background:transparent;border:none;font-weight:800;font-size:16px;}}"
            f"QPushButton:hover{{color:{TEXT_WHITE};}}"
        )
        self.btn_search.clicked.connect(self._toggle_search)

        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setFixedSize(30, 30)
        self.btn_settings.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_settings.setStyleSheet(
            f"QPushButton{{color:{TEXT_GRAY};background:transparent;border:none;font-weight:800;font-size:18px;}}"
            f"QPushButton:hover{{color:{TEXT_WHITE};}}"
        )
        self.btn_settings.clicked.connect(self._open_settings)

        self.btn_collapse = QPushButton("<")
        self.btn_collapse.setFixedSize(30, 30)
        self.btn_collapse.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_collapse.setStyleSheet(
            f"QPushButton{{background:{CARD_BG};color:{TEXT_GRAY};border:none;border-radius:15px;font-weight:900;}}"
            f"QPushButton:hover{{background:{HOVER_BG};color:{TEXT_WHITE};}}"
        )
        self.btn_collapse.clicked.connect(self.toggle_collapse)

        self.btn_minimize = QPushButton("−")
        self.btn_minimize.setFixedSize(30, 30)
        self.btn_minimize.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_minimize.setStyleSheet(
            f"QPushButton{{background:{CARD_BG};color:{TEXT_GRAY};border:none;border-radius:15px;font-weight:900;}}"
            f"QPushButton:hover{{background:{HOVER_BG};color:{TEXT_WHITE};}}"
        )
        self.btn_minimize.clicked.connect(self.showMinimized)

        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_close.setStyleSheet(
            f"QPushButton{{background:{CARD_BG};color:{TEXT_GRAY};border:none;border-radius:15px;font-weight:900;}}"
            f"QPushButton:hover{{background:#3a2a2a;color:{TEXT_WHITE};}}"
        )
        self.btn_close.clicked.connect(self._quit)

        nav_lay.addWidget(self.btn_tasks)
        nav_lay.addWidget(self.btn_notes)

        lay.addWidget(self.nav_group)
        lay.addWidget(self.search_group, 1) # Stretch search bar
        lay.addWidget(self.btn_search)
        lay.addStretch()
        lay.addWidget(self.btn_settings)
        lay.addWidget(self.btn_collapse)
        lay.addWidget(self.btn_minimize)
        lay.addWidget(self.btn_close)

        self.main.addWidget(self.header_bar)

    def _build_stack(self):
        self.stack = QStackedWidget()
        self.main.addWidget(self.stack)

        self.page_tasks = QWidget()
        self.page_notes = QWidget()
        self.page_zen = QWidget()
        self.page_settings = QWidget()
        self.page_whats_new = QWidget()

        self.stack.addWidget(self.page_tasks)
        self.stack.addWidget(self.page_notes)
        self.stack.addWidget(self.page_zen)
        self.stack.addWidget(self.page_settings)
        self.stack.addWidget(self.page_whats_new)

        self._build_tasks_page()
        self._build_notes_page()
        self._build_zen_page()
        self._build_settings_page()
        self._build_whats_new_page()

    def _build_tasks_page(self):
        lay = QVBoxLayout(self.page_tasks)
        lay.setContentsMargins(14, 0, 14, 12)
        lay.setSpacing(10)

        self.input = QLineEdit()
        self.input.setPlaceholderText("✨ Add task…")
        self.input.setStyleSheet(
            f"QLineEdit{{background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};border-radius:12px;padding:12px;}}"
            f"QLineEdit:focus{{border:1px solid {GOLD};}}"
        )
        self.input.returnPressed.connect(self._quick_add_task)
        self.input.installEventFilter(self)
        lay.addWidget(self.input)

        self.board_list = BoardListWidget()
        self.board_list.setStyleSheet(
            "QListWidget{border:none;background:transparent;}"
            "QScrollBar:vertical{width:8px;background:transparent;}"
            "QScrollBar::handle:vertical{background:#2c2c2e;border-radius:4px;min-height:30px;}"
        )
        self.board_list.model().rowsMoved.connect(self._on_section_reordered)
        lay.addWidget(self.board_list, 1)
        
        self.board_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.board_list.customContextMenuRequested.connect(self._open_board_menu)

        self.section_blocks = {}
        self._refresh_tasks_ui()

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
        self.btn_exit_zen = QPushButton("×")
        self.btn_exit_zen.setFixedSize(30, 30)
        self.btn_exit_zen.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_exit_zen.setStyleSheet(
            f"QPushButton{{background:{CARD_BG};color:{TEXT_GRAY};border:none;border-radius:15px;font-weight:900;font-size:16px;}}"
            f"QPushButton:hover{{background:{HOVER_BG};color:{TEXT_WHITE};}}"
        )
        self.btn_exit_zen.clicked.connect(self.exit_zen_mode)
        top.addWidget(self.btn_exit_zen)
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
        self.spin_zen.setStyleSheet(f"background:{CARD_BG};border:1px solid {HOVER_BG};padding:4px;color:{TEXT_WHITE};")
        h1.addWidget(lbl)
        h1.addWidget(self.spin_zen)
        lay.addLayout(h1)
        
        # Auto Collapse
        self.chk_collapse = QCheckBox("Auto-collapse when focus lost")
        self.chk_collapse.setStyleSheet(f"QCheckBox{{color:{TEXT_GRAY};}} QCheckBox::indicator{{border:1px solid {TEXT_GRAY};width:14px;height:14px;}} QCheckBox::indicator:checked{{background:{GOLD};border:none;}}")
        lay.addWidget(self.chk_collapse)

        # Start with Windows
        self.chk_startup = QCheckBox("Start with Windows")
        self.chk_startup.setStyleSheet(f"QCheckBox{{color:{TEXT_GRAY};}} QCheckBox::indicator{{border:1px solid {TEXT_GRAY};width:14px;height:14px;}} QCheckBox::indicator:checked{{background:{GOLD};border:none;}}")
        lay.addWidget(self.chk_startup)

        # Check for Updates
        self.btn_update = QPushButton("Check for Updates")
        self.btn_update.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_update.setStyleSheet(f"background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};border-radius:6px;padding:6px;")
        self.btn_update.clicked.connect(self._check_for_updates)
        lay.addWidget(self.btn_update)

        lay.addStretch()

        # Version Label
        self.lbl_ver = QLabel(f"TaskFlow v{VERSION}")
        self.lbl_ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_ver.setStyleSheet(f"color:{TEXT_GRAY};font-size:12px;text-decoration:underline;")
        self.lbl_ver.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.lbl_ver.mousePressEvent = lambda e: self._show_whats_new()
        lay.addWidget(self.lbl_ver)

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
            f"QCheckBox{{color:{TEXT_GRAY};}} QCheckBox::indicator{{border:1px solid {TEXT_GRAY};width:14px;height:14px;}} QCheckBox::indicator:checked{{background:{GOLD};border:none;}}"
        )
        lay.addWidget(self.chk_dont_show)
        
        btn = QPushButton("Let's Flow")
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.clicked.connect(self._close_whats_new)
        btn.setStyleSheet(f"background:{GOLD};color:{DARK_BG};border-radius:6px;padding:8px;font-weight:bold;")
        lay.addWidget(btn)

    def _show_overlay(self, title, msg, buttons):
        self.overlay.show_msg(title, msg, buttons)

    def enter_zen_mode(self, task_id: str):
        self._zen_task_id = task_id
        self._populate_zen_view(task_id)
        self.header_bar.setVisible(False)
        self.stack.setCurrentWidget(self.page_zen)
        self._animate_tab_transition(self.page_zen)

    def exit_zen_mode(self):
        if self.zen_running:
            self._toggle_zen_timer()
        self._zen_task_id = None
        self.header_bar.setVisible(True)
        self.stack.setCurrentWidget(self.page_tasks)
        self._animate_tab_transition(self.page_tasks)

    def _populate_zen_view(self, task_id: str):
        t = self._find_task(task_id)
        if not t: return
        
        self.zen_emoji.setText(t.get("emoji", "📝"))
        self.zen_text.setText(t.get("text", ""))
        
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
            self.btn_timer_toggle.setText("▶ Start")
            self.btn_timer_toggle.setStyleSheet(
                f"QPushButton{{background:{HOVER_BG};color:{TEXT_WHITE};border-radius:20px;font-weight:bold;}}"
                f"QPushButton:hover{{background:{GOLD};color:{DARK_BG};}}"
            )
        else:
            self.zen_timer.start(1000)
            self.zen_running = True
            self.btn_timer_toggle.setText("⏸ Pause")
            self.btn_timer_toggle.setStyleSheet(
                f"QPushButton{{background:{GOLD};color:{DARK_BG};border-radius:20px;font-weight:bold;}}"
                f"QPushButton:hover{{background:#fcd34d;}}"
            )

    def _reset_zen_timer(self):
        self.zen_timer.stop()
        self.zen_running = False
        self.zen_remaining = 25 * 60
        self._update_timer_display()
        self.btn_timer_toggle.setText("▶ Start")
        self.btn_timer_toggle.setStyleSheet(
            f"QPushButton{{background:{HOVER_BG};color:{TEXT_WHITE};border-radius:20px;font-weight:bold;}}"
            f"QPushButton:hover{{background:{GOLD};color:{DARK_BG};}}"
        )

    def _update_zen_timer(self):
        if self.zen_remaining > 0:
            self.zen_remaining -= 1
            self._update_timer_display()
        else:
            self.zen_timer.stop()
            self.zen_running = False
            self.btn_timer_toggle.setText("▶ Start")
            self.showNormal()
            self.activateWindow()
            self._show_overlay("Flow Complete", "Focus session finished!", [("Awesome", None, "primary")])

    def _update_timer_display(self):
        m = self.zen_remaining // 60
        s = self.zen_remaining % 60
        self.lbl_timer.setText(f"{m:02}:{s:02}")

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
            print(f"Startup registry error: {e}")

    def _create_section_item(self, name: str):
        blk = SectionBlock(name)
        blk.list.taskMoved.connect(self._on_task_moved)
        blk.list.itemSelectionChanged.connect(self._on_selection_changed)
        blk.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        blk.list.customContextMenuRequested.connect(lambda pos, sec=name: self._open_task_menu(sec, pos))
        
        blk.renameRequested.connect(self._rename_section)
        blk.deleteRequested.connect(self._delete_section)
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
        )
        act_add = menu.addAction("Add section")
        chosen = menu.exec(self.board_list.mapToGlobal(pos))
        if chosen == act_add:
            self._add_custom_section()

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
        if name == "Today":
            self._show_overlay("Error", "Cannot delete 'Today'.", [("OK", None, "secondary")])
            return
        
        # Move tasks to Today
        for t in self.state["tasks"]:
            if t.get("section") == name:
                t["section"] = "Today"
        
        if name in self.state["sections"]:
            self.state["sections"].remove(name)
        
        self._schedule_save()
        self._refresh_tasks_ui()

    def _on_section_reordered(self):
        new_order = []
        for i in range(self.board_list.count()):
            item = self.board_list.item(i)
            w = self.board_list.itemWidget(item)
            if isinstance(w, SectionBlock):
                new_order.append(w.name)
        
        if new_order:
            self.state["sections"] = new_order
            self._schedule_save()

    def _build_notes_page(self):
        lay = QVBoxLayout(self.page_notes)
        lay.setContentsMargins(14, 0, 14, 12)
        lay.setSpacing(10)

        top = QHBoxLayout()
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
            match = text in item.text().lower()
            item.setHidden(not match)

    # ---------- Auto-collapse ----------
    def _mark_busy(self, ms: int):
        self._busy_until = int(datetime.now().timestamp() * 1000) + ms

    def _is_busy(self) -> bool:
        return int(datetime.now().timestamp() * 1000) < self._busy_until

    def _schedule_autocollapse(self):
        if self._is_busy():
            return
        self._auto_timer.start(AUTO_COLLAPSE_DELAY_MS)

    def _auto_collapse_if_needed(self):
        if self._is_busy():
            return
        if not self.state.get("config", {}).get("auto_collapse", True):
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
        y = max(scr.top(), min(g.y(), scr.bottom() - WIN_H))
        side = self._collapse_side()

        if side == "left":
            x = scr.left() - (COLLAPSED_W - COLLAPSED_VISIBLE)
        else:
            x = scr.right() - COLLAPSED_VISIBLE

        return QRect(int(x), int(y), COLLAPSED_W, WIN_H)

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
        ts = [t for t in self.state["tasks"] if t.get("section") == section]
        ts.sort(key=lambda x: (x.get("order", 0), x.get("created_at", "")))
        return ts

    def _refresh_tasks_ui(self):
        # Refinement: preserve selection + scroll positions per section.
        preserve = {}
        saved_states = self.state.get("ui", {}).get("section_states", {})
        for sec in self.state["sections"]:
            if sec in self.section_blocks:
                blk = self.section_blocks[sec]
                lst = blk.list
                sel = lst.currentItem().data(Qt.ItemDataRole.UserRole) if lst.currentItem() else None
                preserve[sec] = {
                    "selected": sel,
                    "collapsed": blk.collapsed
                }

        self.board_list.clear()
        self.section_blocks.clear()

        for sec in self.state["sections"]:
            item, blk = self._create_section_item(sec)
            self.board_list.addItem(item)
            self.board_list.setItemWidget(item, blk)

            tasks = self._tasks_in_section(sec)
            
            # Update progress
            completed = len([t for t in tasks if t.get("completed")])
            blk.update_progress(len(tasks), completed)

            lst = blk.list
            lst.blockSignals(True)
            lst.clear()

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
                row = TaskRow(t, subs, num)
                row.toggled.connect(self._toggle_task)
                row.subtaskToggled.connect(self._toggle_task)
                row.resized.connect(lambda: self._on_task_resize(lst, t_item, row))
                row.focusRequested.connect(self.enter_zen_mode)

                t_item.setSizeHint(row.sizeHint())
                lst.addItem(t_item)
                lst.setItemWidget(t_item, row)
            
            lst.update_height()
            item.setSizeHint(blk.sizeHint())

            lst.blockSignals(False)

            # restore selection + scroll
            saved = preserve.get(sec, {})
            want = saved.get("selected")
            if want:
                for i in range(lst.count()):
                    if lst.item(i).data(Qt.ItemDataRole.UserRole) == want:
                        lst.setCurrentRow(i)
                        break
            
            if saved.get("collapsed", False):
                blk.collapsed = True
                blk.list.setVisible(False)
                blk.btn_arrow.setText("▶")
                item.setSizeHint(blk.sizeHint())

    def _on_task_resize(self, lst, item, widget):
        item.setSizeHint(widget.sizeHint())
        lst.update_height()

    def _find_task(self, task_id: str):
        for t in self.state["tasks"]:
            if t.get("id") == task_id:
                return t
        return None

    def _parse_task_input(self, text: str):
        text = text.strip()
        section = "Today"
        emoji = "📝"

        # Priority detection
        if re.search(r'\bimportant\b', text, re.IGNORECASE):
            emoji = "🔥"
            text = re.sub(r'\bimportant\b', '', text, flags=re.IGNORECASE)
        
        if text.endswith("!"):
            emoji = "🔥"
            text = text.rstrip("!")

        # Section detection
        if re.search(r'\btomorrow\b', text, re.IGNORECASE):
            section = "Tomorrow"
            text = re.sub(r'\btomorrow\b', '', text, flags=re.IGNORECASE)
        elif re.search(r'\b(later|someday)\b', text, re.IGNORECASE):
            section = "Someday"
            text = re.sub(r'\b(later|someday)\b', '', text, flags=re.IGNORECASE)

        # Cleanup whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text, section, emoji

    def _create_task(self, text: str, section: str, emoji: str, recur: str = "", parent_id=None):
        text = (text or "").strip()
        if not text:
            return
        if section not in self.state["sections"]:
            section = "Today"
        existing = self._tasks_in_section(section)
        max_order = max([t.get("order", 0) for t in existing], default=0)

        self.state["tasks"].append({
            "id": str(uuid.uuid4()),
            "text": text[:120],
            "emoji": emoji or "📝",
            "completed": False,
            "section": section,
            "order": max_order + 10,
            "note": "",
            "recur": recur or "",
            "parent_id": parent_id,
            "linked_note_id": None,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        })

    def _toggle_task(self, task_id: str):
        # Refinement: avoid toggling while user is typing.
        if self._focus_is_text_entry():
            return
        t = self._find_task(task_id)
        if not t:
            return
        t["completed"] = not bool(t.get("completed"))
        t["updated_at"] = _now_iso()

        if t["completed"]:
            pass
        elif t["completed"] and t.get("recur"):
            freq = t.get("recur")
            next_section = "Tomorrow" if freq == "Daily" else ("This Week" if freq == "Weekly" else "Someday")
            self._create_task(text=t.get("text", ""), section=next_section, emoji=t.get("emoji", "📝"), recur=freq)

        self._schedule_save()
        self._refresh_tasks_ui()
        if self._zen_task_id:
            self._populate_zen_view(self._zen_task_id)

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
        lst = self.section_blocks[section].list
        item = lst.itemAt(pos)
        if not item:
            return
        lst.setCurrentItem(item)
        tid = item.data(Qt.ItemDataRole.UserRole)
        t = self._find_task(tid)
        if not t:
            return

        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};}}"
            f"QMenu::item{{padding:8px 22px;}}"
            f"QMenu::item:selected{{background:{HOVER_BG};}}"
        )

        act_note = menu.addAction("Quick note…")
        act_step = menu.addAction("Add step…")

        menu.addSeparator()
        recur = menu.addMenu("Repeat")
        for opt in RECUR_OPTIONS:
            a = recur.addAction(opt)
            a.triggered.connect(lambda _, o=opt, tid=tid: self._set_recur(tid, o))

        menu.addSeparator()
        act_delete = menu.addAction("Delete")

        chosen = menu.exec(lst.mapToGlobal(pos))
        if chosen == act_delete:
            self._delete_selected_task()
        elif chosen == act_note:
            self._edit_task_note(tid)
        elif chosen == act_step:
            self._add_step(tid)

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
            return
        self.input.clear()
        text, section, emoji = self._parse_task_input(raw)
        self._create_task(text=text, section=section, emoji=emoji)
        self._schedule_save()
        self._refresh_tasks_ui()

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
            "title": "Untitled",
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
        chosen = menu.exec(self.note_list.mapToGlobal(pos))
        if chosen == act_rename:
            self._rename_selected_note()
        elif chosen == act_del:
            self._delete_selected_note()

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
        if name == "Notes":
            self.btn_notes.setChecked(True)
            self.btn_tasks.setChecked(False)
            self.stack.setCurrentWidget(self.page_notes)
            self._animate_tab_transition(self.page_notes)
            self._refresh_notes_ui()
        else:
            self.btn_tasks.setChecked(True)
            self.btn_notes.setChecked(False)
            self.stack.setCurrentWidget(self.page_tasks)
            self._animate_tab_transition(self.page_tasks)

        if save:
            self.state.setdefault("ui", {})
            self.state["ui"]["active_tab"] = name
            self._schedule_save()

    def toggle_collapse(self):
        collapsed = not bool(self.state.get("ui", {}).get("collapsed", False))

        if collapsed:
            self._remember_expanded_geom()

        self.state.setdefault("ui", {})
        self.state["ui"]["collapsed"] = collapsed

        self.btn_collapse.setText(">" if collapsed else "<")
        self.stack.setVisible(not collapsed)
        self.btn_tasks.setVisible(not collapsed)
        self.btn_notes.setVisible(not collapsed)

        self._schedule_save()

        if collapsed:
            self._snap(self._collapsed_geometry(), animated=True)
        else:
            self._snap(self._expanded_geometry(), animated=True)

    def _focus_add(self):
        if self.state.get("ui", {}).get("collapsed", False):
            self.toggle_collapse()
        self._switch_tab("Tasks")
        self.input.setFocus()

    def _schedule_save(self):
        self._save_timer.start(SAVE_DEBOUNCE_MS)

    def _save_now(self):
        save_state(self.state)

    def _apply_ui_state(self):
        tab = self.state.get("ui", {}).get("active_tab", "Tasks")
        self._switch_tab(tab, save=False)

        collapsed = self.state.get("ui", {}).get("collapsed", False)
        self.btn_collapse.setText(">" if collapsed else "<")
        self.stack.setVisible(not collapsed)
        self.btn_tasks.setVisible(not collapsed)
        self.btn_notes.setVisible(not collapsed)

    def _rollover_if_new_day(self):
        last = self.state.get("last_opened", _today_str())
        now = _today_str()
        if last == now:
            return
        for t in self.state["tasks"]:
            if t.get("section") == "Today" and not t.get("completed"):
                t["section"] = "Tomorrow"
                t["updated_at"] = _now_iso()
        self.state["last_opened"] = now
        save_state(self.state)


if __name__ == "__main__":
    try:
        print("Starting TaskFlow...")
        app = QApplication(sys.argv)
        app.setFont(QFont("Segoe UI", 10))

        if os.name == "nt":
            try:
                import ctypes
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