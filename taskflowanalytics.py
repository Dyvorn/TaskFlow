# ============================================================================
# TASKFLOW ANALYTICS ENGINE
# ============================================================================

from typing import Any, Dict, List
from collections import Counter
from datetime import datetime, timedelta
import math
import random

def get_completion_rate(state: Dict[str, Any]) -> float:
    """Calculates the overall task completion percentage."""
    tasks = state.get("tasks") or []
    if not tasks:
        return 0.0
    completed = sum(1 for t in tasks if isinstance(t, dict) and t.get("completed"))
    return (completed / len(tasks)) * 100

def get_category_breakdown(state: Dict[str, Any]) -> Dict[str, int]:
    """Returns a count of completed tasks per category."""
    tasks = state.get("tasks") or []
    # Filter for completed tasks only to show "achievement" breakdown
    completed_tasks = [t for t in tasks if isinstance(t, dict) and t.get("completed")]
    
    # Extract categories, defaulting to "Uncategorized" if None
    categories = [t.get("category") or "Uncategorized" for t in completed_tasks]
    
    if not categories:
        return {}
        
    return dict(Counter(categories))

def get_activity_heatmap_data(state: Dict[str, Any]) -> Dict[str, int]:
    """
    Returns a dictionary mapping date strings (YYYY-MM-DD) to activity counts.
    Used for contribution graphs.
    """
    log = state.get("activityLog") or []
    activity_counts = Counter()
    
    for entry in log:
        if not isinstance(entry, dict): continue
        # We count completions and creations as 'activity'
        if entry.get("action") in ("completed", "created"):
            ts = entry.get("timestamp") or ""
            if ts:
                try:
                    date_str = ts.split("T")[0]
                    activity_counts[date_str] += 1
                except IndexError:
                    pass
                    
    return dict(activity_counts)

def get_most_productive_hour(state: Dict[str, Any]) -> int:
    """Returns the hour of the day (0-23) with the most task completions."""
    log = state.get("activityLog") or []
    hours = []
    
    for entry in log:
        if not isinstance(entry, dict): continue
        if entry.get("action") == "completed":
            ts = entry.get("timestamp") or ""
            try:
                dt = datetime.fromisoformat(ts)
                hours.append(dt.hour)
            except (ValueError, TypeError):
                pass
                
    if not hours:
        return 9 # Default to 9 AM if no data
        
    return Counter(hours).most_common(1)[0][0]

def get_recent_activity_summary(state: Dict[str, Any], limit: int = 5) -> List[str]:
    """Returns a list of readable strings describing recent actions."""
    log = state.get("activityLog") or []
    valid_log = [x for x in log if isinstance(x, dict)]
    # Sort by timestamp descending just in case, though log should be appended
    sorted_log = sorted(valid_log, key=lambda x: x.get("timestamp") or "", reverse=True)
    
    summary = []
    for entry in sorted_log[:limit]:
        action = entry.get("action")
        etype = entry.get("entityType")
        details = entry.get("details") or {}
        
        if action == "completed" and etype == "task":
            summary.append("Completed a task")
        elif action == "created" and etype == "task":
            cat = details.get("category")
            if cat:
                summary.append(f"Added a {cat} task")
            else:
                summary.append("Added a task")
        elif action == "created" and etype == "project":
            summary.append(f"Started project '{details.get('name', '')}'")
            
    return summary

def get_productivity_score(state: Dict[str, Any]) -> int:
    """Calculates a daily productivity score (0-100) based on tasks, habits, and streak."""
    score = 0
    
    # 1. Task Completion (Max 60 pts)
    # We look at tasks completed today
    today_str = datetime.now().date().isoformat()
    tasks = state.get("tasks") or []
    
    # Filter tasks completed today
    # Note: This relies on updatedAt being set when completed. 
    completed_today = []
    for t in tasks:
        if not isinstance(t, dict): continue
        if not t.get("completed"):
            continue
        
        # Use completedAt if available, otherwise fallback to updatedAt (legacy support)
        comp_date = t.get("completedAt") or t.get("updatedAt")
        if comp_date and comp_date.startswith(today_str):
            completed_today.append(t)
    
    # Diminishing returns: first 3 tasks worth 10, next 3 worth 5, rest worth 2
    count = len(completed_today)
    if count <= 3:
        score += count * 10
    elif count <= 6:
        score += 30 + (count - 3) * 5
    else:
        score += 45 + (count - 6) * 2
        
    score = min(60, score)
    
    # 2. Habits (Max 30 pts)
    habit_checks = state.get("habitChecks")
    if not isinstance(habit_checks, dict):
        habit_checks = {}
    checks = habit_checks.get(today_str)
    if not isinstance(checks, dict):
        checks = {}
    habits_done = sum(1 for v in checks.values() if v)
    score += min(30, habits_done * 10)
    
    # 3. Streak Bonus (Max 10 pts)
    stats = state.get("stats")
    if not isinstance(stats, dict):
        stats = {}
    try:
        streak = int(stats.get("currentStreak") or 0)
    except (ValueError, TypeError):
        streak = 0
    score += min(10, streak)
    
    return min(100, score)

def get_hourly_activity(state: Dict[str, Any]) -> Dict[int, int]:
    """Returns a count of completed tasks for each hour of the day (0-23)."""
    log = state.get("activityLog") or []
    hours = Counter()
    
    for entry in log:
        if not isinstance(entry, dict): continue
        if entry.get("action") == "completed":
            ts = entry.get("timestamp") or ""
            try:
                # Handle ISO format with potential Z or offset
                ts = ts.replace("Z", "+00:00")
                dt = datetime.fromisoformat(ts)
                hours[dt.hour] += 1
            except (ValueError, TypeError):
                pass
    return dict(hours)

def get_weekday_averages(state: Dict[str, Any]) -> Dict[int, float]:
    """
    Calculates average tasks completed for each day of the week (0=Monday)
    based on the user's entire history.
    """
    log = state.get("activityLog") or []
    completions_by_date = Counter()
    for entry in log:
        if isinstance(entry, dict) and entry.get("action") == "completed":
            ts = entry.get("timestamp") or ""
            if ts:
                completions_by_date[ts.split("T")[0]] += 1
    
    weekday_totals = Counter()
    weekday_counts = Counter()
    
    for date_str, count in completions_by_date.items():
        try:
            dt = datetime.fromisoformat(date_str)
            wd = dt.weekday()
            weekday_totals[wd] += count
            weekday_counts[wd] += 1
        except ValueError:
            pass
            
    return {wd: (weekday_totals[wd] / weekday_counts[wd]) for wd in weekday_totals}

def get_mood_averages(state: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculates average tasks completed for each mood type based on user history.
    """
    log = state.get("activityLog") or []
    completions_by_date = Counter()
    for entry in log:
        if isinstance(entry, dict) and entry.get("action") == "completed":
            ts = entry.get("timestamp") or ""
            if ts:
                completions_by_date[ts.split("T")[0]] += 1
                
    moods = state.get("moods") or []
    mood_totals = Counter()
    mood_counts = Counter()
    
    for m in moods:
        if isinstance(m, dict) and m.get("date") and m.get("value"):
            d = m["date"]
            v = m["value"]
            count = completions_by_date.get(d, 0)
            mood_totals[v] += count
            mood_counts[v] += 1
            
    return {m: (mood_totals[m] / mood_counts[m]) for m in mood_totals}
