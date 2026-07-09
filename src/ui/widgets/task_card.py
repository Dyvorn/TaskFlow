from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QCheckBox, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt

class TaskCardWidget(QWidget):
    """
    A reusable component that displays a single task.
    """
    # Emitted when the user toggles the complete checkbox
    toggled_complete = pyqtSignal(int, bool) 
    # Emitted when the user wants to delete the task
    deleted = pyqtSignal(int)

    def __init__(self, task_data: dict):
        super().__init__()
        self.task_data = task_data
        self.task_id = task_data["id"]
        
        self.setObjectName("TaskCard")
        # Give it a nice card look in QSS
        self.setProperty("class", "task-card") 
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)

        # Complete Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(bool(task_data.get("is_completed", 0)))
        self.checkbox.toggled.connect(self._on_toggled)
        self.layout.addWidget(self.checkbox)

        # Title
        title_text = task_data["title"]
        if task_data.get("is_important", 0):
            title_text = f"⭐ {title_text}"
            
        self.title_label = QLabel(title_text)
        if self.checkbox.isChecked():
            self.title_label.setStyleSheet("color: #777777; text-decoration: line-through;")
        else:
            self.title_label.setStyleSheet("color: #e0e0e0; font-size: 14px;")
            
        self.layout.addWidget(self.title_label, stretch=1)
        
        # Delete Button
        self.delete_btn = QPushButton("✕")
        self.delete_btn.setFixedSize(24, 24)
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #777777; border: none; font-size: 14px; }
            QPushButton:hover { color: #ff5555; }
        """)
        self.delete_btn.clicked.connect(lambda: self.deleted.emit(self.task_id))
        self.layout.addWidget(self.delete_btn)

    def _on_toggled(self, checked: bool):
        # Visually update immediately
        if checked:
            self.title_label.setStyleSheet("color: #777777; text-decoration: line-through;")
        else:
            self.title_label.setStyleSheet("color: #e0e0e0; font-size: 14px;")
            
        self.toggled_complete.emit(self.task_id, checked)
