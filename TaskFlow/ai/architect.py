import torch
import torch.nn as nn
from typing import List

class TaskBrain(nn.Module):
    """
    A neural network that classifies tasks based on their text and context.
    
    This enhanced model includes multiple embedding layers for various contextual 
    features (like time of day, day of week), which are combined with the text 
    embedding to make a more informed prediction.
    """
    def __init__(self, vocab_size: int, num_classes: int, context_dims: List[int], hidden_size: int = 32, context_embedding_dim: int = 4):
        super(TaskBrain, self).__init__()
        self.embedding = nn.EmbeddingBag(vocab_size, hidden_size, sparse=True)
        
        # Create a list of embedding layers, one for each contextual feature
        self.context_embeddings = nn.ModuleList([
            nn.Embedding(num_features, context_embedding_dim) for num_features in context_dims
        ])
        
        # The total size of the input to the linear layer is the text embedding size
        # plus the size of all context embeddings combined.
        combined_context_size = len(context_dims) * context_embedding_dim
        combined_size = hidden_size + combined_context_size
        
        self.fc = nn.Linear(combined_size, num_classes)
        self.init_weights()

    def init_weights(self):
        initrange = 0.5
        self.embedding.weight.data.uniform_(-initrange, initrange)
        for emb in self.context_embeddings:
            emb.weight.data.uniform_(-initrange, initrange)
        self.fc.weight.data.uniform_(-initrange, initrange)
        self.fc.bias.data.zero_()

    def forward(self, text_indices: torch.Tensor, offsets: torch.Tensor, context_indices: torch.Tensor) -> torch.Tensor:
        text_embedded = self.embedding(text_indices, offsets)
        
        # Process each context feature through its respective embedding layer
        context_embeds = []
        for i, embedding_layer in enumerate(self.context_embeddings):
            # context_indices is (batch_size, num_context_features)
            # We select the i-th column for the i-th embedding layer
            context_embeds.append(embedding_layer(context_indices[:, i]))
        
        all_context_embedded = torch.cat(context_embeds, dim=1)
        combined = torch.cat((text_embedded, all_context_embedded), dim=1)
        
        return self.fc(combined)