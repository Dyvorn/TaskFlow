import json
import torch
from pathlib import Path
from typing import List, Dict, Tuple, Optional

class TaskPipeline:
    """
    Handles text processing, vocabulary management, and data preparation 
    for both training and inference.
    """
    def __init__(self, user_path: Path):
        self.user_path = user_path
        self.vocab_path = user_path / "vocab.json"
        self.categories_path = user_path / "categories.json"
        self.vocab = {"<unk>": 0}
        self.categories = []
        self.cat_to_idx = {}

    def normalize(self, text: str) -> List[str]:
        """Simple text normalization: lowercase and split."""
        return text.lower().split()

    def build_or_update_from_log(self, data: List[Dict]):
        """
        Builds or updates vocabulary and categories from log data.
        It loads existing data first to ensure persistence.
        """
        self.load() # Load existing vocab and categories first
        
        for item in data:
            tokens = self.normalize(item['text'])
            for token in tokens:
                if token not in self.vocab:
                    self.vocab[token] = len(self.vocab)
            
            cat = item['category']
            if cat not in self.categories:
                self.categories.append(cat)
        
        self.cat_to_idx = {cat: i for i, cat in enumerate(self.categories)}
        self.save()

    def save(self):
        """Saves vocabulary and categories to the user's directory."""
        with open(self.vocab_path, 'w', encoding='utf-8') as f:
            json.dump(self.vocab, f)
        with open(self.categories_path, 'w', encoding='utf-8') as f:
            json.dump(self.categories, f)

    def load(self):
        """Loads vocabulary and categories from the user's directory."""
        if self.vocab_path.exists():
            with open(self.vocab_path, 'r', encoding='utf-8') as f:
                self.vocab = json.load(f)
        if self.categories_path.exists():
            with open(self.categories_path, 'r', encoding='utf-8') as f:
                self.categories = json.load(f)
                self.cat_to_idx = {cat: i for i, cat in enumerate(self.categories)}

    def process_input(self, text: str) -> Tuple[torch.Tensor, torch.Tensor]:
        """Converts text into tensors for the model."""
        tokens = self.normalize(text)
        indices = [self.vocab.get(t, 0) for t in tokens]
        if not indices:
            indices = [0] # Handle empty input
        return torch.tensor(indices, dtype=torch.long), torch.tensor([0], dtype=torch.long)

    def get_category_index(self, category: str) -> int:
        return self.cat_to_idx.get(category, -1)
    
    def get_category_name(self, index: int) -> Optional[str]:
        return self.categories[index] if 0 <= index < len(self.categories) else None