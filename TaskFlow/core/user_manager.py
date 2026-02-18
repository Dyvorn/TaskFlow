from pathlib import Path
import os
from .model import DATA_DIR_NAME

class UserManager:
    """
    Manages paths for user-specific data, ensuring a consistent directory structure.
    """
    def __init__(self):
        if os.name == "nt":
            self.base_dir = Path(os.environ.get("APPDATA", os.path.expanduser("~"))) / DATA_DIR_NAME
        else:
            self.base_dir = Path(os.path.expanduser("~")) / f".{DATA_DIR_NAME}"
        self.base_dir.mkdir(exist_ok=True)

    def ensure_user_directory(self, user_id: str) -> Path:
        # For this app, we treat it as single-user, so user_id is mostly a placeholder.
        return self.base_dir