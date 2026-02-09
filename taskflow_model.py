# ============================================================================
# TASKFLOW HUB V6.0 - DATA MODEL
# ============================================================================

import os
import json
import uuid
from datetime import datetime, date
from typing import Any, Dict, List, Optional

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

APP_NAME = "TaskFlow"
APP_VERSION = "6.0"
DATA_DIR_NAME = "TaskFlowV6"

GOLD = "#ffd700"
DARK_BG = "#121212"
CARD_BG = "#1E1E1E"
HOVER_BG = "#33FFFFFF"
GLASS_BG = "rgba(25, 25, 32, 180)"
GLASS_BORDER = "rgba(255, 255, 255, 25)"
PRESSED_BG = "#55FFFFFF"
TEXT_WHITE = "#e0e0e0"
TEXT_GRAY = "#cccccc"

SECTIONS = ["Today", "Tomorrow", "This Week", "Someday", "Scheduled", "Archived"]

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
# DATA PATHS & SIMPLE UTILITIES
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
                pass
        os.replace(tmp, path)
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass

# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL & STATE MANAGEMENT
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
        "moods": [],
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
        },
    }

def validate_and_migrate_state(state: Dict[str, Any]) -> Dict[str, Any]:
    base = default_state()
    for key, value in base.items():
        state.setdefault(key, value)

    state["stats"].setdefault("currentStreak", 0)
    state["stats"].setdefault("lastActivityDate", None)
    state["stats"].setdefault("xp", 0)
    state["stats"].setdefault("level", 1)
    state["stats"].setdefault("tasksCompletedToday", 0)
    state["stats"].setdefault("plannedTasksToday", 0)
    state["stats"].setdefault("targetTasksToday", 0)
    state["stats"].setdefault("moodAtStart", None)
    state["stats"].setdefault("lastPlanningDate", None)
    state["stats"].setdefault("weeklyFocus", [])
    state["stats"].setdefault("lastWeeklyReset", None)
    state["stats"].setdefault("focusSessions", {})

    fixed_tasks: List[Dict[str, Any]] = []
    for t in state.get("tasks", []):
        if not isinstance(t, dict): continue
        t.setdefault("id", str(uuid.uuid4()))
        t.setdefault("text", "")
        t.setdefault("completed", False)
        t.setdefault("section", "Today")
        if t["section"] not in SECTIONS: t["section"] = "Today"
        t.setdefault("order", 0)
        t.setdefault("projectId", None)
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
            except Exception: pass
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

def add_task(state: Dict[str, Any], text: str, section: str = "Today", project_id: Optional[str] = None, important: bool = False) -> Dict[str, Any]:
    if section not in SECTIONS: section = "Today"
    task = {
        "id": str(uuid.uuid4()), "text": text, "completed": False, "section": section,
        "order": 0, "projectId": project_id, "createdAt": now_iso(), "updatedAt": now_iso(),
        "important": important,
    }
    state.setdefault("tasks", []).append(task)
    return task

def tasks_in_section(state: Dict[str, Any], section: str) -> List[Dict[str, Any]]:
    tasks = [t for t in state.get("tasks", []) if t.get("section") == section]
    return sorted(tasks, key=lambda t: (0 if not t.get("completed") else 1, 0 if t.get("important") else 1, t.get("order", 0)))

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
    proj = {"id": str(uuid.uuid4()), "name": name or "Untitled", "color": GOLD, "createdAt": now_iso()}
    state.setdefault("projects", []).append(proj)
    return proj

def tasks_for_project(state: Dict[str, Any], project_id: str) -> List[Dict[str, Any]]:
    return [t for t in state.get("tasks", []) if t.get("projectId") == project_id]

def get_today_habit_checks(state: Dict[str, Any]) -> Dict[str, bool]:
    today = today_str()
    checks = state.setdefault("habitChecks", {})
    return checks.setdefault(today, {})

def set_habit_checked(state: Dict[str, Any], habit_id: str, checked: bool) -> None:
    today = today_str()
    day = state.setdefault("habitChecks", {}).setdefault(today, {})
    day[habit_id] = checked

def rollover_tasks(state: dict) -> None:
    today = today_str()
    last_opened = state.get("lastOpened")
    if not last_opened or last_opened == today: return
    for task in state.get("tasks", []):
        if not task.get("completed"):
            if task.get("section") == "Tomorrow": task["section"] = "Today"
    state["lastOpened"] = today_str()