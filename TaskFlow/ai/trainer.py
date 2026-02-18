import torch
import torch.optim as optim
import torch.nn as nn
import json
from pathlib import Path

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

    def train_model(self, hidden_size: int = 32, epochs: int = 10, lr: float = 0.01):
        """
        Loads user data, trains the model, and saves the updated weights.
        """
        if not self.log_path.exists():
            print(f"No usage log found for user {self.user_id}. Skipping training.")
            return

        # 1. Load and process data (this would be more robust in pipeline.py)
        with open(self.log_path, 'r', encoding='utf-8') as f:
            log_data = json.load(f)

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
            model.load_state_dict(torch.load(self.model_path))
            print(f"Loaded existing brain for user {self.user_id}.")
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
                if not context: # Handle very old logs with no context key
                    context = {'time_of_day': 'unknown', 'day_of_week': 'unknown', 'mood': 'unknown'}
                else: # Ensure all keys are present
                    context.setdefault('day_of_week', 'unknown')
                    context.setdefault('mood', 'unknown')

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
        torch.save(model.state_dict(), self.model_path)
        print(f"Training complete. Brain saved for user {self.user_id}.")