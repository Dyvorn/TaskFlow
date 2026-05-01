import sys
import os
# Add project root to path so 'core' can be found when running standalone
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re
import hashlib
from core.model import tasks_in_section, today_str

def _get_suggestion_id(suggestion_type: str, text: str) -> str:
    """Creates a deterministic, unique ID for a suggestion."""
    return hashlib.md5(f"{suggestion_type}:{text}".encode()).hexdigest()

def _normalize_task_text(text: str) -> str:
    """Simplifies task text for pattern matching."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text) # remove punctuation
    text = re.sub(r'\b(a|the|an|in|on|at|for|my)\b', '', text) # remove common stop words
    return " ".join(text.split())

def find_recurring_task_patterns(state: dict) -> list:
    """
    Analyzes completed tasks to find potential daily or weekly recurring patterns.
    """
    suggestions = []
    completed_tasks = [t for t in state.get("tasks", []) if t.get("completed") and t.get("completedAt")]
    
    # Don't suggest for tasks that are already recurring
    non_recurring_tasks = [t for t in completed_tasks if not t.get("recurrence")]
    
    # Group tasks by normalized text
    grouped_tasks = defaultdict(list)
    for task in non_recurring_tasks:
        normalized = _normalize_task_text(task.get("text", ""))
        if len(normalized.split()) > 1: # Ignore very short/generic tasks (e.g., "email")
            grouped_tasks[normalized].append(task)
            
    # Analyze groups for patterns
    for text, tasks in grouped_tasks.items():
        if len(tasks) < 3: # Need at least 3 occurrences to suggest a pattern
            continue
            
        # Sort by completion date
        tasks.sort(key=lambda t: t["completedAt"])
        
        # Check for daily pattern
        daily_deltas = []
        for i in range(len(tasks) - 1):
            try:
                d1 = datetime.fromisoformat(tasks[i]["completedAt"])
                d2 = datetime.fromisoformat(tasks[i+1]["completedAt"])
                delta = (d2 - d1).total_seconds() / 3600 # Delta in hours
                daily_deltas.append(delta)
            except (ValueError, TypeError):
                continue
        
        # Is it roughly daily? (e.g., between 20 and 28 hours apart)
        if daily_deltas and all(20 < d < 28 for d in daily_deltas):
            original_text = tasks[-1]['text'] # Use the most recent task's text
            suggestion = {
                'id': _get_suggestion_id('SUGGEST_RECURRENCE_DAILY', text),
                'type': 'SUGGEST_RECURRENCE',
                'task_text': original_text,
                'interval': 'daily',
                'confidence': len(tasks) # Simple confidence score
            }
            suggestions.append(suggestion)
            continue # Don't suggest weekly if daily fits

        # Check for weekly pattern
        weekly_deltas = []
        for i in range(len(tasks) - 1):
            try:
                d1 = datetime.fromisoformat(tasks[i]["completedAt"])
                d2 = datetime.fromisoformat(tasks[i+1]["completedAt"])
                delta = (d2 - d1).total_seconds() / 3600 # Delta in hours
                weekly_deltas.append(delta)
            except (ValueError, TypeError):
                continue
        
        # Is it roughly weekly? (e.g., between 160 and 176 hours apart, which is 7 days +/- 8 hours)
        if weekly_deltas and all(160 < d < 176 for d in weekly_deltas):
            original_text = tasks[-1]['text']
            suggestion = { 'id': _get_suggestion_id('SUGGEST_RECURRENCE_WEEKLY', text), 'type': 'SUGGEST_RECURRENCE', 'task_text': original_text, 'interval': 'weekly', 'confidence': len(tasks) }
            suggestions.append(suggestion)


    return suggestions

def analyze_mood_patterns(state: dict) -> list:
    """Analyzes recent mood entries for negative trends."""
    suggestions = []
    moods = state.get("moods", [])
    if len(moods) < 3:
        return [] # Not enough data

    # Look at the last 3 logged days
    recent_moods = sorted(moods, key=lambda m: m.get("date", ""), reverse=True)[:3]
    
    negative_moods = ["Low energy", "Stressed"]
    
    # Check for consecutive negative moods
    if all(m.get("value") in negative_moods for m in recent_moods):
        suggestion_id = _get_suggestion_id('SUGGEST_WELLBEING_CHECK', recent_moods[0]['date'])
        suggestion = {
            'id': suggestion_id,
            'type': 'WELLBEING_CHECK',
            'text': "I've noticed you've been feeling down or stressed lately. Remember to be kind to yourself. Maybe a short break or a lighter schedule could help?",
            'confidence': 100 # This is a high-priority notification
        }
        suggestions.append(suggestion)
        
    return suggestions

def find_stale_tasks(state: dict) -> list:
    """Finds old, uncompleted tasks in the 'Someday' list."""
    suggestions = []
    someday_tasks = [t for t in state.get("tasks", []) if t.get("section") == "Someday" and not t.get("completed")]
    
    if len(someday_tasks) < 5:
        return []

    now = datetime.now()
    stale_tasks = []
    for task in someday_tasks:
        try:
            created_at = datetime.fromisoformat(task.get("createdAt", ""))
            if (now - created_at).days > 30: # Task is older than 30 days
                stale_tasks.append(task)
        except (ValueError, TypeError):
            continue
            
    if len(stale_tasks) >= 3:
        suggestion_id = _get_suggestion_id('SUGGEST_REVIEW_STALE', str(now.date()))
        suggestion = {
            'id': suggestion_id,
            'type': 'REVIEW_STALE_TASKS',
            'text': f"You have {len(stale_tasks)} tasks in 'Someday' that are over a month old. Would you like to review them now to see if they are still relevant?",
            'confidence': len(stale_tasks)
        }
        suggestions.append(suggestion)
        
    return suggestions

def find_task_churn(state: dict) -> list:
    """Finds tasks that are repeatedly moved, suggesting they might be stuck."""
    suggestions = []
    activity_log = state.get("activityLog", [])
    
    # Group move actions by task ID
    moved_tasks = defaultdict(list)
    for entry in activity_log:
        if entry.get("action") == "moved" and entry.get("entityType") == "task":
            moved_tasks[entry.get("entityId")].append(entry)
            
    for task_id, moves in moved_tasks.items():
        if len(moves) > 3: # More than 3 moves might indicate churn
            # Check if it's a back-and-forth pattern, e.g., Today -> Someday -> Today
            if len(moves) > 2:
                sections = [m['details']['to'] for m in moves if m.get('details')]
                if len(sections) > 2 and sections[-1] == sections[-3]:
                    # Find the actual task to get its text
                    task = next((t for t in state.get("tasks", []) if t.get("id") == task_id), None)
                    if task and not task.get("completed"):
                        suggestion_id = _get_suggestion_id('SUGGEST_BREAKDOWN_STUCK_TASK', task_id)
                        suggestion = {
                            'id': suggestion_id,
                            'type': 'SUGGEST_BREAKDOWN_STUCK_TASK',
                            'text': f"I noticed the task <b>'{task['text']}'</b> keeps getting moved. Is it too big? Maybe breaking it down into smaller steps would help.",
                            'task_id': task_id,
                            'confidence': len(moves)
                        }
                        suggestions.append(suggestion)
    
    return suggestions

def find_overload(state: dict) -> list:
    """Detects if 'Today' is overloaded with tasks."""
    suggestions = []
    today_tasks = tasks_in_section(state, "Today")
    incomplete = [t for t in today_tasks if not t.get("completed")]
    
    if len(incomplete) >= 8:
        suggestion = {
            'id': _get_suggestion_id('OVERLOAD_DETECTED', today_str()),
            'type': 'SUGGEST_RESCHEDULE',
            'text': f"You have {len(incomplete)} active tasks for Today. That might be a recipe for burnout. Want to move the 3 least important ones to Tomorrow?",
            'confidence': 90
        }
        suggestions.append(suggestion)
        
    return suggestions

def find_burnout_risk(state: dict) -> list:
    """Detects high-intensity work patterns and suggests forced breaks."""
    suggestions = []
    log = state.get("activityLog", [])
    today = today_str()
    
    # Filter today's work
    today_log = [e for e in log if e.get("timestamp", "").startswith(today)]
    
    focus_count = sum(1 for e in today_log if e.get("entityType") == "focusSession" and e.get("action") == "completed")
    break_count = sum(1 for e in today_log if e.get("entityType") == "breakSession" and e.get("action") == "completed")
    
    # 1. High focus-to-break ratio check
    if focus_count >= 3 and break_count == 0:
        suggestion = {
            'id': _get_suggestion_id('BURNOUT_RISK_RATIO', today),
            'type': 'FORCED_BREAK',
            'text': "You've crushed 3 focus sessions without a break. Your brain needs a reboot to stay sharp. Start a 15-minute break?",
            'confidence': 95
        }
        suggestions.append(suggestion)
        return suggestions

    # 2. Cognitive Load (Difficulty sum) check
    tasks = state.get("tasks", [])
    completed_today = [t for t in tasks if t.get("completed") and t.get("completedAt", "").startswith(today)]
    total_diff = sum(t.get("difficulty", 1) for t in completed_today)
    
    if total_diff >= 12: # Threshold for high-intensity day (e.g. 3 Hard tasks)
        # Check if last activity was a break recently
        last_break = next((e for e in reversed(today_log) if e.get("entityType") == "breakSession"), None)
        needs_break = True
        if last_break:
            try:
                lb_time = datetime.fromisoformat(last_break["timestamp"])
                if (datetime.now() - lb_time).total_seconds() < 3600: # Within last hour
                    needs_break = False
            except: pass
            
        if needs_break:
            suggestions.append({
                'id': _get_suggestion_id('BURNOUT_RISK_LOAD', today),
                'type': 'FORCED_BREAK',
                'text': "You've tackled some heavy tasks today. To prevent mental fatigue, I suggest taking a short break now.",
                'confidence': 85
            })

    return suggestions

def find_cognitive_overload(state: dict) -> list:
    """Detects if too many high-complexity tasks are planned for a single day."""
    suggestions = []
    today_tasks = tasks_in_section(state, "Today")
    incomplete_hard = [t for t in today_tasks if not t.get("completed") and t.get("difficulty", 1) >= 4]
    
    if len(incomplete_hard) >= 3:
        suggestion = {
            'id': _get_suggestion_id('COGNITIVE_OVERLOAD', today_str()),
            'type': 'SUGGEST_RESCHEDULE',
            'text': (
                f"I noticed you have {len(incomplete_hard)} 'Hard' or 'Epic' tasks today. "
                "This requires intense focus. Consider moving one to Tomorrow to maintain quality."
            ),
            'confidence': 88
        }
        suggestions.append(suggestion)
        
    return suggestions

def find_ghosted_tasks(state: dict) -> list:
    """Identifies tasks that have been pushed to 'Today' many times but never completed."""
    suggestions = []
    log = state.get("activityLog", [])
    
    # Count how many times each task was moved TO 'Today'
    move_counts = Counter(e.get("entityId") for e in log if e.get("action") == "moved" and e.get("details", {}).get("to") == "Today")
    
    for task_id, count in move_counts.items():
        if count >= 5:
            task = next((t for t in state.get("tasks", []) if t.get("id") == task_id), None)
            if task and not task.get("completed") and task.get("section") == "Today":
                suggestions.append({
                    'id': _get_suggestion_id('TASK_GHOSTING', task_id),
                    'type': 'SUGGEST_RESCHEDULE',
                    'text': f"The task <b>'{task['text']}'</b> has been moved to Today {count} times without completion. Should we move it back to 'Someday' for now?",
                    'task_id': task_id,
                    'confidence': count * 10
                })
    return suggestions

def find_golden_hour(state: dict) -> list:
    """Identifies the 60-minute window where the user is most productive."""
    log = state.get("activityLog", [])
    completions = [e for e in log if e.get("action") == "completed" and e.get("entityType") == "task"]
    
    if len(completions) < 10:
        return []

    hours = Counter()
    for c in completions:
        try:
            dt = datetime.fromisoformat(c["timestamp"])
            hours[dt.hour] += 1
        except: continue
        
    golden_hour, count = hours.most_common(1)[0]
    
    # Suggestion based on current time
    if datetime.now().hour == golden_hour:
        suggestions = [{
            'id': _get_suggestion_id('GOLDEN_HOUR_ACTIVE', today_str()),
            'type': 'WELLBEING_CHECK',
            'text': f"It's {golden_hour}:00! This is historically your most productive hour. Want to start a focus session?",
            'confidence': 100
        }]
        return suggestions
    return []

def find_productivity_leaks(state: dict) -> list:
    """Identifies categories that negatively impact user mood."""
    suggestions = []
    log = state.get("activityLog", [])
    moods = state.get("moods", [])
    
    # This is a complex cross-reference of task completion followed by mood drops
    # For now, we suggest a review if a certain category is always active on 'Stressed' days
    stressed_days = [m['date'] for m in moods if m.get('value') == "Stressed"]
    if not stressed_days: return []
    
    tasks = state.get("tasks", [])
    
    # Safety: Ensure completedAt is a string before slicing
    cats_on_bad_days = Counter(
        t.get('category') for t in tasks 
        if isinstance(t.get('completedAt'), str) and t.get('completedAt')[:10] in stressed_days
    )
    
    if cats_on_bad_days:
        top_leak, count = cats_on_bad_days.most_common(1)[0]
        if count >= 3:
            suggestions.append({
                'id': _get_suggestion_id('PRODUCTIVITY_LEAK', top_leak),
                'type': 'WELLBEING_CHECK',
                'text': f"I've noticed tasks in <b>'{top_leak}'</b> often coincide with high stress. Let's try scheduling these for your 'Golden Hour' instead.",
                'confidence': 70
            })
    return suggestions

def find_energy_vampires(state: dict) -> list:
    """
    Identifies categories that frequently result in 'Low energy' mood logs 
    after completion. (Implementation of TODO)
    """
    suggestions = []
    moods = state.get("moods", [])
    # Find days where the user felt low energy
    low_energy_days = [m['date'] for m in moods if m.get('value') == "Low energy"]
    if not low_energy_days:
        return []

    tasks = state.get("tasks", [])
    # Count categories completed on those specific low-energy days
    bad_cats = Counter(
        t.get('category') for t in tasks 
        if t.get('completed') and isinstance(t.get('completedAt'), str) 
        and t.get('completedAt')[:10] in low_energy_days
    )
    
    if bad_cats:
        top_vampire, count = bad_cats.most_common(1)[0]
        if count >= 3: # Threshold for a pattern
            suggestions.append({
                'id': _get_suggestion_id('ENERGY_VAMPIRE', top_vampire),
                'type': 'WELLBEING_CHECK',
                'text': f"I've noticed that <b>'{top_vampire}'</b> tasks often coincide with low energy levels. Consider scheduling a restorative break after these.",
                'confidence': 85
            })
    return suggestions

def find_duration_mismatch(state: dict) -> list:
    """Compares estimatedDuration vs actualDuration across categories."""
    suggestions = []
    tasks = [t for t in state.get("tasks", []) if t.get("completed") and t.get("actualDuration") and t.get("estimatedDuration")]
    if len(tasks) < 5: return []
    
    cat_stats = defaultdict(list)
    for t in tasks:
        ratio = t["actualDuration"] / max(1, t["estimatedDuration"])
        cat_stats[t.get("category", "General")].append(ratio)
        
    for cat, ratios in cat_stats.items():
        avg_ratio = sum(ratios) / len(ratios)
        if avg_ratio > 1.4: # 40% over-budget consistently
            suggestions.append({
                'id': _get_suggestion_id('DURATION_MISMATCH', cat),
                'type': 'SUGGEST_BREAKDOWN_STUCK_TASK',
                'text': f"Tasks in <b>'{cat}'</b> typically take {int(avg_ratio*100)}% longer than you expect. Try allocating more time or breaking them down further.",
                'confidence': int(avg_ratio * 10)
            })
    return suggestions

def find_context_switches(state: dict) -> list:
    """Detects high frequencies of switching between task categories."""
    suggestions = []
    log = state.get("activityLog", [])
    today = today_str()
    # Look at completions today
    completions = [e for e in log if e.get("action") == "completed" and e.get("entityType") == "task" and e.get("timestamp", "").startswith(today)]
    
    if len(completions) < 4: return []
    
    switches = 0
    prev_cat = None
    tasks = {t['id']: t for t in state.get("tasks", [])}
    
    for c in completions:
        task = tasks.get(c.get("entityId"))
        if not task: continue
        cat = task.get("category")
        if prev_cat and cat != prev_cat:
            switches += 1
        prev_cat = cat
        
    if switches > 4: # Threshold for high context switching
        suggestions.append({
            'id': _get_suggestion_id('CONTEXT_SWITCH_OVERLOAD', today),
            'type': 'SUGGEST_BREAKDOWN_STUCK_TASK',
            'text': f"You've switched focus between categories {switches} times today. Batching similar tasks together can save you significant cognitive energy.",
            'confidence': switches * 10
        })
    return suggestions

def find_seasonal_trends(state: dict) -> list:
    """Detects productivity shifts between months."""
    log = state.get("activityLog", [])
    completions = [e for e in log if e.get("action") == "completed"]
    if len(completions) < 50: return []
    
    month_counts = Counter(e["timestamp"][5:7] for e in completions if "timestamp" in e)
    curr_month = datetime.now().strftime("%m")
    avg_comp = sum(month_counts.values()) / len(month_counts)
    
    if month_counts[curr_month] < avg_comp * 0.7:
        return [{
            'id': _get_suggestion_id('SEASONAL_DROP', curr_month),
            'type': 'WELLBEING_CHECK',
            'text': "Your productivity is lower than your usual average this month. Seasonal shifts can affect energy—be kind to yourself.",
            'confidence': 60
        }]
    return []

def generate_suggestions(state: dict) -> list:
    """The main entry point for generating all proactive AI suggestions."""
    dismissed = state.get("dismissed_suggestions", [])
    all_suggestions = []
    
    all_suggestions.extend(find_recurring_task_patterns(state))
    all_suggestions.extend(analyze_mood_patterns(state))
    all_suggestions.extend(find_stale_tasks(state))
    all_suggestions.extend(find_task_churn(state))
    all_suggestions.extend(find_overload(state))
    all_suggestions.extend(find_burnout_risk(state))
    all_suggestions.extend(find_cognitive_overload(state))
    all_suggestions.extend(find_ghosted_tasks(state))
    all_suggestions.extend(find_golden_hour(state))
    all_suggestions.extend(find_productivity_leaks(state))
    all_suggestions.extend(find_energy_vampires(state))
    all_suggestions.extend(find_duration_mismatch(state))
    all_suggestions.extend(find_context_switches(state))
    all_suggestions.extend(find_seasonal_trends(state))
    
    # Filter out dismissed suggestions and sort by confidence
    final_suggestions = [s for s in all_suggestions if s['id'] not in dismissed]


    final_suggestions.sort(key=lambda s: s.get('confidence', 0), reverse=True)
    
    return final_suggestions[:3] # Return top 3

def predict_project_completion(state: dict, project_id: str) -> dict:
    """
    Estimates completion date for a project based on recent velocity.
    (Implementation of TODO)
    """
    project_tasks = [t for t in state.get("tasks", []) if t.get("projectId") == project_id]
    if not project_tasks:
        return {"ready": False, "reason": "No tasks in project"}

    incomplete = [t for t in project_tasks if not t.get("completed")]
    if not incomplete:
        return {"ready": True, "date": "Finished"}

    velocity = predict_future_velocity(state)
    if velocity <= 0.1: # Threshold to avoid division by near-zero
        return {"ready": False, "reason": "Not enough recent data to predict"}

    days_needed = len(incomplete) / velocity
    est_date = datetime.now() + timedelta(days=days_needed)
    return {
        "ready": True,
        "date": est_date.strftime("%Y-%m-%d"),
        "days": int(days_needed)
    }

def predict_future_velocity(state: dict) -> float:
    """
    Predicts expected task completion count for tomorrow based on 
    weighted history of the last 7 days.
    """
    log = state.get("activityLog", [])
    today = datetime.now().date()
    history = Counter()
    
    for entry in log:
        if entry.get("action") == "completed":
            ts = entry.get("timestamp", "").split("T")[0]
            history[ts] += 1
            
    # Calculate weighted average (recent days count more)
    total_weight = 0
    weighted_sum = 0
    for i in range(1, 8):
        d_str = (today - timedelta(days=i)).isoformat()
        weight = (8 - i)
        weighted_sum += history.get(d_str, 0) * weight
        total_weight += weight
        
    return weighted_sum / total_weight if total_weight > 0 else 0.0

# ═══════════════════════════════════════════════════════════════════════════
# TODO / IDEAS LIST
# ═══════════════════════════════════════════════════════════════════════════
# [x] Time-accuracy score: Comparing estimatedDuration vs actualDuration across categories.
# [ ] Seasonal productivity trends (e.g., Summer vs Winter performance).
# [x] Context-Switch Cost: Estimate time lost when moving between different project categories.
# [x] "Energy Vampires": Identify categories that frequently result in "Low energy" mood logs after completion.
# [x] Prediction of "Estimated Completion Time" for entire projects based on current velocity.
