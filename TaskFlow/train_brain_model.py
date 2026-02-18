"""
Script to train a base model for TaskFlow.
Run this to generate 'assets/base_brain.pth' and 'assets/base_vocab.json'.
"""
import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
from pathlib import Path
import shutil

# Ensure we can import from the local package
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai.architect import TaskBrain
from ai.pipeline import TaskPipeline

def train_base():
    # 1. Setup paths
    base_dir = Path(__file__).parent
    assets_dir = base_dir / "assets"
    assets_dir.mkdir(exist_ok=True)
    
    # Temp dir for training context
    temp_dir = base_dir / "temp_training"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(exist_ok=True)
    
    # 2. Create Base Training Data (Common tasks)
    # Categories must match core/model.py defaults
    training_data = [
        {"text": "Buy milk", "category": "Personal", "context": {}},
        {"text": "Call mom", "category": "Personal", "context": {}},
        {"text": "Go to the gym", "category": "Health", "context": {}},
        {"text": "Drink water", "category": "Health", "context": {}},
        {"text": "Submit report", "category": "Work", "context": {}},
        {"text": "Meeting with team", "category": "Work", "context": {}},
        {"text": "Pay rent", "category": "Finance", "context": {}},
        {"text": "Check stocks", "category": "Finance", "context": {}},
        {"text": "Learn Python", "category": "Learning", "context": {}},
        {"text": "Read documentation", "category": "Dev", "context": {}},
        {"text": "Commit changes", "category": "Dev", "context": {}},
        {"text": "Sketch new icon", "category": "Creative", "context": {}},
    ]
    
    print(f"Training on {len(training_data)} base samples...")

    # 3. Initialize Pipeline
    pipeline = TaskPipeline(temp_dir)
    pipeline.build_or_update_from_log(training_data)
    
    # 4. Initialize Model
    context_dims = [len(values) for values in pipeline.context_features.values()]
    model = TaskBrain(
        vocab_size=len(pipeline.vocab),
        hidden_size=64,
        num_classes=len(pipeline.categories),
        context_dims=context_dims
    )
    
    # 5. Train
    criterion = nn.CrossEntropyLoss()
    # Use SGD because Adam does not support sparse gradients (used in Embedding)
    optimizer = optim.SGD(model.parameters(), lr=0.1)
    
    epochs = 60
    model.train()
    for epoch in range(epochs):
        total_loss = 0
        for item in training_data:
            optimizer.zero_grad()
            # Default context
            context = item.get('context', {})
            context.setdefault('time_of_day', 'unknown')
            context.setdefault('day_of_week', 'unknown')
            context.setdefault('mood', 'unknown')
            
            text_indices, offsets, context_indices = pipeline.process_input(item['text'], context)
            target = torch.tensor([pipeline.get_category_index(item['category'])], dtype=torch.long)
            
            output = model(text_indices, offsets, context_indices)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            
    print(f"Final Loss: {total_loss:.4f}")
            
    # 6. Save Artifacts to Assets
    print("Saving artifacts to assets/...")
    
    # Atomic save for brain
    brain_path = assets_dir / "base_brain.pth"
    tmp_brain = brain_path.with_suffix(".tmp")
    torch.save(model.state_dict(), tmp_brain)
    if brain_path.exists(): brain_path.unlink()
    tmp_brain.rename(brain_path)
    
    # Atomic save for vocab
    vocab_path = assets_dir / "base_vocab.json"
    tmp_vocab = vocab_path.with_suffix(".tmp")
    with open(tmp_vocab, 'w', encoding='utf-8') as f:
        json.dump(pipeline.vocab, f, indent=2)
    if vocab_path.exists(): vocab_path.unlink()
    tmp_vocab.rename(vocab_path)
        
    # Clean up
    shutil.rmtree(temp_dir)
    print("Done! Base model ready.")

if __name__ == "__main__":
    train_base()