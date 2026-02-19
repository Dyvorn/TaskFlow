from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re
import hashlib

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

def generate_suggestions(state: dict) -> list:
    """The main entry point for generating all proactive AI suggestions."""
    dismissed = state.get("dismissed_suggestions", [])
    all_suggestions = []
    
    all_suggestions.extend(find_recurring_task_patterns(state))
    all_suggestions.extend(analyze_mood_patterns(state))
    all_suggestions.extend(find_stale_tasks(state))
    
    # Filter out dismissed suggestions and sort by confidence
    final_suggestions = [s for s in all_suggestions if s['id'] not in dismissed]
    final_suggestions.sort(key=lambda s: s.get('confidence', 0), reverse=True)
    
    return final_suggestions[:3] # Return top 3