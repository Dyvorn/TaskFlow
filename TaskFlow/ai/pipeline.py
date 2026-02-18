import json
import torch
from pathlib import Path
import re
import os
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
        # Define context features and their possible values (dimensions)
        self.context_features = {
            'time_of_day': ['morning', 'afternoon', 'evening', 'unknown'],
            'day_of_week': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'unknown'],
            'mood': ['Low energy', 'Okay', 'Motivated', 'Stressed', 'Great', 'unknown']
        }
        # Create a mapping from value to index for each feature type
        self.context_to_idx = {
            feature: {val: i for i, val in enumerate(values)}
            for feature, values in self.context_features.items()
        }

    def normalize(self, text: str) -> List[str]:
        """Improved text normalization: lowercase, remove punctuation, and split."""
        # Remove non-alphanumeric characters (and spaces) and convert to lowercase
        return re.sub(r'[^\w\s]', '', text.lower()).split()

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
        # Atomic save for vocab
        tmp_vocab = self.vocab_path.with_suffix(".tmp")
        with open(tmp_vocab, 'w', encoding='utf-8') as f:
            json.dump(self.vocab, f)
        if self.vocab_path.exists():
            self.vocab_path.unlink()
        tmp_vocab.rename(self.vocab_path)

        # Atomic save for categories
        tmp_cats = self.categories_path.with_suffix(".tmp")
        with open(tmp_cats, 'w', encoding='utf-8') as f:
            json.dump(self.categories, f)
        if self.categories_path.exists():
            self.categories_path.unlink()
        tmp_cats.rename(self.categories_path)

    def load(self):
        """Loads vocabulary and categories from the user's directory."""
        if self.vocab_path.exists():
            with open(self.vocab_path, 'r', encoding='utf-8') as f:
                self.vocab = json.load(f)
        if self.categories_path.exists():
            with open(self.categories_path, 'r', encoding='utf-8') as f:
                self.categories = json.load(f)
                self.cat_to_idx = {cat: i for i, cat in enumerate(self.categories)}

    def process_input(self, text: str, context: Dict) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Converts text and context into tensors for the model."""
        tokens = self.normalize(text)
        indices = [self.vocab.get(t, 0) for t in tokens]
        if not indices:
            indices = [0] # Handle empty input
            
        # Process context
        context_indices_list = []
        
        # Order must be consistent: time_of_day, day_of_week, mood
        tod_val = context.get('time_of_day', 'unknown')
        tod_idx = self.context_to_idx['time_of_day'].get(tod_val, len(self.context_to_idx['time_of_day']) - 1)
        context_indices_list.append(tod_idx)
        
        dow_val = context.get('day_of_week', 'unknown')
        dow_idx = self.context_to_idx['day_of_week'].get(dow_val, len(self.context_to_idx['day_of_week']) - 1)
        context_indices_list.append(dow_idx)
        
        mood_val = context.get('mood', 'unknown')
        mood_idx = self.context_to_idx['mood'].get(mood_val, len(self.context_to_idx['mood']) - 1)
        context_indices_list.append(mood_idx)

        return torch.tensor(indices, dtype=torch.long), torch.tensor([0], dtype=torch.long), torch.tensor([context_indices_list], dtype=torch.long)

    def get_category_index(self, category: str) -> int:
        return self.cat_to_idx.get(category, -1)
    
    def get_category_name(self, index: int) -> Optional[str]:
        return self.categories[index] if 0 <= index < len(self.categories) else None