import torch
import torch.optim as optim
import torch.nn as nn
import json
import random
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from core.user_manager import UserManager
from .architect import TaskBrain
from .pipeline import TaskPipeline

class UserTrainer:
    """
    Handles the training loop for a single user's neural network.
    It ensures that each user's model is trained exclusively on their own data.
    """
    def __init__(self, user_id: str, user_manager: UserManager):
        """
        Initializes the trainer for a specific user.

        Args:
            user_id (str): The unique identifier for the user.
            user_manager (UserManager): The manager for handling user data paths.
        """
        self.user_id = user_id
        self.user_path = user_manager.ensure_user_directory(user_id)
        self.model_path = self.user_path / "brain.pth"
        self.log_path = self.user_path / "usage_log.json"

    def train_model(self, hidden_size: int = 64, epochs: int = 30, lr: float = 0.1):
        """
        Loads user data, trains the model, and saves the updated weights.
        """
        if not self.log_path.exists():
            print(f"No usage log found for user {self.user_id}. Skipping training.")
            return

        # 1. Load and process data (this would be more robust in pipeline.py)
        with open(self.log_path, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
            
        # Shuffle data to prevent order bias
        random.shuffle(log_data)

        # 2. Build/Update pipeline and check for vocabulary changes
        pipeline = TaskPipeline(self.user_path)
        
        # Get old vocab size before updating
        old_vocab = {}
        if pipeline.vocab_path.exists():
            with open(pipeline.vocab_path, 'r', encoding='utf-8') as f:
                old_vocab = json.load(f)

        pipeline.build_or_update_from_log(log_data)
        
        vocab_size_changed = len(old_vocab) != len(pipeline.vocab)
        
        # Get context dimensions from the pipeline
        context_dims = [len(values) for values in pipeline.context_features.values()]
        
        # 3. Initialize Model and Optimizer
        model = TaskBrain(
            vocab_size=len(pipeline.vocab), 
            hidden_size=hidden_size, 
            num_classes=len(pipeline.categories),
            context_dims=context_dims
        )
        
        # Load existing model state ONLY if vocabulary has NOT changed
        if self.model_path.exists() and not vocab_size_changed:
            try:
                # Load with strict=False to allow for architecture changes
                incompatible_keys = model.load_state_dict(torch.load(self.model_path), strict=False)
                if incompatible_keys.missing_keys or incompatible_keys.unexpected_keys:
                    print("Loaded existing brain with some new/removed layers for training.")
                else:
                    print(f"Loaded existing brain for user {self.user_id}.")
            except Exception as e:
                print(f"Could not load existing model for training, starting fresh. Error: {e}")
        elif vocab_size_changed:
            print("Vocabulary has expanded. Re-initializing model to accommodate new words.")

        criterion = nn.CrossEntropyLoss()
        optimizer = optim.SGD(model.parameters(), lr=lr)

        # 4. Training Loop
        model.train()
        print(f"Training started for {epochs} epochs...")
        for epoch in range(epochs):
            total_loss = 0
            for item in log_data:
                optimizer.zero_grad()
                # Provide context, defaulting to 'unknown' for all fields if not present in older logs
                context = item.get('context')
                if not context:  # Handle very old logs with no context key
                    context = {'time_of_day': 'unknown', 'day_of_week': 'unknown', 'mood': 'unknown', 'important': False}
                else: # Ensure all keys are present
                    context.setdefault('time_of_day', 'unknown')
                    context.setdefault('day_of_week', 'unknown')
                    context.setdefault('mood', 'unknown')
                    context.setdefault('important', False)

                text_indices, offsets, context_indices = pipeline.process_input(item['text'], context)
                target = torch.tensor([pipeline.get_category_index(item['category'])], dtype=torch.long)
                output = model(text_indices, offsets, context_indices)
                loss = criterion(output, target)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            
            if (epoch + 1) % 5 == 0:
                print(f"Epoch {epoch+1}/{epochs} - Loss: {total_loss:.4f}")

        # 5. Save the newly trained model back to the user's private directory
        tmp_model_path = self.model_path.with_suffix(".tmp")
        torch.save(model.state_dict(), tmp_model_path)
        if self.model_path.exists():
            self.model_path.unlink()
        tmp_model_path.rename(self.model_path)
        print(f"Training complete. Brain saved for user {self.user_id}.")


class TrainingWorker(QThread):
    """
    A QThread worker that runs the UserTrainer's training process in the background.
    This prevents the UI from freezing during training.
    """
    finished = pyqtSignal()

    def __init__(self, trainer: UserTrainer, parent=None):
        super().__init__(parent)
        self.trainer = trainer

    def run(self):
        """
        Executes the training process. This method is called when the thread starts.
        """
        try:
            self.trainer.train_model()
        except Exception as e:
            print(f"An error occurred during background training: {e}")
        finally:
            self.finished.emit()