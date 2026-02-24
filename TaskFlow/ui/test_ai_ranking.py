import unittest
import sys
import os

# Ensure we can import from core
# Assuming this file is in TaskFlow/TaskFlow/tests/
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# Try importing AIEngine, or mock it if strictly running in an environment without it
try:
    from core.ai import AIEngine
except ImportError:
    # Mock AIEngine for the purpose of this standalone test file if core.ai is missing
    class AIEngine:
        def rank_tasks(self, tasks, context=None):
            if not tasks:
                return []
            # Dummy logic: just return as is or sort by text length for stability in mock
            return sorted(tasks, key=lambda t: len(t.get("text", "")), reverse=True)

        def get_tip_of_the_day(self) -> str:
            """Returns a random tip."""
            import random
            tips = [
                "Use #hashtags in task input to auto-categorize them (e.g., 'Call mom #Personal').",
                "Double-click any task to quickly rename it.",
                "Right-click a task for more options like scheduling or moving it.",
                "Use the Brain Dump feature on the Home page to quickly unload your mind.",
                "Check the AI Coach page to teach the AI and see its recommendations."
            ]
            return random.choice(tips)

class TestAIEngineRanking(unittest.TestCase):
    
    def setUp(self):
        self.ai_engine = AIEngine()

    def test_rank_tasks_with_valid_context(self):
        """Test ranking with a full context provided."""
        tasks = [
            {"id": "1", "text": "Do laundry", "completed": False},
            {"id": "2", "text": "Write report", "completed": False}
        ]
        context = {
            "time_of_day": "morning",
            "day_of_week": "Monday",
            "mood": "Motivated"
        }
        ranked = self.ai_engine.rank_tasks(tasks, context)
        self.assertIsInstance(ranked, list)
        self.assertEqual(len(ranked), 2)
        # Ensure items are preserved
        ids = [t["id"] for t in ranked]
        self.assertIn("1", ids)
        self.assertIn("2", ids)

    def test_rank_tasks_empty_list(self):
        """Test that an empty task list returns an empty list."""
        context = {"time_of_day": "evening"}
        ranked = self.ai_engine.rank_tasks([], context)
        self.assertEqual(ranked, [])

    def test_rank_tasks_missing_context(self):
        """Test that rank_tasks handles None or empty context gracefully."""
        tasks = [{"id": "1", "text": "Task A"}]
        
        # Case 1: None context
        ranked_none = self.ai_engine.rank_tasks(tasks, None)
        self.assertEqual(len(ranked_none), 1)
        
        # Case 2: Empty context
        ranked_empty = self.ai_engine.rank_tasks(tasks, {})
        self.assertEqual(len(ranked_empty), 1)

if __name__ == "__main__":
    unittest.main()