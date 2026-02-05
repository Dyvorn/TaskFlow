import sys
import os
import json
import shutil
import uuid
import webbrowser
import traceback  

# Global exception handler to catch startup crashes (defined early)
def global_exception_handler(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, f"Startup Error:\n{error_msg}", "TaskFlow Crash", 0x10)
    except:
        pass
    sys.exit(1)
sys.excepthook = global_exception_handler

try:
    import requests
except ImportError:
    requests = None
from datetime import datetime, date

from PyQt6.QtCore import (
    Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve,
    pyqtSignal, QThread, QRect, QPoint
)
from PyQt6.QtGui import (
    QFont, QCursor, QKeySequence, QShortcut, QColor, QDrag, QPixmap,
    QPainter, QBrush, QIcon
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QScrollArea,
    QGraphicsDropShadowEffect, QMenu,
    QListWidget, QListWidgetItem, QStackedWidget, QTextEdit,
    QComboBox, QInputDialog, QSplitter, QMessageBox, QProgressBar,
    QSystemTrayIcon
)
from PyQt6.QtCore import QMimeData



APP_NAME = "TaskFlow"
APP_ID = "taskflow.ultimate.desktop"
VERSION = "1.1"
UPDATE_URL = "https://raw.githubusercontent.com/Dyvorn/TaskFlow/main/version.json"

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        BASE_DIR = os.getcwd()

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
        "last_opened": _today_str(),
        "tasks": [],
        "notes": {"groups": {"General": []}, "order": ["General"]},
        "sections": SECTIONS.copy(),
        "ui": {"collapsed": False, "active_tab": "Tasks", "section_states": {}},
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
    data.setdefault("last_opened", _today_str())
    data.setdefault("sections", default["sections"])

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
        self.setSpacing(2)
        self.setStyleSheet(
            "QListWidget{background:transparent;border:none;}"
            "QListWidget::item{background:transparent;border:none;}"
        )

    def update_height(self):
        h = 0
        for i in range(self.count()):
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

    def dropEvent(self, event):
        super().dropEvent(event)
        # Re-order sections in state
        # (Handled by parent checking order)


class UltimateTaskFlow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.state = load_state()
        self._rollover_if_new_day()

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
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(WIN_W, WIN_H)

        self._setup_tray()

        root = QWidget()
        self.setCentralWidget(root)
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)

        self.container = QFrame()
        self.container.setObjectName("container")
        self.container.setStyleSheet(f"#container{{background:{DARK_BG};border-radius:16px;}}")
        root_lay.addWidget(self.container)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(22)
        shadow.setColor(QColor(0, 0, 0, 130))
        shadow.setOffset(0, 6)
        self.container.setGraphicsEffect(shadow)

        self.main = QVBoxLayout(self.container)
        self.main.setContentsMargins(0, 0, 0, 0)
        self.main.setSpacing(0)

        self._build_header()
        self._build_stack()
        self._wire_shortcuts()

        self._apply_ui_state()
        self._remember_expanded_geom()

        self._clamp_to_screen()
        if self.state.get("ui", {}).get("collapsed", False):
            self._snap(self._collapsed_geometry(), animated=False)

    def _setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create a simple icon programmatically
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QBrush(QColor(GOLD)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(4, 4, 24, 24, 6, 6)
        painter.end()
        
        self.tray_icon.setIcon(QIcon(pixmap))
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.show()
        
        menu = QMenu()
        menu.addAction("Show TaskFlow", self._restore_from_tray)
        menu.addAction("Quit", self._quit)
        self.tray_icon.setContextMenu(menu)

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self._minimize_to_tray()
            else:
                self._restore_from_tray()

    def _open_header_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{CARD_BG};color:{TEXT_WHITE};border:1px solid {HOVER_BG};}}"
            f"QMenu::item{{padding:8px 22px;}}"
            f"QMenu::item:selected{{background:{HOVER_BG};}}"
        )
        act_update = menu.addAction("Check for Updates...")
        chosen = menu.exec(self.header_bar.mapToGlobal(pos))
        if chosen == act_update:
            self._check_for_updates()

    def _check_for_updates(self):
        self.update_thread = UpdateCheckThread()
        self.update_thread.finished.connect(self._on_update_check_finished)
        self.update_thread.start()

    def _on_update_check_finished(self, result):
        error = result.get("error")
        if error:
            QMessageBox.warning(self, "Update Check Failed", error)
            return

        latest_version_str = result.get("latest_version")
        download_url = result.get("download_url")

        if not latest_version_str or not download_url:
            QMessageBox.warning(self, "Update Check Failed", "Invalid version information received from the server.")
            return

        try:
            latest_v = tuple(map(int, latest_version_str.split('.')))
            current_v = tuple(map(int, VERSION.split('.')))
        except ValueError:
            QMessageBox.warning(self, "Update Check Failed", f"Invalid version format received: '{latest_version_str}'")
            return

        if latest_v > current_v:
            reply = QMessageBox.information(self, "Update Available", f"A new version ({latest_version_str}) of TaskFlow is available.\n\nDo you want to open the download page?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
            if reply == QMessageBox.StandardButton.Yes:
                webbrowser.open(download_url)
        else:
            QMessageBox.information(self, "No Updates", f"You are using the latest version of TaskFlow (v{VERSION}).")

    # ---------- Helpers ----------
    def _focus_is_text_entry(self) -> bool:
        fw = QApplication.focusWidget()
        return isinstance(fw, (QLineEdit, QTextEdit))

    # ---------- Close ----------
    def _quit(self):
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
        super().closeEvent(event)

    # ---------- Event handling ----------
    def eventFilter(self, obj, event):
        watched = [w for w in (getattr(self, "input", None), getattr(self, "note_editor", None)) if w is not None]
        if watched and obj in tuple(watched):
            if event.type() in (event.Type.KeyPress, event.Type.MouseButtonPress, event.Type.FocusIn):
                self._mark_busy(2500)
        return super().eventFilter(obj, event)

    def enterEvent(self, event):
        self._auto_timer.stop()
        # Speed detection for opening
        if self.state.get("ui", {}).get("collapsed", False):
            self._entry_pos = QCursor.pos()
            QTimer.singleShot(20, self._resolve_entry_speed)
        super().enterEvent(event)

    def _resolve_entry_speed(self):
        if not self.state.get("ui", {}).get("collapsed", False):
            return
        if not self.frameGeometry().contains(QCursor.pos()):
            return
            
        curr = QCursor.pos()
        dist = (curr - self._entry_pos).manhattanLength()
        
        # If moved more than 10px in 20ms -> fast entry
        # Fast: 150ms, Slow: 400ms
        dur = 150 if dist > 10 else 400
        self.toggle_collapse(duration=dur)

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
        
        # Visual feedback when dragging collapsed handle
        if self.state.get("ui", {}).get("collapsed", False):
             self.container.setStyleSheet(f"#container{{background:{DARK_BG};border-radius:0px;border:2px solid {GOLD};}}")

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
                # Update logic for multi-screen / side switching
                self._update_geom_after_drag()
                
                # Restore invisible style and correct alignment
                side = self._collapse_side()
                self._update_layout_for_collapse(True, side)
                
                # allow repositioning the collapsed handle too
                self._snap(self._collapsed_geometry(), animated=False)
            else:
                self._clamp_to_screen()
                self._remember_expanded_geom()

    def _minimize_to_tray(self):
        self.hide()

    def _restore_from_tray(self):
        self.show()
        self.activateWindow()

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

        self.btn_tasks = QPushButton("Tasks")
        self.btn_notes = QPushButton("Notes")
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

        self.btn_minimize = QPushButton("−")
        self.btn_minimize.setFixedSize(30, 30)
        self.btn_minimize.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_minimize.setStyleSheet(
            f"QPushButton{{background:{CARD_BG};color:{TEXT_GRAY};border:none;border-radius:15px;font-weight:900;}}"
            f"QPushButton:hover{{background:{HOVER_BG};color:{TEXT_WHITE};}}"
        )
        self.btn_minimize.clicked.connect(self._minimize_to_tray)

        self.btn_collapse = QPushButton("<")
        self.btn_collapse.setFixedSize(30, 30)
        self.btn_collapse.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_collapse.setStyleSheet(
            f"QPushButton{{background:{CARD_BG};color:{TEXT_GRAY};border:none;border-radius:15px;font-weight:900;}}"
            f"QPushButton:hover{{background:{HOVER_BG};color:{TEXT_WHITE};}}"
        )
        self.btn_collapse.clicked.connect(self.toggle_collapse)

        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_close.setStyleSheet(
            f"QPushButton{{background:{CARD_BG};color:{TEXT_GRAY};border:none;border-radius:15px;font-weight:900;}}"
            f"QPushButton:hover{{background:#3a2a2a;color:{TEXT_WHITE};}}"
        )
        self.btn_close.clicked.connect(self._quit)

        lay.addWidget(self.btn_tasks)
        lay.addWidget(self.btn_notes)
        lay.addStretch()
        lay.addWidget(self.btn_minimize)
        lay.addWidget(self.btn_collapse)
        lay.addWidget(self.btn_close)

        self.main.addWidget(self.header_bar)

    def _build_stack(self):
        self.stack = QStackedWidget()
        self.main.addWidget(self.stack)

        self.page_tasks = QWidget()
        self.page_notes = QWidget()
        self.stack.addWidget(self.page_tasks)
        self.stack.addWidget(self.page_notes)

        self._build_tasks_page()
        self._build_notes_page()

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
            QMessageBox.warning(self, "Error", "Cannot delete 'Today'.")
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

        # Refined: Esc only collapses/expands when NOT typing.
        QShortcut(QKeySequence("Esc"), self, self._esc_behavior)

        # Refined: list shortcuts should not fire while typing.
        QShortcut(QKeySequence("Space"), self, self._toggle_selected_task)
        QShortcut(QKeySequence("Delete"), self, self._delete_selected_any)
        QShortcut(QKeySequence("Alt+Up"), self, lambda: self._move_selected_task(-1))
        QShortcut(QKeySequence("Alt+Down"), self, lambda: self._move_selected_task(1))

    def _esc_behavior(self):
        if self._focus_is_text_entry():
            return
        self.toggle_collapse()

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

    def _update_geom_after_drag(self):
        if not self._last_expanded_geom:
            return

        scr = self.screen().availableGeometry()
        g = self.geometry()
        side = self._collapse_side()
        
        w = self._last_expanded_geom.width()
        h = self._last_expanded_geom.height()
        
        if side in ("left", "right"):
            new_y = max(scr.top(), min(g.y(), scr.bottom() - h))
            if side == "left":
                new_x = scr.left() + 10
            else:
                new_x = scr.right() - w - 10
        else:
            new_x = max(scr.left(), min(g.x(), scr.right() - w))
            if side == "top":
                new_y = scr.top() + 50
            else:
                new_y = scr.bottom() - h - 50
                
        self._last_expanded_geom = QRect(int(new_x), int(new_y), w, h)

    def _collapse_side(self) -> str:
        scr = self.screen().availableGeometry()
        g = self.geometry()
        
        center_x = g.x() + g.width() / 2
        center_y = g.y() + g.height() / 2

        # If in the middle third horizontally, check vertical
        if scr.left() + scr.width() / 3 < center_x < scr.right() - scr.width() / 3:
            if center_y < scr.top() + scr.height() / 2:
                return "top"
            else:
                return "bottom"
        else:
            return "left" if center_x < (scr.x() + scr.width() / 2) else "right"

    def _collapsed_geometry(self) -> QRect:
        scr = self.screen().availableGeometry()
        g = self._last_expanded_geom or self.geometry()
        side = self._collapse_side()

        if side == "left":
            y = max(scr.top(), min(g.y(), scr.bottom() - WIN_H))
            x = scr.left() - (COLLAPSED_W - COLLAPSED_VISIBLE)
            return QRect(int(x), int(y), COLLAPSED_W, WIN_H)
        elif side == "right":
            y = max(scr.top(), min(g.y(), scr.bottom() - WIN_H))
            x = scr.right() - COLLAPSED_VISIBLE
            return QRect(int(x), int(y), COLLAPSED_W, WIN_H)
        elif side == "top":
            x = max(scr.left(), min(g.x(), scr.right() - WIN_W))
            y = scr.top() - (COLLAPSED_W - COLLAPSED_VISIBLE)
            # For top/bottom, we make it a horizontal tab (WIN_W wide, COLLAPSED_W high)
            return QRect(int(x), int(y), WIN_W, COLLAPSED_W)
        else: # bottom
            x = max(scr.left(), min(g.x(), scr.right() - WIN_W))
            y = scr.bottom() - COLLAPSED_VISIBLE
            return QRect(int(x), int(y), WIN_W, COLLAPSED_W)

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

    def _snap(self, target: QRect, animated: bool = True, duration: int = 260):
        if not animated:
            self.setGeometry(target)
            return
        self.geom_anim = QPropertyAnimation(self, b"geometry")
        self.geom_anim.setDuration(duration)
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

        if t["completed"] and t.get("recur"):
            freq = t.get("recur")
            next_section = "Tomorrow" if freq == "Daily" else ("This Week" if freq == "Weekly" else "Someday")
            self._create_task(text=t.get("text", ""), section=next_section, emoji=t.get("emoji", "📝"), recur=freq)

        self._schedule_save()
        self._refresh_tasks_ui()

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
        for sec in self.state["sections"]:
            if sec not in self.section_blocks:
                continue
            lst = self.section_blocks[sec].list
            if lst.currentItem():
                self._active_task_id = lst.currentItem().data(Qt.ItemDataRole.UserRole)

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
        self._create_task(text=raw, section="Today", emoji="📝")
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
            QMessageBox.information(self, "Can't delete", "The 'General' group can't be deleted.")
            return

        notes_count = len(self.state["notes"]["groups"].get(g, []))
        ok = QMessageBox.question(
            self,
            "Delete group",
            f"Delete group '{g}' and its {notes_count} notes?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if ok != QMessageBox.StandardButton.Yes:
            return

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
            self._refresh_notes_ui()
        else:
            self.btn_tasks.setChecked(True)
            self.btn_notes.setChecked(False)
            self.stack.setCurrentWidget(self.page_tasks)

        if save:
            self.state.setdefault("ui", {})
            self.state["ui"]["active_tab"] = name
            self._schedule_save()

    def _update_layout_for_collapse(self, collapsed: bool, side: str):
        root_lay = self.centralWidget().layout()
        if collapsed:
            root_lay.setContentsMargins(0, 0, 0, 0)
            # Invisible handle that catches mouse events (0.01 alpha)
            self.container.setStyleSheet(f"#container{{background:rgba(0,0,0,0.01);border-radius:0px;border:none;}}")
            
            if side == "top":
                # If collapsed to top (bottom visible), push content to bottom
                self.main.setAlignment(Qt.AlignmentFlag.AlignBottom)
            else:
                # For bottom/left/right, top alignment is fine
                self.main.setAlignment(Qt.AlignmentFlag.AlignTop)
        else:
            root_lay.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
            self.container.setStyleSheet(f"#container{{background:{DARK_BG};border-radius:16px;}}")
            self.main.setAlignment(Qt.AlignmentFlag.AlignTop)

    def toggle_collapse(self, duration: int = 260):
        collapsed = not bool(self.state.get("ui", {}).get("collapsed", False))

        if collapsed:
            self._remember_expanded_geom()

        self.state.setdefault("ui", {})
        self.state["ui"]["collapsed"] = collapsed

        self.btn_collapse.setText(">" if collapsed else "<")
        self.stack.setVisible(not collapsed)
        self.btn_tasks.setVisible(not collapsed)
        self.btn_notes.setVisible(not collapsed)

        # Update layout to ensure the handle is visible in the small window
        side = self._collapse_side() if collapsed else "left"
        self._update_layout_for_collapse(collapsed, side)

        self._schedule_save()

        if collapsed:
            self._snap(self._collapsed_geometry(), animated=True, duration=duration)
        else:
            self._snap(self._expanded_geometry(), animated=True, duration=duration)

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
        
        # Restore layout state on startup
        if collapsed:
            side = self._collapse_side()
            self._update_layout_for_collapse(True, side)

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
            pass