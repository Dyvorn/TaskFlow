# ============================================================================
# TASKFLOW HUB V7.0 - DATA MODEL
# ============================================================================

import os
import json
import uuid
import shutil
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Callable

# UI Imports (Guarded for non-GUI contexts)
try:
    from PyQt6.QtCore import Qt, QSize, QPoint
    from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
    import html
    UI_LIBS_AVAILABLE = True
except ImportError:
    UI_LIBS_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

APP_NAME = "TaskFlow"
APP_VERSION = "8.0"
DATA_DIR_NAME = "TaskFlowV7"

# Theme colors
GOLD = "#ffd700"
DARK_BG = "#121212"
CARD_BG = "#1E1E1E"
HOVER_BG = "#33FFFFFF"
GLASS_BG = "rgba(25, 25, 32, 180)"
GLASS_BORDER = "rgba(255, 255, 255, 25)"
PRESSED_BG = "#55FFFFFF"
TEXT_WHITE = "#e0e0e0"
TEXT_GRAY = "#cccccc"

# Sections used by the hub
SECTIONS = ["Today", "Tomorrow", "This Week", "Someday", "Scheduled", "Archived"]

# Motivational quotes
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

# Modes: how the app "talks" to you based on mood + progress
MODE_RECOVERY = "Recovery"
MODE_FOCUS = "Focus"
MODE_WRAPUP = "Wrap-up"

# Animation & UX tuning constants
ANIM_DURATION_FAST = 150
ANIM_DURATION_MEDIUM = 250


# Mood options
MOOD_OPTIONS = [
    "Low energy",
    "Okay",
    "Motivated",
    "Stressed",
    "Great",
]

# GitHub update config
GITHUB_OWNER = "Dyvorn"
GITHUB_REPO = "TaskFlow"
GITHUB_API_LATEST = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)


# ═══════════════════════════════════════════════════════════════════════════
# SIMPLE UTILITIES
# ═══════════════════════════════════════════════════════════════════════════


def today_str() -> str:
    return str(date.today())


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def parse_version_tuple(v: str) -> tuple:
    """Turn '6.0.1' or 'v6.0.1' into (6, 0, 1) for safe comparison."""
    try:
        parts = v.strip().lstrip("v").split(".")
        return tuple(int(p) for p in parts)
    except Exception:
        return (0,)


def is_newer_version(latest: str, current: str) -> bool:
    """Return True if latest > current."""
    return parse_version_tuple(latest) > parse_version_tuple(current)


def current_time_of_day() -> str:
    """Return 'morning', 'afternoon', or 'evening' based on local time."""
    hour = datetime.now().hour
    if hour < 12:
        return "morning"
    if hour < 18:
        return "afternoon"
    return "evening"


def determine_today_mode(
    mood_value: Optional[str],
    tasks_completed_today: int,
    planned_tasks_today: int,
) -> str:
    """
    Decide which guidance mode to use today, based on mood and progress.

    - Recovery: low/stressed and little/no progress.
    - Wrap-up: later in the day and plan is mostly or fully met.
    - Focus: default productive mode.
    """
    tod = current_time_of_day()
    low_mood = mood_value in ("Low energy", "Stressed")
    plan_met = planned_tasks_today > 0 and tasks_completed_today >= planned_tasks_today

    if low_mood and tasks_completed_today == 0:
        return MODE_RECOVERY

    if tod == "evening" and (plan_met or tasks_completed_today > 0):
        return MODE_WRAPUP

    return MODE_FOCUS


# ═══════════════════════════════════════════════════════════════════════════
# DATA PATHS & ATOMIC WRITE
# ═══════════════════════════════════════════════════════════════════════════


def get_data_paths() -> Dict[str, str]:
    """Return directory and file paths used by the hub."""
    if os.name == "nt":
        base = os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")),
            DATA_DIR_NAME,
        )
    else:
        base = os.path.join(os.path.expanduser("~"), f".{DATA_DIR_NAME}")

    os.makedirs(base, exist_ok=True)
    data_file = os.path.join(base, "taskflow_hub_data.json")
    backup_file = os.path.join(base, "taskflow_hub_data.backup.json")
    kb_file = os.path.join(base, "knowledge_base.json")
    training_file = os.path.join(base, "user_training.json")
    return {"dir": base, "data": data_file, "backup": backup_file, "kb": kb_file, "training": training_file}


def atomic_write_json(path: str, backup_path: str, data: Dict[str, Any]) -> None:
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if os.path.exists(path):
            try:
                os.replace(path, backup_path)
            except OSError:
                pass
        os.replace(tmp, path)
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# STATE MODEL
# ═══════════════════════════════════════════════════════════════════════════


def default_state() -> Dict[str, Any]:
    """Initial state for a new user."""
    return {
        "version": APP_VERSION,
        "lastOpened": today_str(),
        "userProfile": {
            "name": "Friend",
            "role": "Generalist",
            "style": "Gentle",  # Options: Gentle, Direct, Stoic, Hype
        },
        "tasks": [],
        "activityLog": [],
        "categories": ["Work", "Personal", "Health", "Learning", "Finance", "Dev", "Creative"],
        "projects": [],
        "habits": [
            {"id": str(uuid.uuid4()), "name": "Drink water", "active": True},
            {"id": str(uuid.uuid4()), "name": "Go outside 10 minutes", "active": True},
            {"id": str(uuid.uuid4()), "name": "Study 25 minutes", "active": True},
        ],
        "ideas": [],
        "notes": [],
        "journal": [],
        "moods": [],
        "habitChecks": {},
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
            "lastWeeklyReviewDate": None,
            "weeklyFocus": [],
            "lastWeeklyReset": None,
            "focusSessions": {},
            "lastIgnoredVersion": None,
            "tasksCompletedByProject": {},
            "habitsCompletedByDay": {},
            "moodsByDate": {},
            "dailyLogs": {},
            "didShowBrainDumpOnboarding": False,
        },
        # dayQuality: stores {date, tasksCompleted, tasksPlanned, moodAtStart, moodAtEnd, habitsDone}
        "dayQuality": {},
        "uiGeometry": None,
        "settings": {
            "widgetEnabled": True,
            "widgetTaskCount": 5,
            "widgetDockSide": "right",
            "startWithHubMaximized": True,
            "widgetDocked": True,
            "widgetPos": None,
            "widgetCollapsed": False,
            "closeToTray": True,
            "startWithWindows": False,
            "zenSoundscape": "Silent",
        },
        "widgetCurrentProjectId": None,
    }


def validate_and_migrate_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure all expected keys exist; repair tasks if needed."""
    base = default_state()
    for key, value in base.items():
        state.setdefault(key, value)
        # Ensure critical containers are not None
        if state[key] is None and isinstance(value, (dict, list)):
            state[key] = value

    if not isinstance(state.get("stats"), dict):
        state["stats"] = {}
    stats = state["stats"]
    stats.setdefault("currentStreak", 0)
    stats.setdefault("lastActivityDate", None)
    stats.setdefault("xp", 0)
    stats.setdefault("level", 1)
    stats.setdefault("tasksCompletedToday", 0)
    stats.setdefault("plannedTasksToday", 0)
    stats.setdefault("targetTasksToday", 0)
    stats.setdefault("moodAtStart", None)
    stats.setdefault("lastPlanningDate", None)
    stats.setdefault("lastWeeklyReviewDate", None)
    stats.setdefault("weeklyFocus", [])
    stats.setdefault("lastWeeklyReset", None)
    stats.setdefault("focusSessions", {})
    stats.setdefault("lastIgnoredVersion", None)
    stats.setdefault("tasksCompletedByProject", {})
    stats.setdefault("habitsCompletedByDay", {})
    stats.setdefault("moodsByDate", {})
    stats.setdefault("dailyLogs", {})
    stats.setdefault("didShowBrainDumpOnboarding", False)

    if not isinstance(state.get("userProfile"), dict):
        state["userProfile"] = {"name": "Friend", "role": "Generalist", "style": "Gentle"}
    state["userProfile"].setdefault("style", "Gentle")
    state["userProfile"].setdefault("name", "Friend")

    if not isinstance(state.get("activityLog"), list): state["activityLog"] = []
    if not isinstance(state.get("categories"), list): state["categories"] = ["Work", "Personal", "Health", "Learning", "Finance", "Dev", "Creative"]
    if not isinstance(state.get("ideas"), list): state["ideas"] = []
    if not isinstance(state.get("tasks"), list): state["tasks"] = []
    if not isinstance(state.get("notes"), list): state["notes"] = []
    if not isinstance(state.get("journal"), list): state["journal"] = []
    if not isinstance(state.get("habitChecks"), dict): state["habitChecks"] = {}
    if not isinstance(state.get("dayQuality"), dict): state["dayQuality"] = {}
    state.setdefault("widgetCurrentProjectId", None)

    settings = state.setdefault("settings", {})
    settings.setdefault("widgetEnabled", True)
    settings.setdefault("widgetTaskCount", 5)
    settings.setdefault("widgetDockSide", "right")
    settings.setdefault("startWithHubMaximized", True)
    settings.setdefault("widgetDocked", True)
    settings.setdefault("widgetPos", None)
    settings.setdefault("widgetCollapsed", False)
    settings.setdefault("closeToTray", True)
    settings.setdefault("startWithWindows", False)
    settings.setdefault("zenSoundscape", "Silent")

    # Validate widgetPos: must be [int, int] or None
    w_pos = settings.get("widgetPos")
    if w_pos is not None and (not isinstance(w_pos, list) or len(w_pos) != 2 or not all(isinstance(x, (int, float)) for x in w_pos)):
        settings["widgetPos"] = None

    # Validate widgetDockSide: must be 'left' or 'right'
    if settings.get("widgetDockSide") not in ("left", "right"):
        settings["widgetDockSide"] = "right"

    state.setdefault("uiGeometry", None)

    # Migration for widgetNotes to the new notes structure
    if "widgetNotes" in state and isinstance(state.get("widgetNotes"), dict):
        for date_str, text in state["widgetNotes"].items():
            if text and text.strip():
                scope = f"day:{date_str}"
                exists = any(n for n in state["notes"] if n.get("scope") == scope)
                if not exists:
                    state["notes"].append({
                        "id": str(uuid.uuid4()),
                        "date": date_str,
                        "text": text,
                        "scope": scope,
                        "createdAt": now_iso(),
                        "updatedAt": now_iso(),
                    })
        del state["widgetNotes"]

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
        # Future extension: could add due dates, tags, etc. here
        t.setdefault("createdAt", now_iso())
        t.setdefault("updatedAt", now_iso())
        t.setdefault("important", False)
        t.setdefault("subArea", None)
        t.setdefault("recurrence", None)
        t.setdefault("schedule", None)
        t.setdefault("category", None)
        t.setdefault("completedAt", t["updatedAt"] if t["completed"] else None)
        fixed_tasks.append(t)
    state["tasks"] = fixed_tasks

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
        # If main file is corrupt, rename it so it isn't overwritten by a fresh save
        try:
            os.rename(path, path + ".corrupted")
        except OSError:
            pass

        if os.path.exists(backup):
            try:
                with open(backup, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return validate_and_migrate_state(data)
            except Exception:
                pass
        return default_state()


def save_state(paths: Dict[str, str], state: Dict[str, Any]) -> None:
    state["lastOpened"] = today_str()
    atomic_write_json(paths["data"], paths["backup"], state)


def log_activity(state: Dict[str, Any], action: str, entity_type: str, entity_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
    """Records a user action into the activity log for statistics."""
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": now_iso(),
        "action": action,
        "entityType": entity_type,
        "entityId": entity_id,
        "details": details or {}
    }
    log = state.setdefault("activityLog", [])
    log.append(entry)
    
    # Keep log size manageable (last 10,000 entries)
    if len(log) > 10000:
        state["activityLog"] = log[-10000:]

# ═══════════════════════════════════════════════════════════════════════════
# MOOD & HABITS
# ═══════════════════════════════════════════════════════════════════════════


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


def get_today_habit_checks(state: Dict[str, Any]) -> Dict[str, bool]:
    today = today_str()
    checks = state.setdefault("habitChecks", {})
    return checks.setdefault(today, {})


def set_habit_checked(state: Dict[str, Any], habit_id: str, checked: bool) -> None:
    today = today_str()
    day = state.setdefault("habitChecks", {}).setdefault(today, {})
    day[habit_id] = checked


# ═══════════════════════════════════════════════════════════════════════════
# IDEAS & NOTES
# ═══════════════════════════════════════════════════════════════════════════


def add_idea(
    state: Dict[str, Any],
    text: str,
    project_id: Optional[str] = None,
    mood_value: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a new idea to the state."""
    idea = {
        "id": str(uuid.uuid4()),
        "text": text,
        "createdAt": now_iso(),
        "projectId": project_id,
        "moodValue": mood_value,
    }
    state.setdefault("ideas", []).insert(0, idea)
    return idea


def ideas_for_project(state: Dict[str, Any], project_id: str) -> List[Dict[str, Any]]:
    """Get all ideas for a given project."""
    return [i for i in state.get("ideas", []) if i.get("projectId") == project_id]


def delete_idea(state: Dict[str, Any], idea_id: str) -> None:
    """Remove an idea from the state."""
    state["ideas"] = [i for i in state.get("ideas", []) if i.get("id") != idea_id]


def add_note(state: Dict[str, Any], text: str, scope: str) -> Dict[str, Any]:
    """Add a new note to the state."""
    note = {
        "id": str(uuid.uuid4()),
        "date": today_str(),
        "text": text,
        "scope": scope,
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }
    state.setdefault("notes", []).insert(0, note)
    return note


def notes_for_scope(state: Dict[str, Any], scope: str) -> List[Dict[str, Any]]:
    """Get all notes for a given scope."""
    return [n for n in state.get("notes", []) if n.get("scope") == scope]


def get_today_widget_note(state: Dict[str, Any]) -> str:
    """Gets today's note from the new notes structure for the widget."""
    scope = f"day:{today_str()}"
    today_notes = [n for n in state.get("notes", []) if n.get("scope") == scope]
    return today_notes[0].get("text", "") if today_notes else ""


def set_today_widget_note(state: Dict[str, Any], text: str) -> None:
    """Sets today's note in the new notes structure for the widget."""
    scope = f"day:{today_str()}"
    today_notes = [n for n in state.get("notes", []) if n.get("scope") == scope]
    if today_notes:
        today_notes[0]["text"] = text
        today_notes[0]["updatedAt"] = now_iso()
    else:
        add_note(state, text, scope)


def get_journal_entry(state: Dict[str, Any], date_str: str) -> Optional[Dict[str, Any]]:
    """Retrieve the journal entry for a specific date."""
    for entry in state.get("journal", []):
        if entry.get("date") == date_str:
            return entry
    return None


def set_journal_entry(state: Dict[str, Any], date_str: str, text: str) -> None:
    """Create or update a journal entry."""
    entry = get_journal_entry(state, date_str)
    if entry:
        entry["text"] = text
        entry["updatedAt"] = now_iso()
    else:
        new_entry = {
            "id": str(uuid.uuid4()),
            "date": date_str,
            "text": text,
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
        }
        state.setdefault("journal", []).insert(0, new_entry)
        # Keep sorted by date descending
        state["journal"].sort(key=lambda x: x.get("date", ""), reverse=True)

# ═══════════════════════════════════════════════════════════════════════════
# TASKS & PROJECTS
# ═══════════════════════════════════════════════════════════════════════════


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
    category: Optional[str] = None,
    schedule: Optional[Dict[str, str]] = None,
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
        "important": important,
        "category": category,
        "schedule": schedule,
    }
    state.setdefault("tasks", []).append(task)
    log_activity(state, "created", "task", task["id"], {"text": text, "section": section, "category": category})
    return task


def tasks_in_section(state: Dict[str, Any], section: str) -> List[Dict[str, Any]]:
    tasks = [t for t in state.get("tasks", []) if t.get("section") == section]
    return sorted(
        tasks,
        key=lambda t: (
            0 if not t.get("completed") else 1,
            0 if t.get("important") else 1,
            t.get("schedule", {}).get("date", "9999-99-99") if t.get("schedule") else "9999-99-99",
            t.get("order", 0),
        ),
    )


def _handle_recurrence(state: Dict[str, Any], original_task: Dict[str, Any]) -> None:
    """Creates the next instance of a recurring task."""
    rec = original_task.get("recurrence")
    if not rec or not isinstance(rec, dict): return
    
    rtype = rec.get("type")
    if not rtype: return
    
    # Calculate next date based on Today (completion date)
    today_dt = date.today()
    next_date = None
    
    if rtype == "daily":
        next_date = today_dt + timedelta(days=1)
    elif rtype == "weekly":
        next_date = today_dt + timedelta(weeks=1)
    elif rtype == "monthly":
        y, m = today_dt.year, today_dt.month
        m += 1
        if m > 12:
            m = 1
            y += 1
        try:
            next_date = date(y, m, today_dt.day)
        except ValueError:
            # Handle short months (e.g. Jan 31 -> Feb 28/29)
            # Simple fallback: 1st of the month after next
            next_date = date(y, m + 1, 1) if m < 12 else date(y + 1, 1, 1)
    
    if next_date:
        new_task = original_task.copy()
        new_task["id"] = str(uuid.uuid4())
        new_task["completed"] = False
        new_task["createdAt"] = now_iso()
        new_task["updatedAt"] = now_iso()
        new_task["section"] = "Scheduled"
        new_task["schedule"] = {"date": str(next_date)}
        # Note: We keep the recurrence setting on the new task so it chains forever
        state["tasks"].append(new_task)


def toggle_task_completed(state: Dict[str, Any], task_id: str) -> Optional[Dict[str, Any]]:
    for t in state.get("tasks", []):
        if t.get("id") == task_id:
            was_completed = t.get("completed")
            t["completed"] = not was_completed
            t["updatedAt"] = now_iso()
            
            if t["completed"]:
                t["completedAt"] = now_iso()
            else:
                t["completedAt"] = None
            
            # Handle recurrence on completion
            if t["completed"] and not was_completed and t.get("recurrence"):
                _handle_recurrence(state, t)
                
            action = "completed" if t["completed"] else "uncompleted"
            log_activity(state, action, "task", task_id)
            
            return t
    return None


def delete_task(state: Dict[str, Any], task_id: str) -> None:
    # Find task to log details before deleting
    task = next((t for t in state.get("tasks", []) if t.get("id") == task_id), None)
    if task:
        log_activity(state, "deleted", "task", task_id, {"text": task.get("text")})
    state["tasks"] = [t for t in state.get("tasks", []) if t.get("id") != task_id]


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
    log_activity(state, "created", "project", proj["id"], {"name": name})
    return proj


def tasks_for_project(state: Dict[str, Any], project_id: str) -> List[Dict[str, Any]]:
    return [t for t in state.get("tasks", []) if t.get("projectId") == project_id]


def duplicate_project(state: Dict[str, Any], project_id: str) -> Optional[Dict[str, Any]]:
    """Creates a copy of a project and all its tasks."""
    project = get_project_by_id(state, project_id)
    if not project:
        return None
    
    # Clone project
    new_proj = project.copy()
    new_proj["id"] = str(uuid.uuid4())
    new_proj["name"] = f"{project['name']} (Copy)"
    new_proj["createdAt"] = now_iso()
    state["projects"].append(new_proj)
    
    # Clone tasks
    tasks = tasks_for_project(state, project_id)
    for t in tasks:
        new_task = t.copy()
        new_task["id"] = str(uuid.uuid4())
        new_task["projectId"] = new_proj["id"]
        new_task["createdAt"] = now_iso()
        new_task["updatedAt"] = now_iso()
        state["tasks"].append(new_task)
        
    return new_proj


# ═══════════════════════════════════════════════════════════════════════════
# ROLLOVER / DAILY MAINTENANCE
# ═══════════════════════════════════════════════════════════════════════════


def rollover_tasks(state: Dict[str, Any]) -> None:
    """Move 'Tomorrow' and due 'Scheduled' tasks into 'Today'."""
    today = today_str()
    last_opened = state.get("lastOpened")

    # 1. Tomorrow -> Today (only if new day)
    if last_opened != today:
        for task in state.get("tasks", []):
            if not task.get("completed") and task.get("section") == "Tomorrow":
                task["section"] = "Today"
                task["updatedAt"] = now_iso()

    # 2. Scheduled -> Today (Check all tasks, regardless of last open)
    for task in state.get("tasks", []):
        if task.get("completed"): continue
        
        sched = task.get("schedule")
        if sched and isinstance(sched, dict) and sched.get("date"):
            d = sched["date"]
            # If due date is today or past, and not already in Today/Archived
            if d <= today and task.get("section") not in ("Today", "Archived"):
                task["section"] = "Today"
                task["updatedAt"] = now_iso()

    state["lastOpened"] = today

# ═══════════════════════════════════════════════════════════════════════════
# BACKUP SYSTEM
# ═══════════════════════════════════════════════════════════════════════════

def create_timestamped_backup(paths: Dict[str, str]) -> Optional[str]:
    """Creates a copy of the current data file with a timestamp."""
    try:
        data_path = paths["data"]
        if not os.path.exists(data_path):
            return None
        
        backup_dir = os.path.join(paths["dir"], "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{timestamp}.json"
        dest = os.path.join(backup_dir, filename)
        
        shutil.copy2(data_path, dest)
        return filename
    except Exception:
        return None

def get_backups(paths: Dict[str, str]) -> List[str]:
    """Returns a list of backup filenames sorted by date (newest first)."""
    backup_dir = os.path.join(paths["dir"], "backups")
    if not os.path.exists(backup_dir):
        return []
    files = [f for f in os.listdir(backup_dir) if f.endswith(".json") and f.startswith("backup_")]
    files.sort(reverse=True)
    return files

def restore_backup(paths: Dict[str, str], filename: str) -> bool:
    """Restores a backup file to the main data file."""
    backup_path = os.path.join(paths["dir"], "backups", filename)
    data_path = paths["data"]
    if not os.path.exists(backup_path):
        return False
    try:
        shutil.copy2(backup_path, data_path)
        return True
    except Exception:
        return False

if UI_LIBS_AVAILABLE:
    def create_task_row_widget(
        task: Dict[str, Any],
        on_toggle: Callable[[bool, str], None],
        on_delete: Optional[Callable[[bool, str], None]] = None,
        on_context_menu: Optional[Callable[[QPoint, str], None]] = None,
        on_edit: Optional[Callable[[str], None]] = None,
        on_focus: Optional[Callable[[str], None]] = None,
        show_delete_button: bool = True
    ) -> QWidget:
        """
        Creates a standardized task row widget used in multiple lists.
        """
        row = QWidget()
        row.setObjectName("TaskRow")
        row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        important_style = f"border-left: 3px solid {GOLD};" if task.get("important") else "border-left: 3px solid transparent;"
        row.setStyleSheet(f"""
            #TaskRow {{
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 0.02);
                {important_style}
            }}
            #TaskRow:hover {{ background-color: {HOVER_BG}; }}
        """)
        
        hl = QHBoxLayout(row)
        hl.setContentsMargins(6, 2, 6, 2)
        hl.setSpacing(6)

        chk = QPushButton("✔" if task.get("completed") else "")
        chk.setFixedSize(QSize(22, 22))
        chk.setCheckable(True)
        chk.setChecked(task.get("completed", False))
        chk.setStyleSheet(
            f"""
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
            """
        )

        # Build label with metadata
        text_content = task.get("text", "")
        meta_info = []
        if sched := task.get("schedule"):
            if isinstance(sched, dict) and sched.get("date"):
                date_str = sched['date']
                if sched.get("time"):
                    date_str += f" @ {sched['time']}"
                meta_info.append(f"📅 {date_str}")
        if rec := task.get("recurrence"):
            if isinstance(rec, dict) and rec.get("type"):
                meta_info.append(f"↻ {rec['type']}")
        if cat := task.get("category"):
            meta_info.append(f"🏷 {cat}")

        lbl = QLabel()
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {TEXT_GRAY if task.get('completed') else (GOLD if task.get('important') else TEXT_WHITE)};" + ("text-decoration: line-through;" if task.get("completed") else ""))
        lbl.setToolTip(text_content)
        
        lbl.setText(f"{html.escape(text_content)}<br><span style='color:{TEXT_GRAY}; font-size:10px;'>{'  '.join(meta_info)}</span>" if meta_info else text_content)

        # Focus Button (Zen Mode)
        focus_btn = QPushButton("👁")
        focus_btn.setFixedSize(QSize(24, 24))
        focus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        focus_btn.setToolTip("Focus on this task (Zen Mode)")
        focus_btn.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {TEXT_GRAY}; font-size: 14px; }} QPushButton:hover {{ color: {GOLD}; }}")
        focus_btn.setVisible(not task.get("completed") and on_focus is not None)

        del_btn = QPushButton("×")
        del_btn.setFixedSize(QSize(24, 24))
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {TEXT_GRAY}; font-weight: bold; font-size: 14px; }} QPushButton:hover {{ color: {GOLD}; }}")
        del_btn.setVisible(show_delete_button and on_delete is not None)

        hl.addWidget(chk)
        hl.addWidget(lbl, 1)
        hl.addWidget(focus_btn)
        hl.addWidget(del_btn)

        tid = task.get("id")
        chk.clicked.connect(lambda c, t=tid: on_toggle(c, t))
        if on_focus: focus_btn.clicked.connect(lambda c, t=tid: on_focus(t))
        if on_delete: del_btn.clicked.connect(lambda c, t=tid: on_delete(c, t))
        if on_context_menu:
            row.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            row.customContextMenuRequested.connect(lambda pos, t=tid: on_context_menu(pos, t))
        if on_edit:
            def mouseDoubleClickEvent(event, t=tid):
                if event.button() == Qt.MouseButton.LeftButton: on_edit(t)
            row.mouseDoubleClickEvent = mouseDoubleClickEvent

        return row
