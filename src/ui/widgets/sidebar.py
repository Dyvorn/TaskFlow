from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt

class SidebarWidget(QWidget):
    """
    The left navigation sidebar.
    Emits `section_changed` when a user clicks a different section.
    """
    section_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("SidebarWidget")
        self.setFixedWidth(200)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 20, 0, 20)
        self.layout.setSpacing(5)

        # App Title
        title = QLabel("TaskFlow")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffd700; margin-bottom: 20px;")
        self.layout.addWidget(title)

        # Navigation Buttons
        self.buttons = {}
        sections = ["Today", "Tomorrow", "This Week", "Someday", "Archived"]
        
        for section in sections:
            btn = QPushButton(section)
            btn.setObjectName(f"nav_{section.replace(' ', '_')}")
            btn.setProperty("class", "sidebar-btn")
            btn.setCheckable(True)
            
            # Connect the click event
            # Use default argument binding `s=section` to avoid closure issues in loops
            btn.clicked.connect(lambda checked, s=section: self._on_button_clicked(s))
            
            self.layout.addWidget(btn)
            self.buttons[section] = btn

        # Spacer to push buttons to the top
        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.layout.addSpacerItem(spacer)
        
        # Set initial selection
        self.set_active_section("Today")

    def _on_button_clicked(self, section: str):
        self.set_active_section(section)
        self.section_changed.emit(section)

    def set_active_section(self, active_section: str):
        """Updates the UI to show which button is selected."""
        for section, btn in self.buttons.items():
            # Block signals temporarily so setChecked doesn't fire events
            btn.blockSignals(True)
            btn.setChecked(section == active_section)
            btn.blockSignals(False)
