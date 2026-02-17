import json
from pathlib import Path
from typing import Optional, Dict, Any, List

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
        self._ensure_log_file()

    def _ensure_log_file(self):
        """Creates an empty usage_log.json if it doesn't exist."""
        if not self.log_path.exists():
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def log_task_for_training(self, text: str, category: str):
        """Appends a new task to the user's usage log for future training."""
        log_data = []
        with open(self.log_path, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
        
        log_data.append({"text": text, "category": category})
        
        with open(self.log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=4)

    def predict_category(self, text: str) -> Optional[str]:
        """Creates a fresh inference engine to get a prediction."""
        engine = InferenceEngine(self.user_id, self.user_manager)
        return engine.predict(text)

    def train_model(self):
        """Creates a trainer and runs the training process."""
        trainer = UserTrainer(self.user_id, self.user_manager)
        trainer.train_model(epochs=20)
        print("AI Engine: Training complete.")

    def get_stats(self) -> Dict[str, Any]:
        """Gathers stats for the AI Coach UI."""
        pipeline = TaskPipeline(self.user_path)
        pipeline.load()

        num_tasks = 0
        if self.log_path.exists():
            with open(self.log_path, 'r', encoding='utf-8') as f:
                num_tasks = len(json.load(f))

        return {
            "status": "Active" if (self.user_path / "brain.pth").exists() else "Not Trained",
            "vocab_size": len(pipeline.vocab),
            "categories": pipeline.categories,
            "task_log_count": num_tasks,
        }
