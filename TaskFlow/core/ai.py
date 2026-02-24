import random
import threading
import time
from typing import List, Dict, Any, Optional

try:
    import ai.analytics as analytics
except ImportError:
    analytics = None

class AIEngine:
    """
    The central AI logic for TaskFlow.
    Handles categorization, ranking, and user coaching.
    """
    def __init__(self):
        self._tips = [
            "Use #hashtags in task input to auto-categorize them (e.g., 'Call mom #Personal').",
            "Double-click any task to quickly rename it.",
            "Right-click a task for more options like scheduling or moving it.",
            "Use the Brain Dump feature on the Home page to quickly unload your mind.",
            "Check the AI Coach page to teach the AI and see its recommendations.",
            "You can drag and drop tasks to reorder them.",
            "Press Ctrl+B to toggle Focus Mode and hide the sidebar.",
            "Complete recurring tasks to build a streak.",
            "The 'Zen Mode' helps you focus on just one task at a time.",
            "Review your 'Someday' list occasionally to keep it fresh."
        ]
        # Placeholder for model state
        self.vocab_size = 0
        self.training_samples = 0

    def get_tip_of_the_day(self) -> str:
        """Returns a random tip to display on startup."""
        return random.choice(self._tips)

    def predict_category(self, text: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Predicts a category for the given task text.
        """
        # Simple keyword-based heuristic for now
        text_lower = text.lower()
        if any(w in text_lower for w in ["email", "call", "meeting", "report", "presentation"]):
            return "Work"
        if any(w in text_lower for w in ["buy", "grocery", "milk", "clean", "laundry"]):
            return "Personal"
        if any(w in text_lower for w in ["gym", "run", "workout", "doctor"]):
            return "Health"
        return None

    def rank_tasks(self, tasks: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Ranks tasks based on importance and context.
        """
        if not tasks:
            return []
        
        # Sort by: Important -> Has Due Date -> Creation Order
        return sorted(tasks, key=lambda t: (
            not t.get("important", False),
            t.get("schedule", {}).get("date", "9999-99-99") if t.get("schedule") else "9999-99-99",
            t.get("createdAt", "")
        ))

    # --- Coach / Training Methods ---

    def get_stats(self) -> Dict[str, Any]:
        return {
            "status": "Online",
            "vocab_size": self.vocab_size,
            "task_log_count": self.training_samples
        }

    def get_review_queue(self) -> List[Dict[str, Any]]:
        # Future: Return tasks that need review (e.g. low priority, old)
        return []

    def get_proactive_suggestions(self, state: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if analytics and state:
            return analytics.generate_suggestions(state)
        return []

    def train_model(self, background: bool = True, on_finish_callback=None) -> None:
        """Simulates a training process."""
        def _train():
            time.sleep(2) # Simulate work
            self.training_samples += 10
            if on_finish_callback:
                on_finish_callback()
        
        if background:
            threading.Thread(target=_train, daemon=True).start()
        else:
            _train()

    def learn_task(self, text: str, category: str, context: Optional[Dict[str, Any]] = None) -> None:
        self.training_samples += 1

    def dismiss_suggestion(self, suggestion_id: str) -> None:
        pass

    def get_all_categories(self) -> List[str]:
        return ["Work", "Personal", "Health", "Learning", "Finance", "Dev", "Creative"]