import os
import shutil

# Configuration: Map old filenames to new paths
MOVES = {
    "taskflowai.py": "ai/engine.py",
    "taskflowmodel.py": "core/model.py",
    "taskflowanalytics.py": "core/analytics.py",
    "TaskFlowHub.py": "ui/hub.py",
    "TaskFlowWidget.py": "ui/widget.py",
    "TaskFlowApp.py": "main.py",
}

# Configuration: Content replacements to fix imports
REPLACEMENTS = {
    "ai/engine.py": [
        ("import taskflowanalytics", "import core.analytics as taskflowanalytics"),
        ("import ai.analytics as analytics", "import core.analytics as analytics"),
    ],
    "core/model.py": [],
    "core/analytics.py": [],
    "ui/hub.py": [
        ("from taskflowmodel import", "from core.model import"),
        ("import taskflowanalytics", "import core.analytics as taskflowanalytics"),
        ("import taskflowai", "from ai import engine as taskflowai"),
    ],
    "ui/widget.py": [
        ("import taskflowai", "from ai import engine as taskflowai"),
        ("from taskflowmodel import", "from core.model import"),
    ],
    "main.py": [
        ("from taskflowmodel import", "from core.model import"),
        ("from TaskFlowHub import", "from ui.hub import"),
        ("from TaskFlowWidget import", "from ui.widget import"),
    ],
    "build.py": [
        ("from taskflowmodel import", "from core.model import"),
        ('MAIN_SCRIPT = "TaskFlowHub.py"', 'MAIN_SCRIPT = "main.py"'),
        ('"--hidden-import", "taskflowanalytics",', '"--hidden-import", "core.analytics",'),
        ('"--hidden-import", "taskflowai",', '"--hidden-import", "ai.engine",'),
    ]
}

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("--- Organizing Project Structure ---")
    
    # 1. Create Directories and __init__.py
    for folder in ["ai", "core", "ui"]:
        path = os.path.join(base_dir, folder)
        os.makedirs(path, exist_ok=True)
        init_file = os.path.join(path, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write("")
            print(f"Created {folder}/__init__.py")

    # 2. Move and Update Files
    for old_name, new_rel_path in MOVES.items():
        old_path = os.path.join(base_dir, old_name)
        new_path = os.path.join(base_dir, new_rel_path)
        
        if os.path.exists(old_path):
            with open(old_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Apply replacements
            if new_rel_path in REPLACEMENTS:
                for old_str, new_str in REPLACEMENTS[new_rel_path]:
                    content = content.replace(old_str, new_str)
            
            with open(new_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            os.remove(old_path)
            print(f"Moved: {old_name} -> {new_rel_path}")
        elif os.path.exists(new_path):
            print(f"Skipped: {old_name} (Target {new_rel_path} already exists)")
        else:
            print(f"Warning: {old_name} not found")

    # 3. Update build.py (in place)
    build_path = os.path.join(base_dir, "build.py")
    if os.path.exists(build_path):
        with open(build_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        updated = False
        for old_str, new_str in REPLACEMENTS["build.py"]:
            if old_str in content:
                content = content.replace(old_str, new_str)
                updated = True
        
        if updated:
            with open(build_path, "w", encoding="utf-8") as f:
                f.write(content)
            print("Updated: build.py")

    print("--- Done! ---")
    print("Run 'python main.py' to start the app.")

if __name__ == "__main__":
    main()
