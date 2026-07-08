from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QLineEdit, QPushButton, QScrollArea, QLabel
)
from PyQt6.QtCore import Qt

from core.task_manager import get_tasks, add_task, update_task_status, delete_task
from ui.widgets.task_card import TaskCardWidget

class DashboardWidget(QWidget):
    """
    The main dashboard view containing the task input and the list of tasks.
    """
    def __init__(self):
        super().__init__()
        self.current_section = "Today"
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        # 1. Header
        self.header_label = QLabel("Today")
        self.header_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        self.layout.addWidget(self.header_label)
        
        # 2. Input Area
        self.input_layout = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText(f"Add a task to Today...")
        self.task_input.setStyleSheet("""
            QLineEdit {
                background: #1e1e1e;
                color: #ffffff;
                border: 1px solid #2d2d2d;
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #ffd700;
            }
        """)
        self.task_input.returnPressed.connect(self._on_add_task)
        
        self.add_btn = QPushButton("Add")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background: #ffd700;
                color: #000000;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background: #ffea00; }
        """)
        self.add_btn.clicked.connect(self._on_add_task)
        
        self.input_layout.addWidget(self.task_input)
        self.input_layout.addWidget(self.add_btn)
        self.layout.addLayout(self.input_layout)
        
        # 3. Scrollable Task List
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.tasks_container = QWidget()
        self.tasks_container.setStyleSheet("background: transparent;")
        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.setContentsMargins(0, 10, 0, 10)
        self.tasks_layout.setSpacing(5)
        self.tasks_layout.addStretch() # Push tasks to top
        
        self.scroll_area.setWidget(self.tasks_container)
        self.layout.addWidget(self.scroll_area, stretch=1)
        
        # Initial load
        self.load_tasks()

    def set_section(self, section: str):
        """Updates the dashboard to show a different section."""
        self.current_section = section
        self.header_label.setText(section)
        self.task_input.setPlaceholderText(f"Add a task to {section}...")
        self.load_tasks()

    def load_tasks(self):
        """Fetches tasks for the current section and populates the UI."""
        # Clear existing tasks (except the stretch at the end)
        while self.tasks_layout.count() > 1:
            item = self.tasks_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        # Fetch and add new tasks
        tasks = get_tasks(section=self.current_section)
        for t in tasks:
            card = TaskCardWidget(t)
            card.toggled_complete.connect(self._on_task_toggled)
            card.deleted.connect(self._on_task_deleted)
            # Insert before the stretch
            self.tasks_layout.insertWidget(self.tasks_layout.count() - 1, card)

    def _on_add_task(self):
        title = self.task_input.text().strip()
        if not title:
            return
            
        add_task(title=title, section=self.current_section)
        self.task_input.clear()
        self.load_tasks()

    def _on_task_toggled(self, task_id: int, is_completed: bool):
        update_task_status(task_id, is_completed)
        # We don't need to reload_tasks() immediately to let the user see the checked state,
        # but the DB is updated.

    def _on_task_deleted(self, task_id: int):
        delete_task(task_id)
        self.load_tasks()
