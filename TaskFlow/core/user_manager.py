import os
from pathlib import Path

class UserManager:
    """
    Manages user-specific data paths to ensure strict data isolation.
    This is the cornerstone of the privacy-first architecture.
    """
    def __init__(self, base_data_dir: str = "data/users"):
        """
        Initializes the UserManager with a base directory for all user data.

        Args:
            base_data_dir (str): The root folder where user subdirectories are stored.
        """
        self.base_path = Path(base_data_dir)

    def ensure_user_directory(self, user_id: str) -> Path:
        """
        Ensures that the directory for a given user_id exists, creating it if necessary.

        Args:
            user_id (str): The unique identifier for the user.

        Returns:
            Path: The absolute path to the user's data directory.
        """
        user_path = self.base_path / user_id
        os.makedirs(user_path, exist_ok=True)
        return user_path