import json
import torch
import shutil
from pathlib import Path
from typing import Dict, Optional, List

from core.user_manager import UserManager
from .architect import TaskBrain
from .pipeline import TaskPipeline
from .trainer import UserTrainer, TrainingWorker
import ai.analytics as analytics

class AIEngine:
    """
    Orchestrates all AI operations, including prediction, learning, and training.
    """
    def __init__(self, user_id: str, state: Dict):
        self.user_id = user_id
        self.state = state
        self.user_manager = UserManager()
        self.user_path = self.user_manager.ensure_user_directory(user_id)
        
        self._bootstrap_base_model()
        
        self.pipeline = TaskPipeline(self.user_path)
        self.model: Optional[TaskBrain] = None
        self.review_queue: List[Dict] = []

        self._new_samples_counter = 0
        self._training_threshold = 10  # Auto-train after 10 new learned tasks
        self._training_worker: Optional[TrainingWorker] = None

        self.load_pipeline_and_model()

    def _bootstrap_base_model(self):
        """Copies pre-trained assets to user directory if fresh."""
        # Locate assets folder (assuming it's in the project root, two levels up)
        base_path = Path(__file__).parent.parent / "assets"
        base_brain = base_path / "base_brain.pth"
        base_vocab = base_path / "base_vocab.json"
        
        user_brain = self.user_path / "brain.pth"
        user_vocab = self.user_path / "vocab.json"
        
        if base_brain.exists() and not user_brain.exists():
            try:
                shutil.copy2(base_brain, user_brain)
                print(f"Bootstrapped user brain from {base_brain}")
            except Exception as e:
                print(f"Failed to bootstrap brain: {e}")
                
        if base_vocab.exists() and not user_vocab.exists():
            try:
                shutil.copy2(base_vocab, user_vocab)
                print(f"Bootstrapped user vocab from {base_vocab}")
            except Exception as e:
                print(f"Failed to bootstrap vocab: {e}")

    def load_pipeline_and_model(self):
        """Loads the pipeline and model from disk."""
        self.pipeline.load()
        
        if not self.pipeline.categories:
            # If no categories exist, use the default ones from the main state
            self.pipeline.categories = self.state.get("categories", [])
            self.pipeline.cat_to_idx = {cat: i for i, cat in enumerate(self.pipeline.categories)}

        if not self.pipeline.vocab:
            # First run, build a basic pipeline from existing tasks
            self.pipeline.build_or_update_from_log(self.state.get("tasks", []))

        # The dimensions for each context feature (e.g., 4 times of day, 7 days of week)
        context_dims = [len(values) for values in self.pipeline.context_features.values()]

        self.model = TaskBrain(
            vocab_size=len(self.pipeline.vocab),
            hidden_size=64,
            num_classes=len(self.pipeline.categories),
            context_dims=context_dims
        )
        
        model_path = self.user_path / "brain.pth"
        if model_path.exists():
            try:
                # Check for corruption (empty file)
                if model_path.stat().st_size == 0:
                    raise ValueError("Model file is empty")
                self.model.load_state_dict(torch.load(model_path))
                print("AI brain loaded successfully.")
            except Exception as e:
                print(f"Could not load AI brain (corrupt or incompatible). Re-initializing. Error: {e}")
                # Rename corrupt file for safety/debugging
                try:
                    model_path.rename(model_path.with_suffix(".corrupt"))
                except OSError:
                    pass
                
                # Attempt to restore base model immediately
                self._bootstrap_base_model()
                # Try loading again if bootstrap succeeded
                if model_path.exists():
                    try:
                        self.model.load_state_dict(torch.load(model_path))
                    except Exception as e2:
                        print(f"Failed to load bootstrapped model: {e2}")
                        print("Starting with random weights. Please run 'train_brain_model.py' to update the base model.")
        self.model.eval()

    def predict_category(self, text: str, context: Dict) -> Optional[str]:
        """Predicts the category for a given task text and context."""
        if not self.model or not text:
            return None

        # --- Dynamic Confidence Threshold ---
        # Start with a high threshold and lower it as the model becomes more mature.
        base_threshold = 0.85
        min_threshold = 0.60
        vocab_size = len(self.pipeline.vocab)
        log_count = self.get_stats()["task_log_count"]
        
        # Lower threshold by 0.05 for every 100 vocab words and 50 log entries
        vocab_bonus = (vocab_size // 100) * 0.05
        log_bonus = (log_count // 50) * 0.05
        
        dynamic_threshold = max(min_threshold, base_threshold - vocab_bonus - log_bonus)

        text_indices, offsets, context_indices = self.pipeline.process_input(text, context)
        with torch.no_grad():
            output = self.model(text_indices, offsets, context_indices)
            probabilities = torch.softmax(output, dim=1)
            confidence, predicted_idx = torch.max(probabilities, 1)

        if confidence.item() < dynamic_threshold:
            # Low confidence, add to review queue
            prediction = {
                "text": text,
                "predicted_category": self.pipeline.get_category_name(predicted_idx.item()),
                "confidence": confidence.item(),
                "context": context
            }
            if len(self.review_queue) < 20: # Limit queue size
                self.review_queue.append(prediction)
            return None # Don't return a guess if unsure

        return self.pipeline.get_category_name(predicted_idx.item())

    def learn_task(self, text: str, category: str, context: Optional[Dict] = None):
        """Adds a verified task to the training log."""
        log_path = self.user_path / "usage_log.json"
        log_data = []
        if log_path.exists():
            with open(log_path, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
        
        log_data.append({"text": text, "category": category, "context": context or {}})
        
        # Log Rotation: Keep the model focused on recent user behavior.
        MAX_LOG_ENTRIES = 500
        if len(log_data) > MAX_LOG_ENTRIES:
            # Keep the most recent N entries
            log_data = log_data[-MAX_LOG_ENTRIES:]
            print(f"AI log trimmed to the latest {MAX_LOG_ENTRIES} entries for relevance.")

        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2)
            
        # Remove from review queue if it was there
        self.review_queue = [item for item in self.review_queue if item['text'] != text]

        # Trigger auto-training if threshold is met
        self._new_samples_counter += 1
        if self._new_samples_counter >= self._training_threshold:
            print("Auto-training threshold reached. Starting background training.")
            self.train_model(background=True)
            self._new_samples_counter = 0

    def train_model(self, background: bool = True, on_finish_callback=None):
        """Initiates the model training process."""
        if self._training_worker and self._training_worker.isRunning():
            print("Training is already in progress.")
            return

        trainer = UserTrainer(self.user_id, self.user_manager)
        
        if background:
            self._training_worker = TrainingWorker(trainer)
            if on_finish_callback:
                self._training_worker.finished.connect(on_finish_callback)
            self._training_worker.finished.connect(self._on_training_complete)
            self._training_worker.start()
        else:
            trainer.train_model()
            self._on_training_complete()

    def _on_training_complete(self):
        """Called after training finishes to load the new model."""
        print("AIEngine: Training complete. Reloading model.")
        self.load_pipeline_and_model()

    def get_stats(self) -> Dict:
        """Returns statistics about the AI's state."""
        status = "Ready"
        if self._training_worker and self._training_worker.isRunning():
            status = "Training"
        elif not (self.user_path / "brain.pth").exists():
            status = "Untrained"
            
        log_path = self.user_path / "usage_log.json"
        log_count = 0
        if log_path.exists():
            with open(log_path, 'r') as f:
                log_count = len(json.load(f))

        return {
            "status": status,
            "vocab_size": len(self.pipeline.vocab),
            "task_log_count": log_count,
        }

    def get_review_queue(self) -> List[Dict]:
        """Returns the list of low-confidence predictions for user review."""
        return self.review_queue

    def get_all_categories(self) -> List[str]:
        """Returns all categories known to the AI."""
        # Ensure pipeline is loaded and has categories
        if not self.pipeline.categories:
            self.pipeline.load()
        # Fallback to app state if still empty
        return self.pipeline.categories or self.state.get("categories", [])

    def get_proactive_suggestions(self) -> List[Dict]:
        """Generates and returns actionable suggestions based on user history."""
        return analytics.generate_suggestions(self.state)

    def dismiss_suggestion(self, suggestion_id: str):
        """Adds a suggestion ID to the dismissed list to hide it."""
        dismissed = self.state.setdefault("dismissed_suggestions", [])
        if suggestion_id not in dismissed:
            dismissed.append(suggestion_id)
        # The caller is expected to schedule a save.