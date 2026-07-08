from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt

from ui.widgets.sidebar import SidebarWidget
from ui.widgets.dashboard import DashboardWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TaskFlow Remake")
        self.resize(1000, 700)
        
        # Central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Initialize UI Components
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        # 1. Sidebar
        self.sidebar = SidebarWidget()
        self.main_layout.addWidget(self.sidebar)
        
        # 2. Main Content Area (Dashboard)
        self.dashboard = DashboardWidget()
        self.main_layout.addWidget(self.dashboard, stretch=1)

    def _connect_signals(self):
        self.sidebar.section_changed.connect(self._on_section_changed)

    def _on_section_changed(self, section: str):
        """Called when a user clicks a different section in the sidebar."""
        self.dashboard.set_section(section)

