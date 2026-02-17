import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from .trainer import UserTrainer
from .inference import InferenceEngine
from .pipeline import TaskPipeline
from core.user_manager import UserManager

class AIEngine:
    """
    A high-level bridge connecting the UI to the AI subsystems.
    This class provides a clean API for predictions, training, and data logging.
    """
    def __init__(self, user_id: str = "user_123"):
        self.user_id = user_id
        self.user_manager = UserManager()
        self.user_path = self.user_manager.ensure_user_directory(self.user_id)
        self.log_path = self.user_path / "usage_log.json"
        self.review_path = self.user_path / "review_queue.json"
        self._ensure_files()
        self._inference_engine = None # Cache the loaded model

    def _ensure_files(self):
        """Creates empty data files if they don't exist."""
        if not self.log_path.exists():
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump([], f)
        if not self.review_path.exists():
            with open(self.review_path, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def log_task_for_training(self, text: str, category: str):
        """Appends a new task to the user's usage log for future training."""
        log_data = []
        with open(self.log_path, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
        
        log_data.append({"text": text, "category": category})
        
        with open(self.log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=4)

    def learn_task(self, text: str, category: str):
        """
        The main entry point for learning. 
        Call this whenever a user saves or corrects a task in the UI.
        """
        # 1. Add to training log
        self.log_task_for_training(text, category)
        
        # 2. Remove from review queue if it was there (auto-resolve)
        self._remove_from_review_queue(text)

    def _log_for_review(self, text: str, category: str, confidence: float):
        """Adds a task to the review queue if the AI was unsure."""
        queue = []
        if self.review_path.exists():
            with open(self.review_path, 'r', encoding='utf-8') as f:
                queue = json.load(f)
        
        # Avoid duplicates
        if not any(item['text'] == text for item in queue):
            queue.append({
                "text": text,
                "predicted_category": category,
                "confidence": confidence
            })
            with open(self.review_path, 'w', encoding='utf-8') as f:
                json.dump(queue, f, indent=4)

    def _remove_from_review_queue(self, text: str):
        """Removes a task from the review queue."""
        if not self.review_path.exists(): return
        
        with open(self.review_path, 'r', encoding='utf-8') as f:
            queue = json.load(f)
        
        new_queue = [q for q in queue if q['text'] != text]
        
        if len(new_queue) != len(queue):
            with open(self.review_path, 'w', encoding='utf-8') as f:
                json.dump(new_queue, f, indent=4)

    def predict_category(self, text: str) -> Optional[str]:
        """Creates a fresh inference engine to get a prediction."""
        engine = InferenceEngine(self.user_id, self.user_manager)
        category, confidence = engine.predict(text)
        if self._inference_engine is None:
            self._inference_engine = InferenceEngine(self.user_id, self.user_manager)
            
        category, confidence = self._inference_engine.predict(text)
        
        # If the AI is unsure (confidence < 60%), add to review queue for the Coach
        if category and confidence < 0.6:
            self._log_for_review(text, category, confidence)
            
        return category

    def train_model(self):
        """Creates a trainer and runs the training process."""
        trainer = UserTrainer(self.user_id, self.user_manager)
        trainer.train_model(epochs=20)
        self._inference_engine = None # Invalidate cache so we reload the new brain next time
        print("AI Engine: Training complete.")

    def get_stats(self) -> Dict[str, Any]:
        """Gathers stats for the AI Coach UI."""
        pipeline = TaskPipeline(self.user_path)
        pipeline.load()

        num_tasks = 0
        if self.log_path.exists():
            with open(self.log_path, 'r', encoding='utf-8') as f:
                num_tasks = len(json.load(f))
        
        num_reviews = 0
        if self.review_path.exists():
            with open(self.review_path, 'r', encoding='utf-8') as f:
                num_reviews = len(json.load(f))

        return {
            "status": "Active" if (self.user_path / "brain.pth").exists() else "Not Trained",
            "vocab_size": len(pipeline.vocab),
            "categories": pipeline.categories,
            "task_log_count": num_tasks,
            "pending_reviews": num_reviews
        }

    def get_review_queue(self) -> List[Dict]:
        """Returns the list of uncertain tasks for the AI Coach UI."""
        if not self.review_path.exists(): return []
        with open(self.review_path, 'r', encoding='utf-8') as f:
            return json.load(f)
