import torch
import torch.nn as nn

class TaskBrain(nn.Module):
    """
    A simple Feed-Forward Neural Network for task classification (e.g., priority/category).
    This architecture is designed to be lightweight and fast for a local-first environment.
    
    Layers:
    1. EmbeddingBag: Efficiently converts batches of word indices into dense vectors.
    2. Linear (Hidden): A fully connected layer.
    3. ReLU: Activation function.
    4. Linear (Output): Produces logits for each class.
    """
    def __init__(self, vocab_size: int, hidden_size: int, num_classes: int):
        """
        Initializes the network layers.

        Args:
            vocab_size (int): The total number of unique words in the vocabulary.
            hidden_size (int): The number of neurons in the hidden layer.
            num_classes (int): The number of output classes (e.g., categories).
        """
        super(TaskBrain, self).__init__()
        self.embedding = nn.EmbeddingBag(vocab_size, hidden_size, sparse=True)
        self.fc1 = nn.Linear(hidden_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, num_classes)
        self.init_weights()

    def init_weights(self):
        initrange = 0.5
        self.embedding.weight.data.uniform_(-initrange, initrange)
        self.fc1.weight.data.uniform_(-initrange, initrange)
        self.fc1.bias.data.zero_()
        self.fc2.weight.data.uniform_(-initrange, initrange)
        self.fc2.bias.data.zero_()

    def forward(self, text_indices: torch.Tensor, offsets: torch.Tensor) -> torch.Tensor:
        """
        Defines the forward pass of the model.

        Args:
            text_indices (torch.Tensor): A tensor of concatenated word indices from a batch of texts.
            offsets (torch.Tensor): A tensor indicating the starting position of each text in `text_indices`.

        Returns:
            torch.Tensor: The output logits from the model.
        """
        embedded = self.embedding(text_indices, offsets)
        x = self.relu(self.fc1(embedded))
        return self.fc2(x)