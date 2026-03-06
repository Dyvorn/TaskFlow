# ============================================================================
# TASKFLOW HUB V7.0 - DATA MODEL
# ============================================================================

import os
import json
import uuid
import shutil
import math
import re
import random
import calendar
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Callable

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

APP_NAME = "TaskFlow"
APP_VERSION = "10.0"
DATA_DIR_NAME = "TaskFlow_Data"

# Theme colors
GOLD = "#ffd700"
DARK_BG = "#121212"
CARD_BG = "#1E1E1E"
HOVER_BG = "rgba(255, 255, 255, 0.15)"
GLASS_BG = "rgba(25, 25, 32, 180)"
GLASS_BORDER = "rgba(255, 255, 255, 25)"
PRESSED_BG = "rgba(255, 255, 255, 0.25)"
TEXT_WHITE = "#e0e0e0"
TEXT_GRAY = "#a0a0a0"

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


def get_user_name(state: Dict[str, Any]) -> str:
    """Safely retrieve the user's name from the profile."""
    return state.get("userProfile", {}).get("name", "Friend")

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


def parse_task_input(text: str) -> Dict[str, Any]:
    """
    Parses a raw input string to extract text, section, category, and importance.
    """
    text = text.strip()
    section = "Today" # Default
    important = False
    category = None
    tags = []
    
    # Priority
    if "!" in text or "urgent" in text.lower():
        important = True
        text = text.replace("!", "").replace("urgent", "", 1).strip()
        
    # Category hashtags
    match = re.search(r"#(\w+)", text)
    if match:
        category = match.group(1)
        text = text.replace(match.group(0), "").strip()

    # Tags (@tag)
    tags_found = re.findall(r"@(\w+)", text)
    if tags_found:
        tags = tags_found
        text = re.sub(r"@(\w+)", "", text).strip()
        
    # Section keywords
    lower = text.lower()
    if "tomorrow" in lower: 
        section = "Tomorrow"
    elif "week" in lower and "next" not in lower: # "this week"
        section = "This Week"
    elif "someday" in lower: 
        section = "Someday"
        
    return {
        "text": text,
        "section": section,
        "category": category,
        "important": important,
        "tags": tags
    }

# ═══════════════════════════════════════════════════════════════════════════
# ANALYTICS HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def get_completion_rate(state: Dict[str, Any]) -> float:
    tasks = state.get("tasks", [])
    if not tasks: return 0.0
    completed = sum(1 for t in tasks if t.get("completed"))
    return (completed / len(tasks)) * 100

def get_most_productive_hour(state: Dict[str, Any]) -> int:
    log = state.get("activityLog", [])
    hours = {}
    for entry in log:
        if entry.get("action") == "completed":
            try:
                dt = datetime.fromisoformat(entry["timestamp"])
                h = dt.hour
                hours[h] = hours.get(h, 0) + 1
            except: pass
    if not hours: return 9
    return max(hours, key=hours.get)

def get_category_breakdown(state: Dict[str, Any]) -> Dict[str, int]:
    tasks = state.get("tasks", [])
    counts = {}
    for t in tasks:
        if t.get("completed"):
            cat = t.get("category", "Uncategorized") or "Uncategorized"
            counts[cat] = counts.get(cat, 0) + 1
    return counts

def get_productivity_score(state: Dict[str, Any]) -> int:
    today = today_str()
    tasks = state.get("tasks", [])
    completed_today = sum(1 for t in tasks if t.get("completed") and t.get("completedAt", "").startswith(today))
    checks = state.get("habitChecks", {}).get(today, {})
    habits_done = sum(1 for v in checks.values() if v)
    return min(100, (completed_today * 10) + (habits_done * 5))

def get_hourly_activity(state: Dict[str, Any]) -> Dict[int, int]:
    log = state.get("activityLog", [])
    hours = {h: 0 for h in range(24)}
    for entry in log:
        try:
            dt = datetime.fromisoformat(entry["timestamp"])
            hours[dt.hour] += 1
        except: pass
    return hours

def get_activity_heatmap_data(state: Dict[str, Any]) -> Dict[str, int]:
    log = state.get("activityLog", [])
    data = {}
    for entry in log:
        ts = entry.get("timestamp", "")
        if ts:
            d = ts.split("T")[0]
            data[d] = data.get(d, 0) + 1
    return data


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
        "dismissed_suggestions": [],
        "uiGeometry": None,
        "settings": {
            "widgetEnabled": True,
            "widgetTaskCount": 5,
            "widgetDockSide": "right",
            "startWithHubMaximized": True,
            "widgetDocked": True,
            "widgetPos": None,
            "widgetCollapsed": False,
            "startInFocusMode": False,
            "closeToTray": True,
            "startWithWindows": False,
            "zenSoundscape": "Silent",
            "zenVolume": 0.5,
            "voiceEnabled": True,
        },
        "widgetCurrentProjectId": None,
    }


def _ensure_nested_defaults(data_dict: Dict[str, Any], default_dict: Dict[str, Any]) -> None:
    """Recursively ensures default keys exist in a nested dictionary."""
    for key, value in default_dict.items():
        data_dict.setdefault(key, value)


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
    _ensure_nested_defaults(state["stats"], base["stats"])

    if not isinstance(state.get("userProfile"), dict):
        state["userProfile"] = {}
    _ensure_nested_defaults(state["userProfile"], base["userProfile"])

    if not isinstance(state.get("activityLog"), list): state["activityLog"] = []
    if not isinstance(state.get("categories"), list): state["categories"] = ["Work", "Personal", "Health", "Learning", "Finance", "Dev", "Creative"]
    if not isinstance(state.get("ideas"), list): state["ideas"] = []
    if not isinstance(state.get("tasks"), list): state["tasks"] = []

    if not isinstance(state.get("settings"), dict):
        state["settings"] = {}
    _ensure_nested_defaults(state["settings"], base["settings"])

    # Validate widgetPos: must be [int, int] or None
    w_pos = state["settings"].get("widgetPos")
    if w_pos is not None and (not isinstance(w_pos, list) or len(w_pos) != 2 or not all(isinstance(x, (int, float)) for x in w_pos)):
        state["settings"]["widgetPos"] = None

    # Validate widgetDockSide: must be 'left' or 'right'
    if state["settings"].get("widgetDockSide") not in ("left", "right"):
        state["settings"]["widgetDockSide"] = "right"

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
        # 10.0 New Fields
        t.setdefault("subtasks", [])
        t.setdefault("tags", [])
        t.setdefault("difficulty", 1) # 1: Easy, 2: Medium, 3: Hard
        t.setdefault("xpReward", 10)
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
    tags: Optional[List[str]] = None,
    schedule: Optional[Dict[str, str]] = None,
    difficulty: int = 1,
    xpReward: int = 10,
    estimatedDuration: int = 0,
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
        "tags": tags or [],
        "subtasks": [],
        "difficulty": difficulty,
        "xpReward": xpReward,
        "estimatedDuration": estimatedDuration,
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

def add_subtask(state: Dict[str, Any], parent_task_id: str, text: str) -> Optional[Dict[str, Any]]:
    """Adds a subtask to a parent task."""
    parent_task = next((t for t in state.get("tasks", []) if t.get("id") == parent_task_id), None)
    if not parent_task:
        return None
    
    subtask = {
        "id": str(uuid.uuid4()),
        "text": text,
        "completed": False,
        "createdAt": now_iso(),
    }
    
    parent_task.setdefault("subtasks", []).append(subtask)
    parent_task["updatedAt"] = now_iso()
    
    log_activity(state, "created", "subtask", subtask["id"], {"parent_task_id": parent_task_id})
    return subtask

def toggle_subtask_completed(state: Dict[str, Any], task_id: str, subtask_id: str) -> bool:
    """Toggles the completed status of a subtask and updates parent if needed."""
    task = next((t for t in state.get("tasks", []) if t.get("id") == task_id), None)
    if not task:
        return False
        
    subtasks = task.get("subtasks", [])
    for st in subtasks:
        if st.get("id") == subtask_id:
            st["completed"] = not st.get("completed", False)
            task["updatedAt"] = now_iso()
            
            # If all subtasks are now complete, complete the parent
            if all(s.get("completed") for s in subtasks):
                if not task.get("completed"):
                    toggle_task_completed(state, task_id)
            # If un-completing a subtask, un-complete the parent
            elif not st["completed"] and task.get("completed"):
                 toggle_task_completed(state, task_id)

            log_activity(state, "toggled", "subtask", subtask_id, {"parent_task_id": task_id, "completed": st["completed"]})
            return True
            
    return False

def delete_subtask(state: Dict[str, Any], task_id: str, subtask_id: str) -> bool:
    """Deletes a subtask from a parent task."""
    task = next((t for t in state.get("tasks", []) if t.get("id") == task_id), None)
    if not task: return False
    
    initial_len = len(task.get("subtasks", []))
    task["subtasks"] = [st for st in task.get("subtasks", []) if st.get("id") != subtask_id]
    if len(task.get("subtasks", [])) < initial_len:
        task["updatedAt"] = now_iso()
        log_activity(state, "deleted", "subtask", subtask_id, {"parent_task_id": task_id})
        return True
    return False

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
        # Handle end of month (e.g. Jan 31 -> Feb 28)
        _, last_day = calendar.monthrange(y, m)
        next_date = date(y, m, min(today_dt.day, last_day))
    
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
            is_completing = not was_completed
            t["completed"] = is_completing
            t["updatedAt"] = now_iso()
            
            if t["completed"]:
                t["completedAt"] = now_iso()
                # Also complete all subtasks
                for st in t.get("subtasks", []):
                    st["completed"] = True
            else:
                t["completedAt"] = None
            
            # Handle recurrence on completion
            if is_completing and t.get("recurrence"):
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
        if sched and isinstance(sched, dict) and sched.get("date") and isinstance(sched["date"], str):
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

def calculate_xp_for_task(task: Dict[str, Any]) -> int:
    """Calculates XP based on difficulty and importance."""
    base = task.get("xpReward", 10)
    difficulty = task.get("difficulty", 1)
    
    # Multiplier for difficulty
    multiplier = 1.0 + (0.5 * (difficulty - 1))
    
    return int(base * multiplier)
