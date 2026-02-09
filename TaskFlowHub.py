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
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer, QSize
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
)


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

        self.stack.addWidget(self.page_home)

        # Placeholder pages for future blocks
        self.page_today = self._make_placeholder_page("Today view coming soon.")
        self.page_week = self._make_placeholder_page("This Week view coming soon.")
        self.page_someday = self._make_placeholder_page("Someday view coming soon.")
        self.page_projects = self._make_placeholder_page("Projects view coming soon.")
        self.page_stats = self._make_placeholder_page("Stats & habits coming soon.")

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

    def _switch_page(self, page: QWidget) -> None:
        self.stack.setCurrentWidget(page)
        if page is self.page_home:
            self._refresh_home()

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

        self.summary_label.setText(summary_text)

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


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6: ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    app = QApplication(sys.argv)
    paths = get_data_paths()
    state = load_state(paths)
    window = HubWindow(state, paths)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
