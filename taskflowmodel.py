# ============================================================================
# TASKFLOW HUB V6.0 - DATA MODEL
# ============================================================================

import os
import json
import uuid
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

APP_NAME = "TaskFlow"
APP_VERSION = "6.0"
DATA_DIR_NAME = "TaskFlowV6"

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
        "tasks": [],
        "projects": [],
        "habits": [
            {"id": str(uuid.uuid4()), "name": "Drink water", "active": True},
            {"id": str(uuid.uuid4()), "name": "Go outside 10 minutes", "active": True},
            {"id": str(uuid.uuid4()), "name": "Study 25 minutes", "active": True},
        ],
        "ideas": [],
        "notes": [],
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
            "weeklyFocus": [],
            "lastWeeklyReset": None,
            "focusSessions": {},
            "lastIgnoredVersion": None,
            "tasksCompletedByProject": {},
            "habitsCompletedByDay": {},
            "moodsByDate": {},
        },
        # dayQuality: stores {date, tasksCompleted, tasksPlanned, moodAtStart, moodAtEnd, habitsDone}
        "dayQuality": {},
        "uiGeometry": None,
    }


def validate_and_migrate_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure all expected keys exist; repair tasks if needed."""
    base = default_state()
    for key, value in base.items():
        state.setdefault(key, value)

    stats = state.setdefault("stats", {})
    stats.setdefault("currentStreak", 0)
    stats.setdefault("lastActivityDate", None)
    stats.setdefault("xp", 0)
    stats.setdefault("level", 1)
    stats.setdefault("tasksCompletedToday", 0)
    stats.setdefault("plannedTasksToday", 0)
    stats.setdefault("targetTasksToday", 0)
    stats.setdefault("moodAtStart", None)
    stats.setdefault("lastPlanningDate", None)
    stats.setdefault("weeklyFocus", [])
    stats.setdefault("lastWeeklyReset", None)
    stats.setdefault("focusSessions", {})
    stats.setdefault("lastIgnoredVersion", None)
    stats.setdefault("tasksCompletedByProject", {})
    stats.setdefault("habitsCompletedByDay", {})
    stats.setdefault("moodsByDate", {})

    state.setdefault("ideas", [])
    state.setdefault("notes", [])
    state.setdefault("habitChecks", {})
    state.setdefault("dayQuality", {})
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
    }
    state.setdefault("tasks", []).append(task)
    return task


def tasks_in_section(state: Dict[str, Any], section: str) -> List[Dict[str, Any]]:
    tasks = [t for t in state.get("tasks", []) if t.get("section") == section]
    return sorted(
        tasks,
        key=lambda t: (
            0 if not t.get("completed") else 1,
            0 if t.get("important") else 1,
            t.get("order", 0),
        ),
    )


def toggle_task_completed(state: Dict[str, Any], task_id: str) -> Optional[Dict[str, Any]]:
    for t in state.get("tasks", []):
        if t.get("id") == task_id:
            t["completed"] = not t.get("completed")
            t["updatedAt"] = now_iso()
            return t
    return None


def delete_task(state: Dict[str, Any], task_id: str) -> None:
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
    return proj


def tasks_for_project(state: Dict[str, Any], project_id: str) -> List[Dict[str, Any]]:
    return [t for t in state.get("tasks", []) if t.get("projectId") == project_id]


# ═══════════════════════════════════════════════════════════════════════════
# ROLLOVER / DAILY MAINTENANCE
# ═══════════════════════════════════════════════════════════════════════════


def rollover_tasks(state: Dict[str, Any]) -> None:
    """Move yesterday's 'Tomorrow' tasks into 'Today' when the date changes."""
    today = today_str()
    last_opened = state.get("lastOpened")
    if not last_opened or last_opened == today:
        return

    for task in state.get("tasks", []):
        if not task.get("completed") and task.get("section") == "Tomorrow":
            task["section"] = "Today"
            task["updatedAt"] = now_iso()

    state["lastOpened"] = today
