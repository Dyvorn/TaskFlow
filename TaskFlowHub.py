# ============================================================================
# TASKFLOW HUB V6.0 - Planning & Mental Health Workspace
# ============================================================================

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1: IMPORTS & SETUP
# ═══════════════════════════════════════════════════════════════════════════

import sys
import os
import json
import uuid
import threading
import webbrowser
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from PyQt6.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QComboBox,
    QTextEdit,
    QSpacerItem,
    QSizePolicy,
    QGraphicsOpacityEffect,
    QMessageBox,
)
from PyQt6.QtWidgets import QInputDialog
from PyQt6.QtWidgets import QMenu

try:
    import requests
except ImportError:
    requests = None


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: CONSTANTS & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

APP_NAME = "TaskFlow"
APP_VERSION = "6.0"
DATA_DIR_NAME = "TaskFlowV6"

# Colors – dark, gold, cozy
DARK_BG = "#101012"
CARD_BG = "#191920"
HOVER_BG = "#262636"
TEXT_WHITE = "#f2f2f2"
TEXT_GRAY = "#b0b0b8"
GOLD = "#ffd700"
PRESSED_BG = "#303045"

GITHUB_OWNER = "Dyvorn"
GITHUB_REPO = "TaskFlow"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

SECTIONS = ["Today", "Tomorrow", "This Week", "Someday", "Scheduled"]

MOTIVATIONAL_QUOTES = [
    "Small steps lead to big changes.",
    "Progress over perfection.",
    "You are doing enough.",
    "One thing at a time.",
    "Be proud of the effort you put in.",
    "Rest is also part of the work.",
    "You got this.",
    "Your well-being comes first.",
]

MOOD_OPTIONS = [
    "Low energy",
    "Okay",
    "Motivated",
    "Stressed",
    "Great",
]


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3: DATA PATHS & SIMPLE UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def today_str() -> str:
    return str(date.today())


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def get_data_paths() -> Dict[str, str]:
    """Return directory and file paths used by the hub."""
    if os.name == "nt":
        base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), DATA_DIR_NAME)
    else:
        base = os.path.join(os.path.expanduser("~"), f".{DATA_DIR_NAME}")

    os.makedirs(base, exist_ok=True)
    data_file = os.path.join(base, "taskflow_hub_data.json")
    backup_file = os.path.join(base, "taskflow_hub_data.backup.json")
    return {"dir": base, "data": data_file, "backup": backup_file}


def atomic_write_json(path: str, backup_path: str, data: Dict[str, Any]) -> None:
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if os.path.exists(path):
            try:
                os.replace(path, backup_path)
            except OSError:
                # Backup failed; not fatal
                pass
        os.replace(tmp, path)
    except Exception:
        # Last resort: best effort, but never crash app on save
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4: DATA MODEL & STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

def default_state() -> Dict[str, Any]:
    """Initial state for a new user."""
    return {
        "version": APP_VERSION,
        "lastOpened": today_str(),
        "tasks": [],          # list of task dicts
        "projects": [],       # list of project dicts
        "habits": [           # simple predefined habits (can be edited later)
            {"id": str(uuid.uuid4()), "name": "Drink water", "active": True},
            {"id": str(uuid.uuid4()), "name": "Go outside 10 minutes", "active": True},
            {"id": str(uuid.uuid4()), "name": "Study 25 minutes", "active": True},
        ],
        "moods": [],          # list of {"date": "YYYY-MM-DD", "value": str, "note": str}
        "stats": {
            "currentStreak": 0,
            "lastActivityDate": None,
            "xp": 0,
            "level": 1,
            "tasksCompletedToday": 0,
            "plannedTasksToday": 0,
            "targetTasksToday": 0,
            "moodAtStart": None,
            "lastPlanningDate": None,
        },
    }


def validate_and_migrate_state(state: Dict[str, Any]) -> Dict[str, Any]:
    base = default_state()
    for key, value in base.items():
        state.setdefault(key, value)

    # Ensure required subkeys
    state["stats"].setdefault("currentStreak", 0)
    state["stats"].setdefault("lastActivityDate", None)
    state["stats"].setdefault("xp", 0)
    state["stats"].setdefault("level", 1)
    state["stats"].setdefault("tasksCompletedToday", 0)
    state["stats"].setdefault("plannedTasksToday", 0)
    state["stats"].setdefault("targetTasksToday", 0)
    state["stats"].setdefault("moodAtStart", None)
    state["stats"].setdefault("lastPlanningDate", None)

    # Normalize tasks
    fixed_tasks: List[Dict[str, Any]] = []
    for t in state.get("tasks", []):
        if not isinstance(t, dict):
            continue
        t.setdefault("id", str(uuid.uuid4()))
        t.setdefault("text", "")
        t.setdefault("completed", False)
        t.setdefault("section", "Today")
        if t["section"] not in SECTIONS:
            t["section"] = "Today"
        t.setdefault("order", 0)
        t.setdefault("projectId", None)
        t.setdefault("createdAt", now_iso())
        t.setdefault("updatedAt", now_iso())
        t.setdefault("dueDate", None)   # "YYYY-MM-DD" or None
        t.setdefault("dueTime", None)   # "HH:MM" or None
        t.setdefault("important", False)
        t.setdefault("steps", [])       # list of {"id", "text", "completed"}
        fixed_tasks.append(t)
    state["tasks"] = fixed_tasks

    # Normalize projects
    fixed_projects: List[Dict[str, Any]] = []
    for p in state.get("projects", []):
        if not isinstance(p, dict):
            continue
        p.setdefault("id", str(uuid.uuid4()))
        p.setdefault("name", "Untitled")
        p.setdefault("color", GOLD)
        p.setdefault("createdAt", now_iso())
        fixed_projects.append(p)
    state["projects"] = fixed_projects

    # Normalize habits
    fixed_habits: List[Dict[str, Any]] = []
    for h in state.get("habits", []):
        if not isinstance(h, dict):
            continue
        h.setdefault("id", str(uuid.uuid4()))
        h.setdefault("name", "Habit")
        h.setdefault("active", True)
        fixed_habits.append(h)
    state["habits"] = fixed_habits

    # Normalize habit checks
    if "habitChecks" not in state or not isinstance(state["habitChecks"], dict):
        state["habitChecks"] = {}

    # Normalize moods
    fixed_moods: List[Dict[str, Any]] = []
    for m in state.get("moods", []):
        if not isinstance(m, dict):
            continue
        m.setdefault("date", today_str())
        m.setdefault("value", "Okay")
        m.setdefault("note", "")
        fixed_moods.append(m)
    state["moods"] = fixed_moods

    return state


def load_state(paths: Dict[str, str]) -> Dict[str, Any]:
    path = paths["data"]
    backup = paths["backup"]

    if not os.path.exists(path):
        return default_state()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return validate_and_migrate_state(data)
    except Exception:
        # Try backup
        if os.path.exists(backup):
            try:
                with open(backup, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return validate_and_migrate_state(data)
            except Exception:
                pass
        # Fall back to fresh state
        return default_state()


def save_state(paths: Dict[str, str], state: Dict[str, Any]) -> None:
    state["lastOpened"] = today_str()
    atomic_write_json(paths["data"], paths["backup"], state)


def get_today_mood(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    today = today_str()
    for m in state.get("moods", []):
        if m.get("date") == today:
            return m
    return None


def set_today_mood(state: Dict[str, Any], value: str, note: str = "") -> None:
    today = today_str()
    moods = state.setdefault("moods", [])
    for m in moods:
        if m.get("date") == today:
            m["value"] = value
            m["note"] = note
            return
    moods.append({"date": today, "value": value, "note": note})


def count_today_tasks(state: Dict[str, Any]) -> Dict[str, int]:
    today_tasks = [t for t in state.get("tasks", []) if t.get("section") == "Today"]
    done = [t for t in today_tasks if t.get("completed")]
    return {"total": len(today_tasks), "completed": len(done)}

def add_task(
    state: Dict[str, Any],
    text: str,
    section: str = "Today",
    project_id: Optional[str] = None,
    important: bool = False,
) -> Dict[str, Any]:
    if section not in SECTIONS:
        section = "Today"
    task = {
        "id": str(uuid.uuid4()),
        "text": text,
        "completed": False,
        "section": section,
        "order": 0,
        "projectId": project_id,
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
        "dueDate": None,
        "dueTime": None,
        "important": important,
        "steps": [],
    }
    state.setdefault("tasks", []).append(task)
    return task


def tasks_in_section(state: Dict[str, Any], section: str) -> List[Dict[str, Any]]:
    tasks = [
        t for t in state.get("tasks", [])
        if t.get("section") == section
    ]

    def sort_key(t: Dict[str, Any]) -> Any:
        return (
            t.get("order", 0),
            0 if t.get("important") else 1,
            0 if not t.get("completed") else 1,
            t.get("createdAt", ""),
        )

    return sorted(tasks, key=sort_key)


def toggle_task_completed(state: Dict[str, Any], task_id: str) -> Optional[Dict[str, Any]]:
    for t in state.get("tasks", []):
        if t.get("id") == task_id:
            t["completed"] = not t.get("completed")
            t["updatedAt"] = now_iso()

            if t["completed"]:
                today = today_str()
                stats = state.setdefault("stats", {})
                stats.setdefault("tasksCompletedToday", 0)
                stats.setdefault("lastActivityDate", None)
                stats.setdefault("currentStreak", 0)

                if stats["lastActivityDate"] != today:
                    last = stats["lastActivityDate"]
                    if last:
                        try:
                            prev = date.fromisoformat(last)
                            diff = (date.fromisoformat(today) - prev).days
                            if diff == 1:
                                stats["currentStreak"] += 1
                            else:
                                stats["currentStreak"] = 1
                        except ValueError:
                            stats["currentStreak"] = 1
                    else:
                        stats["currentStreak"] = 1
                    stats["tasksCompletedToday"] = 1
                else:
                    stats["tasksCompletedToday"] += 1

                stats["lastActivityDate"] = today
            return t
    return None


def delete_task(state: Dict[str, Any], task_id: str) -> None:
    tasks = state.get("tasks", [])
    state["tasks"] = [t for t in tasks if t.get("id") != task_id]


def get_project_by_id(state: Dict[str, Any], project_id: str) -> Optional[Dict[str, Any]]:
    for p in state.get("projects", []):
        if p.get("id") == project_id:
            return p
    return None


def add_project(state: Dict[str, Any], name: str) -> Dict[str, Any]:
    proj = {
        "id": str(uuid.uuid4()),
        "name": name or "Untitled",
        "color": GOLD,
        "createdAt": now_iso(),
    }
    state.setdefault("projects", []).append(proj)
    return proj


def tasks_for_project(state: Dict[str, Any], project_id: str) -> List[Dict[str, Any]]:
    return [
        t for t in state.get("tasks", [])
        if t.get("projectId") == project_id
    ]


def get_today_habit_checks(state: Dict[str, Any]) -> Dict[str, bool]:
    """Return dict habit_id -> checked(bool) for today."""
    today = today_str()
    checks = state.setdefault("habitChecks", {})  # new dict: date -> {habit_id: bool}
    return checks.setdefault(today, {})


def set_habit_checked(state: Dict[str, Any], habit_id: str, checked: bool) -> None:
    today = today_str()
    checks = state.setdefault("habitChecks", {})
    day = checks.setdefault(today, {})
    day[habit_id] = checked


def rollover_tasks(state: dict) -> None:
    """Move tasks from Today to Tomorrow, and Tomorrow to Today, on a new day."""
    today = today_str()
    last_opened = state.get("lastOpened")

    if not last_opened or last_opened == today:
        return

    try:
        last_date = date.fromisoformat(last_opened)
        today_date = date.fromisoformat(today)
        if (today_date - last_date).days < 1:
            return
    except (ValueError, TypeError):
        return

    for task in state.get("tasks", []):
        if not task.get("completed"):
            if task.get("section") == "Today":
                task["section"] = "Tomorrow"
            elif task.get("section") == "Tomorrow":
                task["section"] = "Today"
    state["lastOpened"] = today_str()

def parse_version_tuple(v: str) -> tuple:
    """Convert version string like '6.0' or 'v6.0.1' to tuple of ints."""
    v = v.strip()
    if v.lower().startswith("v"):
        v = v[1:]
    parts = v.split(".")
    nums = []
    for p in parts:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    # Ensure at least 2 components
    while len(nums) < 2:
        nums.append(0)
    return tuple(nums)

def is_newer_version(latest: str, current: str) -> bool:
    return parse_version_tuple(latest) > parse_version_tuple(current)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5: HUB WINDOW - BASE & HOME TAB
# ═══════════════════════════════════════════════════════════════════════════

class HubWindow(QMainWindow):
    """Main planning & mental health hub."""

    def __init__(self, state: Dict[str, Any], paths: Dict[str, str]):
        super().__init__()
        self.state = state
        self.paths = paths

        self.setWindowTitle(f"{APP_NAME} Hub v{APP_VERSION}")
        self.resize(1200, 800)
        self._save_timer = QTimer(self)
        self._save_timer.setInterval(800)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._do_save)

        self._build_ui()
        self._refresh_home()

        # Check for updates silently in the background
        self._check_updates_async()
        self._run_daily_planning()

    # ────────────────────────────────────────────────────────────────────
    # UI construction
    # ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {DARK_BG};
            }}
            QLabel#TitleLabel {{
                color: {GOLD};
                font-size: 20px;
                font-weight: bold;
            }}
            QLabel {{
                color: {TEXT_WHITE};
            }}
            QTextEdit, QComboBox {{
                background-color: {CARD_BG};
                color: {TEXT_WHITE};
                border-radius: 8px;
                border: 1px solid {HOVER_BG};
            }}
            QPushButton {{
                background-color: {CARD_BG};
                color: {TEXT_WHITE};
                border-radius: 8px;
                border: 1px solid {HOVER_BG};
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {HOVER_BG};
            }}
            QPushButton:pressed {{
                background-color: {PRESSED_BG};
            }}
            QListWidget {{
                background-color: {CARD_BG};
                color: {TEXT_WHITE};
                border-radius: 8px;
                border: 1px solid {HOVER_BG};
            }}
        """)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # Left navigation
        nav_frame = QFrame()
        nav_frame.setFixedWidth(180)
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(8)

        title = QLabel(f"{APP_NAME} Hub")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(title)

        nav_layout.addSpacing(6)

        self.btn_home = QPushButton("🏠 Home")
        self.btn_today = QPushButton("📅 Today")
        self.btn_week = QPushButton("🗓 This Week")
        self.btn_someday = QPushButton("🌙 Someday")
        self.btn_projects = QPushButton("📁 Projects")
        self.btn_stats = QPushButton("📊 Stats")

        for btn in [
            self.btn_home,
            self.btn_today,
            self.btn_week,
            self.btn_someday,
            self.btn_projects,
            self.btn_stats,
        ]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(32)
            nav_layout.addWidget(btn)

        self.btn_check_updates = QPushButton("🔄 Check updates")
        self.btn_check_updates.setCursor(Qt.CursorShape.PointingHandCursor)
        nav_layout.addWidget(self.btn_check_updates)

        nav_layout.addStretch(1)

        self.btn_quit = QPushButton("Exit Hub")
        self.btn_quit.setCursor(Qt.CursorShape.PointingHandCursor)
        nav_layout.addWidget(self.btn_quit)

        root.addWidget(nav_frame)

        # Right stacked pages
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        # Home page
        self.page_home = QWidget()
        home_layout = QVBoxLayout(self.page_home)
        home_layout.setContentsMargins(12, 12, 12, 12)
        home_layout.setSpacing(10)

        self.home_title = QLabel("Today Check‑In")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.home_title.setFont(font)
        home_layout.addWidget(self.home_title)

        self.mood_label = QLabel("How are you feeling today?")
        home_layout.addWidget(self.mood_label)

        mood_row = QHBoxLayout()
        self.mood_combo = QComboBox()
        self.mood_combo.addItems(MOOD_OPTIONS)
        self.mood_save_btn = QPushButton("Save mood")
        mood_row.addWidget(self.mood_combo, 1)
        mood_row.addWidget(self.mood_save_btn)
        home_layout.addLayout(mood_row)

        self.mood_note = QTextEdit()
        self.mood_note.setPlaceholderText("Optional: write a few words about your day.")
        self.mood_note.setFixedHeight(80)
        home_layout.addWidget(self.mood_note)

        self.mood_message = QLabel("")
        self.mood_message.setWordWrap(True)
        self.mood_message.setStyleSheet(f"color: {TEXT_GRAY};")
        home_layout.addWidget(self.mood_message)

        # Today summary
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {HOVER_BG};")
        home_layout.addWidget(line)

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        home_layout.addWidget(self.summary_label)

        # Motivational quote
        spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        home_layout.addItem(spacer)

        self.quote_label = QLabel("")
        self.quote_label.setWordWrap(True)
        self.quote_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.quote_label.setStyleSheet(f"color: {TEXT_GRAY}; font-style: italic;")
        home_layout.addWidget(self.quote_label)

                # Today page
        self.page_today = TaskListWidget(self.state, "Today", self._schedule_save)
        # Margins are now handled inside the TaskListWidget itself for better encapsulation.

        # This Week page
        self.page_week = TaskListWidget(self.state, "This Week", self._schedule_save)
        # Margins are now handled inside the TaskListWidget itself for better encapsulation.

        # Someday page
        self.page_someday = TaskListWidget(self.state, "Someday", self._schedule_save)
        # Margins are now handled inside the TaskListWidget itself for better encapsulation.

        # Projects page
        self.page_projects = QWidget()
        proj_layout = QVBoxLayout(self.page_projects)
        proj_layout.setContentsMargins(12, 12, 12, 12)
        proj_layout.setSpacing(10)

        proj_title = QLabel("Projects")
        f_proj = proj_title.font()
        f_proj.setPointSize(14)
        f_proj.setBold(True)
        proj_title.setFont(f_proj)
        proj_layout.addWidget(proj_title)

        header_proj = QHBoxLayout()
        self.btn_add_project = QPushButton("New project")
        self.btn_add_project.setFixedHeight(28)
        header_proj.addStretch(1)
        header_proj.addWidget(self.btn_add_project)
        proj_layout.addLayout(header_proj)

        content_proj = QHBoxLayout()
        proj_layout.addLayout(content_proj, 1)

        # left: project list
        self.project_list = QListWidget()
        self.project_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.project_list.setMinimumWidth(220)
        content_proj.addWidget(self.project_list, 0)

        # right: project detail (tasks summary)
        self.project_detail = QTextEdit()
        self.project_detail.setReadOnly(True)
        self.project_detail.setPlaceholderText("Select a project to see its tasks.")
        content_proj.addWidget(self.project_detail, 1)

        # Stats & Habits page
        self.page_stats = QWidget()
        stats_layout = QVBoxLayout(self.page_stats)
        stats_layout.setContentsMargins(12, 12, 12, 12)
        stats_layout.setSpacing(10)

        stats_title = QLabel("Stats & Habits")
        f_stats = stats_title.font()
        f_stats.setPointSize(14)
        f_stats.setBold(True)
        stats_title.setFont(f_stats)
        stats_layout.addWidget(stats_title)

        # Streak + tasks
        self.stats_summary_label = QLabel("")
        self.stats_summary_label.setWordWrap(True)
        stats_layout.addWidget(self.stats_summary_label)

        line_stats = QFrame()
        line_stats.setFrameShape(QFrame.Shape.HLine)
        line_stats.setStyleSheet(f"color: {HOVER_BG};")
        stats_layout.addWidget(line_stats)

        # Habits list
        habits_title = QLabel("Today’s habits")
        habits_title.setStyleSheet(f"color: {TEXT_WHITE}; font-weight: bold;")
        stats_layout.addWidget(habits_title)

        self.habits_list = QListWidget()
        stats_layout.addWidget(self.habits_list, 1)

        self.habit_message = QLabel("")
        self.habit_message.setWordWrap(True)
        self.habit_message.setStyleSheet(f"color: {TEXT_GRAY}; font-style: italic;")
        stats_layout.addWidget(self.habit_message)

        # Add all pages to stacked widget
        self.stack.addWidget(self.page_home)
        self.stack.addWidget(self.page_today)
        self.stack.addWidget(self.page_week)
        self.stack.addWidget(self.page_someday)
        self.stack.addWidget(self.page_projects)
        self.stack.addWidget(self.page_stats)


        # Connect navigation
        self.btn_home.clicked.connect(lambda: self._switch_page(self.page_home))
        self.btn_today.clicked.connect(lambda: self._switch_page(self.page_today))
        self.btn_week.clicked.connect(lambda: self._switch_page(self.page_week))
        self.btn_someday.clicked.connect(lambda: self._switch_page(self.page_someday))
        self.btn_projects.clicked.connect(lambda: self._switch_page(self.page_projects))
        self.btn_stats.clicked.connect(lambda: self._switch_page(self.page_stats))
        self.btn_quit.clicked.connect(self.close)

        self.mood_save_btn.clicked.connect(self._on_save_mood)

        # Projects signals
        self.btn_add_project.clicked.connect(self._on_add_project)
        self.project_list.itemSelectionChanged.connect(self._on_project_selected)
        self.btn_check_updates.clicked.connect(self._check_updates_async)


    def _make_placeholder_page(self, text: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        layout.addStretch(1)
        return page

    # ────────────────────────────────────────────────────────────────────
    # Navigation & updates
    # ────────────────────────────────────────────────────────────────────
    
    def _animate_page_in(self):
        effect = QGraphicsOpacityEffect(self.stack)
        self.stack.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _switch_page(self, page: QWidget) -> None:
        if self.stack.currentWidget() is page:
            return

        self.stack.setCurrentWidget(page)

        if page is self.page_home:
            self._refresh_home()
        elif page is self.page_today:
            self.page_today.refresh()
        elif page is self.page_week:
            self.page_week.refresh()
        elif page is self.page_someday:
            self.page_someday.refresh()
        elif page is self.page_projects:
            self._refresh_projects()
        elif page is self.page_stats:
            self._refresh_stats_and_habits()


    def _refresh_home(self) -> None:
        # Mood
        mood = get_today_mood(self.state)
        if mood:
            value = mood.get("value", "Okay")
            note = mood.get("note", "")
            idx = self.mood_combo.findText(value)
            if idx >= 0:
                self.mood_combo.setCurrentIndex(idx)
            else:
                self.mood_combo.setCurrentIndex(0)
            self.mood_note.setPlainText(note)
            self.mood_message.setText(self._mood_message_for_value(value))
        else:
            self.mood_combo.setCurrentIndex(0)
            self.mood_note.clear()
            self.mood_message.setText("There are good days and bad days. You still deserve kindness on all of them.")

        # Today summary
        counts = count_today_tasks(self.state)
        total = counts["total"]
        done = counts["completed"]

        if total == 0:
            summary_text = "You have no tasks in Today yet. You can keep it light or send a few tasks here later."
        else:
            if done == 0:
                summary_text = f"You planned {total} tasks for today. Even one step is progress."
            elif done < total:
                summary_text = f"You completed {done} of {total} tasks today. That already counts."
            else:
                summary_text = f"You completed all {total} tasks you planned for today. That’s amazing."

        extra = ""
        if total > 0 and done == 0:
            extra = "You don’t have to finish everything. One tiny step is still progress."
        elif 0 < done < total:
            extra = "You’re in motion. You’re allowed to stop when your energy runs low."
        elif total > 0 and done == total:
            extra = "You cleared today’s plan. Anything else is pure bonus."

        self.summary_label.setText(summary_text + ("\n" + extra if extra else ""))

        # Quote (simple deterministic choice)
        idx = hash(today_str()) % len(MOTIVATIONAL_QUOTES)
        self.quote_label.setText(MOTIVATIONAL_QUOTES[idx])

    def _mood_message_for_value(self, value: str) -> str:
        if value == "Low energy":
            return "Low days happen. You’re still allowed to go slow and do tiny steps."
        if value == "Stressed":
            return "Stress is heavy. You don’t have to win the whole day, just make it softer."
        if value == "Okay":
            return "An okay day is still a real day. One or two gentle wins are enough."
        if value == "Motivated":
            return "Nice, you’re motivated. Let’s use that energy without burning you out."
        if value == "Great":
            return "Enjoy the good days. You don’t need to be perfect to deserve them."
        return "There are good days and bad days. You still deserve kindness on all of them."

    def _run_daily_planning(self):
        stats = self.state.setdefault("stats", {})
        if stats.get("lastPlanningDate") == today_str():
            return

        mood = get_today_mood(self.state)
        mood_value = mood.get("value", "Okay") if mood else "Okay"

        num, ok = QInputDialog.getInt(
            self,
            "Daily Planning",
            "How many tasks do you realistically want to focus on today?",
            value=0, min=0, max=5
        )

        if ok:
            stats["plannedTasksToday"] = num
            stats["targetTasksToday"] = num
            stats["moodAtStart"] = mood_value
            stats["lastPlanningDate"] = today_str()
            self._schedule_save()
    # ────────────────────────────────────────────────────────────────────
    # Projects page
    # ────────────────────────────────────────────────────────────────────

    def _refresh_projects(self) -> None:
        self.project_list.clear()
        for p in self.state.get("projects", []):
            item = QListWidgetItem(p.get("name", "Untitled"))
            item.setData(Qt.ItemDataRole.UserRole, p.get("id"))
            self.project_list.addItem(item)
        self.project_detail.clear()
        self.project_detail.setPlainText("Select a project to see its tasks.")

    def _on_add_project(self) -> None:
        name = f"Project {len(self.state.get('projects', [])) + 1}"
        add_project(self.state, name)
        self._schedule_save()
        self._refresh_projects()

    def _on_project_selected(self) -> None:
        items = self.project_list.selectedItems()
        if not items:
            self.project_detail.clear()
            self.project_detail.setPlainText("Select a project to see its tasks.")
            return
        item = items[0]
        pid = item.data(Qt.ItemDataRole.UserRole)
        proj = get_project_by_id(self.state, pid)
        if not proj:
            self.project_detail.clear()
            self.project_detail.setPlainText("Project not found.")
            return

        tasks = tasks_for_project(self.state, pid)
        if not tasks:
            text = f"{proj.get('name', 'Untitled')}\n\nNo tasks yet in this project."
        else:
            lines = [f"{proj.get('name', 'Untitled')}", ""]
            for t in tasks:
                mark = "✔" if t.get("completed") else "•"
                lines.append(f"{mark} {t.get('text', '')}")
            text = "\n".join(lines)
        self.project_detail.setPlainText(text)

    # ────────────────────────────────────────────────────────────────────
    # Stats & habits page
    # ────────────────────────────────────────────────────────────────────

    def _refresh_stats_and_habits(self) -> None:
        stats = self.state.get("stats", {})
        streak = stats.get("currentStreak", 0)
        done_today = stats.get("tasksCompletedToday", 0)
        planned = stats.get("plannedTasksToday", 0)
        mood_start = stats.get("moodAtStart")

        if streak <= 0:
            streak_msg = "You don't have an active streak yet. That’s okay; you can start any day."
        elif streak == 1:
            streak_msg = "You have a 1‑day streak. That first step already counts."
        else:
            streak_msg = f"You have a {streak}‑day streak. That's a lot of small wins."

        if planned > 0:
            tasks_msg = f"You planned {planned} task(s) and completed {done_today}."
        elif done_today == 0:
            tasks_msg = "You haven't completed any tasks today yet. Even one tiny thing is enough."
        else:
            tasks_msg = f"You completed {done_today} task(s) today. Your effort matters."

        mood_start_msg = f"Mood at start: {mood_start}" if mood_start else ""

        mood = get_today_mood(self.state)
        encouragement = ""
        if mood:
            val = mood.get("value", "")
            if val in ("Low energy", "Stressed"):
                if done_today > 0:
                    encouragement = "You did something on a hard day. That really counts."
                else:
                    encouragement = "On heavy days, just breathing and existing is already work."
            elif val in ("Motivated", "Great"):
                encouragement = "Nice energy today. Use it gently, not to exhaust yourself."
        else:
            encouragement = "However you feel today is valid. You’re allowed to go at your pace."

        self.stats_summary_label.setText(
            "\n".join(filter(None, [streak_msg, tasks_msg, mood_start_msg, encouragement]))
        )

        # Habits list
        self.habits_list.clear()
        checks = get_today_habit_checks(self.state)
        for h in self.state.get("habits", []):
            if not h.get("active", True):
                continue
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, h.get("id"))

            row = QWidget()
            hl = QHBoxLayout(row)
            hl.setContentsMargins(6, 2, 6, 2)
            hl.setSpacing(6)

            btn = QPushButton("✔" if checks.get(h["id"], False) else "")
            btn.setCheckable(True)
            btn.setChecked(checks.get(h["id"], False))
            btn.setFixedSize(QSize(22, 22))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border-radius: 11px;
                    border: 1px solid {HOVER_BG};
                    color: {GOLD};
                    font-weight: bold;
                }}
                QPushButton:checked {{
                    background-color: {GOLD};
                    color: {DARK_BG};
                }}
            """)

            lbl = QLabel(h.get("name", "Habit"))
            lbl.setStyleSheet(f"color: {TEXT_WHITE};")

            hl.addWidget(btn)
            hl.addWidget(lbl, 1)

            self.habits_list.addItem(item)
            self.habits_list.setItemWidget(item, row)

            btn.clicked.connect(
                lambda checked, hid=h["id"]: self._on_toggle_habit(hid, checked)
            )

    def _on_toggle_habit(self, habit_id: str, checked: bool) -> None:
        set_habit_checked(self.state, habit_id, checked)
        if checked:
            self.habit_message.setText("Nice, that’s one small win for today.")
        else:
            self.habit_message.setText("You can always come back to this habit. Nothing is ruined.")
        self._schedule_save()

    # ────────────────────────────────────────────────────────────────────
    # Updates
    # ────────────────────────────────────────────────────────────────────

    def _check_updates_async(self) -> None:
        """Run on a background thread; fetch latest GitHub release."""
        if requests is None:
            return  # no HTTP support available

        def worker():
            latest_version = None
            download_url = None
            error = None
            try:
                headers = {"Accept": "application/vnd.github+json"}
                resp = requests.get(GITHUB_API_LATEST, headers=headers, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                tag = data.get("tag_name") or ""
                latest_version = tag

                # Find setup.exe asset
                assets = data.get("assets", [])
                for asset in assets:
                    name = asset.get("name", "").lower()
                    if "setup" in name and name.endswith(".exe"):
                        download_url = asset.get("browser_download_url")
                        break
            except Exception as e:
                error = str(e)

            # Back to main thread
            QTimer.singleShot(0, lambda: self._on_update_check_result(latest_version, download_url, error))

        threading.Thread(target=worker, daemon=True).start()

    def _on_update_check_result(self, latest_version: Optional[str], download_url: Optional[str], error: Optional[str]) -> None:
        """Handle update check result on UI thread."""
        if error or not latest_version or not is_newer_version(latest_version, APP_VERSION):
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Update available")
        msg.setText(f"A newer version of TaskFlow Hub is available: {latest_version}.\n\nYour version: {APP_VERSION}.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        if download_url:
            msg.setInformativeText("Do you want to open the download page in your browser?")
            ret = msg.exec()
            if ret == QMessageBox.StandardButton.Ok:
                self._open_update_url(download_url)

    def _open_update_url(self, url: str) -> None:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    # ────────────────────────────────────────────────────────────────────
    # Events & saving
    # ────────────────────────────────────────────────────────────────────

    def _on_save_mood(self) -> None:
        value = self.mood_combo.currentText()
        note = self.mood_note.toPlainText().strip()
        set_today_mood(self.state, value, note)
        self.mood_message.setText(self._mood_message_for_value(value))
        self._schedule_save()

    def _schedule_save(self) -> None:
        self._save_timer.start()

    def _do_save(self) -> None:
        save_state(self.paths, self.state)

    def closeEvent(self, event) -> None:
        self._do_save()
        super().closeEvent(event)
class TaskListWidget(QWidget):
    """Simple vertical task list for a given section."""

    def __init__(self, state: Dict[str, Any], section: str, save_callback, parent=None):
        super().__init__(parent)
        self.state = state
        self.section = section
        self._save_callback = save_callback

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        # Header row
        header = QHBoxLayout()
        lbl = QLabel(section)
        f = lbl.font()
        f.setBold(True)
        lbl.setFont(f)
        header.addWidget(lbl)

        header.addStretch(1)

        self.add_btn = QPushButton("Add")
        self.add_btn.setFixedHeight(26)
        header.addWidget(self.add_btn)

        layout.addLayout(header)

        self.tasks_list = QListWidget()
        self.tasks_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.tasks_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.tasks_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        layout.addWidget(self.tasks_list, 1)

        self.add_btn.clicked.connect(self._on_add_task)
        self.refresh()

    def refresh(self) -> None:
        self.tasks_list.clear()
        for t in tasks_in_section(self.state, self.section):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, t.get("id"))

            row = QWidget()
            row.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            hl = QHBoxLayout(row)
            hl.setContentsMargins(6, 2, 6, 2)
            hl.setSpacing(6)

            chk = QPushButton("✔" if t.get("completed") else "")
            chk.setFixedSize(QSize(22, 22))
            chk.setCheckable(True)
            chk.setChecked(t.get("completed"))
            chk.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border-radius: 11px;
                    border: 1px solid {HOVER_BG};
                    color: {GOLD};
                    font-weight: bold;
                }}
                QPushButton:checked {{
                    background-color: {GOLD};
                    color: {DARK_BG};
                }}
            """)

            lbl = QLabel(t.get("text", ""))
            lbl.setWordWrap(True)
            if t.get("completed"):
                lbl.setStyleSheet(f"color: {TEXT_GRAY}; text-decoration: line-through;")
            else:
                lbl.setStyleSheet(f"color: {TEXT_WHITE};")

            del_btn = QPushButton("×")
            del_btn.setFixedSize(QSize(24, 24))
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    color: {TEXT_GRAY};
                    font-weight: bold;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    color: {GOLD};
                }}
            """)

            hl.addWidget(chk)
            hl.addWidget(lbl, 1)
            hl.addWidget(del_btn)

            self.tasks_list.addItem(item)
            self.tasks_list.setItemWidget(item, row)

            chk.clicked.connect(lambda checked, tid=t.get("id"): self._on_toggle_task(tid))
            del_btn.clicked.connect(lambda checked=False, tid=t.get("id"): self._on_delete_task(tid))
            row.customContextMenuRequested.connect(
                lambda pos, tid=t.get("id"): self._show_task_menu(tid, row.mapToGlobal(pos))
            )

    def _on_add_task(self) -> None:
        add_task(self.state, text=f"New task in {self.section}", section=self.section)
        self._save_callback()
        self.refresh()

    def _on_toggle_task(self, task_id: str) -> None:
        toggle_task_completed(self.state, task_id)
        self._save_callback()
        self.refresh()

    def _on_delete_task(self, task_id: str) -> None:
        delete_task(self.state, task_id)
        self._save_callback()
        self.refresh()
    
    def _show_task_menu(self, task_id: str, pos) -> None:
        task = next((t for t in self.state["tasks"] if t["id"] == task_id), None)
        if not task:
            return

        menu = QMenu()
        rename_action = menu.addAction("Rename")
        move_menu = menu.addMenu("Move to")
        move_today = move_menu.addAction("Today")
        move_week = move_menu.addAction("This Week")
        move_someday = move_menu.addAction("Someday")

        if task["section"] == "Today":
            move_today.setEnabled(False)
        elif task["section"] == "This Week":
            move_week.setEnabled(False)
        elif task["section"] == "Someday":
            move_someday.setEnabled(False)

        action = menu.exec(pos)

        if action == rename_action:
            self._rename_task(task_id)
        elif action == move_today:
            self._move_task(task_id, "Today")
        elif action == move_week:
            self._move_task(task_id, "This Week")
        elif action == move_someday:
            self._move_task(task_id, "Someday")

    def _rename_task(self, task_id: str) -> None:
        task = next((t for t in self.state["tasks"] if t["id"] == task_id), None)
        if not task:
            return

        new_text, ok = QInputDialog.getText(self, "Rename Task", "New name:", text=task["text"])

        if ok and new_text:
            task["text"] = new_text
            task["updatedAt"] = now_iso()
            self._save_callback()
            self.refresh()

    def _move_task(self, task_id: str, new_section: str) -> None:
        task = next((t for t in self.state["tasks"] if t["id"] == task_id), None)
        if task and task["section"] != new_section:
            task["section"] = new_section
            task["updatedAt"] = now_iso()
            self._save_callback()
            self.refresh()

    def dropEvent(self, event) -> None:
        super().dropEvent(event)
        tasks_in_this_section = {t['id']: t for t in self.state['tasks'] if t['section'] == self.section}
        for i in range(self.tasks_list.count()):
            item = self.tasks_list.item(i)
            task_id = item.data(Qt.ItemDataRole.UserRole)
            if task_id in tasks_in_this_section:
                task = tasks_in_this_section[task_id]
                if task.get("order") != i:
                    task['order'] = i
                    task['updatedAt'] = now_iso()
        self._save_callback()

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6: ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    app = QApplication(sys.argv)
    paths = get_data_paths()
    state = load_state(paths)
    rollover_tasks(state)
    save_state(paths, state)
    window = HubWindow(state, paths)
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
