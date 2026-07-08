import torch
from pathlib import Path
from typing import Optional, Dict, List, Tuple

from core.user_manager import UserManager
from .architect import TaskBrain
from .pipeline import TaskPipeline

class InferenceEngine:
    """
    Handles fast, real-time predictions for a given user.
    It loads the user's specific trained model for inference.
    """
    def __init__(self, user_id: str, user_manager: UserManager, hidden_size: int = 32):
        """
        Initializes the inference engine for a specific user.

        Args:
            user_id (str): The unique identifier for the user.
            user_manager (UserManager): The manager for handling user data paths.
            hidden_size (int): The hidden layer size, must match the trained model.
        """
        self.user_id = user_id
        self.user_path = user_manager.ensure_user_directory(user_id)
        self.model_path = self.user_path / "brain.pth"
        
        # Load the pipeline (vocab and categories)
        self.pipeline = TaskPipeline(self.user_path)
        self.pipeline.load()

        if not self.pipeline.vocab or not self.pipeline.categories:
            print(f"Warning: No vocabulary found for user {user_id}. Model cannot be initialized.")
            self.model = None
            return

        # Initialize the model architecture
        self.model = TaskBrain(vocab_size=len(self.pipeline.vocab), hidden_size=hidden_size, num_classes=len(self.pipeline.categories))

        # Load the user's trained weights if they exist
        if self.model_path.exists():
            self.model.load_state_dict(torch.load(self.model_path))
            print(f"Inference engine ready for user {self.user_id}.")
        else:
            print(f"Warning: No trained model found for user {self.user_id}. Predictions will be from an untrained model.")
        
        # Set model to evaluation mode for inference
        self.model.eval()

    def predict(self, text: str) -> Tuple[Optional[str], float]:
        """
        Predicts the category for a given text input.

        Args:
            text (str): The input text (e.g., a task description).

        Returns:
            Tuple[Optional[str], float]: The predicted category and confidence score (0.0-1.0).
        """
        if self.model is None:
            return None, 0.0
            
        with torch.no_grad():
            text_indices, offsets = self.pipeline.process_input(text)
            
            output = self.model(text_indices, offsets)
            probs = torch.softmax(output, dim=1)
            confidence, predicted_index = torch.max(probs, dim=1)
            
            return self.pipeline.get_category_name(predicted_index.item()), confidence.item()