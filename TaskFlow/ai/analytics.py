from datetime import datetime, timedelta
from collections import defaultdict
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

def generate_suggestions(state: dict) -> list:
    """The main entry point for generating all proactive AI suggestions."""
    dismissed = state.get("dismissed_suggestions", [])
    all_suggestions = []
    
    all_suggestions.extend(find_recurring_task_patterns(state))
    
    # Filter out dismissed suggestions and sort by confidence
    final_suggestions = [s for s in all_suggestions if s['id'] not in dismissed]
    final_suggestions.sort(key=lambda s: s.get('confidence', 0), reverse=True)
    
    return final_suggestions[:3] # Return top 3