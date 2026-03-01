# ============================================================================
# SECTION 1: IMPORTS & SETUP
# ============================================================================

from __future__ import annotations

import sys
import os
import json

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import html
import random
import threading
import webbrowser
import re
import math
import ctypes
import time
import wave
import struct
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Callable

from PyQt6.QtCore import (
    Qt,
    QTimer,
    QSize,
    QPropertyAnimation,
    QEasingCurve,
    QVariantAnimation,
    QRect,
    QRectF,
    QPoint,
    QParallelAnimationGroup,
    QPointF,
    pyqtSignal, 
    QUrl,
    QMimeData,
    QThread,
)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QBrush,
    QShortcut,
    QKeySequence, 
    QTextCursor,
    QTextListFormat,
    QTextCharFormat,
    QDrag,
)
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QComboBox,
    QTextEdit,
    QSpacerItem,
    QSizePolicy,
    QGraphicsOpacityEffect,
    QMessageBox,
    QCheckBox,
    QDialogButtonBox,
    QDialog,
    QInputDialog,
    QMenu,
    QSpinBox,
    QLineEdit,
    QGraphicsDropShadowEffect,
    QSlider,
    QCalendarWidget,
    QScrollArea,
    QProgressBar,
    QSystemTrayIcon,
    QLayout,
    QStackedLayout,
)

try:
    import requests
except ImportError:
    requests = None

try:
    import winsound
except ImportError:
    winsound = None

try:
    import winreg
except ImportError:
    winreg = None

try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
except ImportError:
    QMediaPlayer = None
    QAudioOutput = None

try:
    import ctypes
except ImportError:
    ctypes = None

try:
    import pyaudio
except ImportError:
    pyaudio = None


# Shared model & theme (data model, colors, constants, helpers)
from core.model import (
    APP_NAME,
    APP_VERSION,
    DATA_DIR_NAME,
    DARK_BG,
    CARD_BG,
    HOVER_BG,
    GLASS_BG,
    GLASS_BORDER,
    TEXT_WHITE,
    TEXT_GRAY,
    GOLD,
    PRESSED_BG,
    SECTIONS,
    MOTIVATIONAL_QUOTES,
    MODE_RECOVERY,
    MODE_FOCUS,
    MODE_WRAPUP,
    ANIM_DURATION_FAST,
    ANIM_DURATION_MEDIUM,
    MOOD_OPTIONS,
    today_str,
    now_iso,
    current_time_of_day,
    get_data_paths,
    default_state,
    validate_and_migrate_state,
    load_state,
    save_state,
    get_today_mood,
    set_today_mood,
    get_user_name,
    add_idea,
    delete_idea,
    get_today_widget_note,
    set_today_widget_note,
    get_journal_entry,
    set_journal_entry,
    count_today_tasks,
    add_task,
    add_subtask,
    tasks_in_section,
    toggle_task_completed,
    delete_task,
    get_project_by_id,
    add_project,
    tasks_for_project,
    duplicate_project,
    get_today_habit_checks,
    set_habit_checked,
    rollover_tasks,
    log_activity,
    parse_version_tuple,
    is_newer_version,
    GITHUB_OWNER,
    GITHUB_REPO,
    GITHUB_API_LATEST,
    create_timestamped_backup,
    get_backups,
    restore_backup,
    parse_task_input,
    get_completion_rate,
    get_most_productive_hour,
    get_category_breakdown,
    get_productivity_score,
    get_hourly_activity,
    get_activity_heatmap_data,
    calculate_xp_for_task,
)

from .shared_widgets import AnimationManager, ConfettiOverlay, TaskRowWidget
try:
    from .coach import CoachWidget
except ImportError:
    from ui.coach import CoachWidget

# --- Voice Input Imports ---
try:
    from ai.processor import VoiceListener, CommandParser
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

# ============================================================================
# SECTION 2: APP CONFIGURATION & MODES
# ============================================================================

# App identity (imported from model)
# APP_NAME, APP_VERSION, DATA_DIR_NAME

# Theme colors (imported from model)
# DARK_BG, CARD_BG, GLASS_BG, GLASS_BORDER, HOVER_BG, PRESSED_BG
# TEXT_WHITE, TEXT_GRAY, GOLD

# Sections, quotes, mood options imported:
# SECTIONS, MOTIVATIONAL_QUOTES, MOOD_OPTIONS

# GitHub update config (imported):
# GITHUB_OWNER, GITHUB_REPO, GITHUB_API_LATEST


# ──────────────────────────────────────────────────────────────────────────
# UX tuning constants
# ──────────────────────────────────────────────────────────────────────────

PAGE_FADE_DURATION_MS = ANIM_DURATION_MEDIUM # Soft page transitions
SAVE_DEBOUNCE_MS = 800               # Delay before auto-saving after edits
SPLASH_DURATION_MS = 1200            # Total splash screen time
SPLASH_FADE_MS = 300                 # Fade in/out for splash

MAX_TODAY_SUGGESTION_TASKS = 3       # How many tasks to show in Home glance
MAX_FOCUS_CANDIDATES = 20            # Upper bound when scanning for "next" task

MAX_PLANNED_TASKS = 10               # Daily planning upper limit
DEFAULT_PLANNED_TASKS = 3            # Default suggested plan for a day

FOCUS_SESSION_SIZE = 3               # Tasks per "focus session" before suggesting a break

# ============================================================================
# SECTION 3: SPLASH SCREEN & UPDATE HELPERS
# ============================================================================


class LiquidProgressBar(QWidget):
    """
    Simple progress bar that fills from left to right.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress = 0  # 0-100
        self.setMinimumHeight(12)
        self.setMaximumHeight(12)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
    def set_progress(self, value):
        """Set progress value (0-100)"""
        self.progress = min(100, max(0, value))
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect()
        width = rect.width()
        height = rect.height()
        radius = height / 2
        
        # Draw background with rounded corners
        bg_color = QColor(60, 100, 160, 180)  # Lighter blue with transparency
        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, radius, radius)
        
        # Draw progress fill from left to right
        if self.progress > 0:
            fill_width = (width * self.progress) / 100
            
            # Use clipping to ensure the fill stays inside the rounded background
            path = QPainterPath()
            path.addRoundedRect(QRectF(rect), radius, radius)
            painter.setClipPath(path)

            gold_color = QColor(GOLD)
            gold_color.setAlpha(220)
            painter.fillRect(QRectF(0, 0, fill_width, height), gold_color)


class SplashWindow(QMainWindow):
    """
    Soft startup screen with a watery gradient and a rotating quote.

    Shown briefly at app launch before the main hub window.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        # Track timing for minimum load duration
        self._load_start_time = time.time()
        self._min_duration_ms = 2000  # Minimum 2 seconds
        self._progress_bar = None
        self.card = None

        self._build_ui()
        self._center_on_screen()

        # Start fully transparent, then fade in
        self.setWindowOpacity(0.0)
        self._fade_in()

    def _build_ui(self) -> None:
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(600, 400)

        central = QWidget(self)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Background card with gradient + glass
        self.card = QFrame()
        self.card.setObjectName("SplashCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(32, 32, 32, 24)
        card_layout.setSpacing(16)

        # Content container for fading out text separately
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(16)

        title = QLabel(APP_NAME)
        f = title.font()
        f.setPointSize(24)
        f.setBold(True)
        title.setFont(f)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {GOLD};")

        quote = QLabel(self._pick_quote())
        quote.setWordWrap(True)
        quote.setAlignment(Qt.AlignmentFlag.AlignCenter)
        quote.setStyleSheet(f"color: {TEXT_GRAY}; font-style: italic;")

        # Liquid progress bar with wave effect
        self._progress_bar = LiquidProgressBar()

        subtitle = QLabel("A gentle space to plan and breathe.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {TEXT_WHITE};")

        # Layout: title, quote, stretch, progress bar, subtitle
        self.content_layout.addWidget(title)
        self.content_layout.addWidget(quote)
        self.content_layout.addStretch()
        self.content_layout.addWidget(self._progress_bar)
        self.content_layout.addWidget(subtitle)

        card_layout.addWidget(self.content_container)
        layout.addWidget(self.card)

        # Initial Style
        self._update_style(0.0)

    def _update_style(self, progress: float) -> None:
        """Interpolates background color from Splash Gradient to Hub Dark Grey."""
        # Start: rgba(20, 30, 60, 220) -> End: rgba(18, 18, 18, 255) (#121212)
        def interp(a, b, p):
            return int(a + (b - a) * p)

        r = interp(20, 18, progress)
        g = interp(30, 18, progress)
        b = interp(60, 18, progress)
        a = interp(220, 255, progress)
        
        # Second stop for gradient (fading to flat color)
        r2 = interp(10, 18, progress)
        g2 = interp(15, 18, progress)
        b2 = interp(30, 18, progress)

        self.setStyleSheet(
            f"""
            QMainWindow {{
                background-color: transparent;
            }}
            QFrame#SplashCard {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba({r}, {g}, {b}, {a}),
                    stop:1 rgba({r2}, {g2}, {b2}, {a})
                );
                border-radius: 24px;
                border: 1px solid {GLASS_BORDER};
            }}
            """
        )

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        self.move(
            geo.center().x() - self.width() // 2,
            geo.center().y() - self.height() // 2,
        )

    def _pick_quote(self) -> str:
        # Use the same MOTIVATIONAL_QUOTES as the hub, but random per launch
        if not MOTIVATIONAL_QUOTES:
            return "Small steps still count."
        return random.choice(MOTIVATIONAL_QUOTES)

    def set_progress(self, value: int) -> None:
        """Update the progress bar (0-100)."""
        if self._progress_bar:
            self._progress_bar.set_progress(min(100, max(0, value)))

    def _fade_in(self) -> None:
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(SPLASH_FADE_MS)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: None)  # No automatic fade out
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _fade_out(self) -> None:
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(SPLASH_FADE_MS)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.finished.connect(self._on_finished)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _on_finished(self) -> None:
        self.close()

    def finish_loading(self) -> None:
        """Call this when loading is complete. Waits for minimum duration then fades out."""
        elapsed_ms = (time.time() - self._load_start_time) * 1000
        remaining_ms = max(0, self._min_duration_ms - elapsed_ms)
        
        self._progress_bar.set_progress(100)
        
        # Schedule fade out after minimum duration
        QTimer.singleShot(int(remaining_ms), self._fade_out)

    def transition_to_main(self, target_geometry: QRect, on_finished: Callable[[], None]) -> None:
        """
        Smoothly morphs the splash screen into the main window geometry/color.
        """
        # 1. Fade out content (text/progress)
        self.content_opacity = QGraphicsOpacityEffect(self.content_container)
        self.content_opacity.setOpacity(1.0)
        self.content_container.setGraphicsEffect(self.content_opacity)
        
        self.anim_content = QPropertyAnimation(self.content_opacity, b"opacity")
        self.anim_content.setDuration(300)
        self.anim_content.setStartValue(1.0)
        self.anim_content.setEndValue(0.0)
        self.anim_content.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # 2. Animate Geometry (Resize to Hub size)
        self.anim_geo = QPropertyAnimation(self, b"geometry")
        self.anim_geo.setDuration(500)
        self.anim_geo.setStartValue(self.geometry())
        self.anim_geo.setEndValue(target_geometry)
        self.anim_geo.setEasingCurve(QEasingCurve.Type.InOutQuart)
        
        # 3. Animate Color (Gradient -> Dark Grey)
        self.anim_color = QVariantAnimation()
        self.anim_color.setDuration(500)
        self.anim_color.setStartValue(0.0)
        self.anim_color.setEndValue(1.0)
        self.anim_color.setEasingCurve(QEasingCurve.Type.InOutQuart)
        self.anim_color.valueChanged.connect(self._update_style)
        
        # Group animations
        self.trans_group = QParallelAnimationGroup(self)
        self.trans_group.addAnimation(self.anim_content)
        self.trans_group.addAnimation(self.anim_geo)
        self.trans_group.addAnimation(self.anim_color)
        
        self.trans_group.finished.connect(on_finished)
        self.trans_group.start()

# ──────────────────────────────────────────────────────────────────────────
# Update helpers
# ──────────────────────────────────────────────────────────────────────────


def fetch_latest_release() -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Query GitHub for the latest release.

    Returns (tag_name, setup_download_url, error_message).
    If requests is not available or anything fails, returns (None, None, error).
    """
    if requests is None:
        return None, None, "requests not available"

    try:
        headers = {"Accept": "application/vnd.github+json"}
        resp = requests.get(GITHUB_API_LATEST, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        tag = data.get("tag_name") or ""
        download_url = None
        for asset in data.get("assets", []):
            name = asset.get("name", "").lower()
            if "setup" in name and name.endswith(".exe"):
                download_url = asset.get("browser_download_url")
                break
        return tag, download_url, None
    except Exception as e:
        return None, None, str(e)


def open_url_safe(url: str) -> None:
    """Best-effort wrapper to open a URL in the system browser."""
    try:
        webbrowser.open(url)
    except Exception:
        pass

def add_dialog_shadow(dialog: QDialog) -> None:
    """Add drop shadow effect to frameless dialog to make it appear floating."""
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(20)
    shadow.setColor(QColor(0, 0, 0, 100))
    shadow.setOffset(0, 8)
    dialog.setGraphicsEffect(shadow)


class ShadowedDialog(QDialog):
    """Base dialog class with frameless window, shadow, and rounded corners."""
    def __init__(self, parent: Optional[QWidget] = None, title: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        try:
            # Set frameless window
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        except Exception as e:
            # Fallback if attributes not supported
            pass
        
        self.setModal(True)
        
        # Create main frame with shadow
        self.shadow_frame = QFrame()
        self.shadow_frame.setObjectName("ShadowFrame")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 8)
        self.shadow_frame.setGraphicsEffect(shadow)
        
        # Create main container layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)  # Space for shadow
        main_layout.addWidget(self.shadow_frame)
        
        # Create layout for content inside frame
        self.content_layout = QVBoxLayout(self.shadow_frame)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(16)
        
        # Apply styling - transparent dialog, styled frame
        self.setStyleSheet(f"""
            QDialog {{
                background-color: transparent;
            }}
            QFrame#ShadowFrame {{
                background-color: {CARD_BG};
                border: 1px solid {GLASS_BORDER};
                border-radius: 16px;
            }}
        """)
    
    def add_widget(self, widget: QWidget) -> None:
        """Add a widget to the dialog's content layout."""
        self.content_layout.addWidget(widget)
    
    def add_layout(self, layout: QLayout) -> None:
        """Add a layout to the dialog's content layout."""
        self.content_layout.addLayout(layout)
    
    def add_stretch(self) -> None:
        """Add stretch to the dialog's content layout."""
        self.content_layout.addStretch()

    def showEvent(self, event):
        super().showEvent(event)
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

class WelcomeDialog(ShadowedDialog):
    """
    Start-of-Day screen to capture mood and main focus.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent, "Welcome Back")
        self.setMinimumWidth(400)

        # Greeting
        lbl_greet = QLabel(f"Good {current_time_of_day()}.")
        lbl_greet.setStyleSheet(f"color: {GOLD}; font-size: 22px; font-weight: bold;")
        self.add_widget(lbl_greet)

        self.add_widget(QLabel("How are you feeling right now?"))

        self.mood_combo = QComboBox()
        self.mood_combo.addItems(MOOD_OPTIONS)
        self.add_widget(self.mood_combo)

        self.add_widget(QLabel("What is your one main goal for today?"))
        self.goal_input = QLineEdit()
        self.goal_input.setPlaceholderText("e.g. Finish the report")
        self.add_widget(self.goal_input)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Start Day")
        buttons.accepted.connect(self.accept)
        self.add_widget(buttons)

        # Additional styling
        self.setStyleSheet(f"""
            {self.styleSheet()}
            QLabel {{ color: {TEXT_WHITE}; }}
            QLineEdit, QComboBox {{ 
                background-color: rgba(0,0,0,0.3); 
                color: {TEXT_WHITE}; 
                border: 1px solid {HOVER_BG}; 
                border-radius: 6px; 
                padding: 6px; 
            }}
            QLineEdit:focus, QComboBox:focus {{ border: 1px solid {GOLD}; }}
            QPushButton {{
                background-color: {HOVER_BG}; color: {TEXT_WHITE}; border-radius: 6px; padding: 6px 16px; border: 1px solid {GLASS_BORDER};
            }}
            QPushButton:hover {{ background-color: {GOLD}; color: {DARK_BG}; border: none; }}
        """)

    def get_data(self) -> Dict[str, Any]:
        return {
            "mood": self.mood_combo.currentText(),
            "primaryGoal": self.goal_input.text().strip()
        }

# ============================================================================
# SECTION 4: DIALOGS & SMALL VISUAL WIDGETS
# ============================================================================


class DailyPlanningDialog(ShadowedDialog):
    """
    Gentle dialog shown once per day to set a realistic number of tasks.

    It acknowledges leftover tasks and encourages a light plan.
    """

    def __init__(self, incomplete_today_count: int, parent: Optional[QWidget] = None):
        super().__init__(parent, "Daily planning")
        self.setMinimumWidth(360)

        if incomplete_today_count > 0:
            info = (
                f"You have {incomplete_today_count} incomplete task(s) carried over."
                "\nLet's set a gentle plan for today."
            )
        else:
            info = "Ready for a fresh start. Let's plan today lightly."
        info_label = QLabel(info)
        info_label.setWordWrap(True)
        self.add_widget(info_label)

        self.add_widget(QLabel("How many tasks do you realistically want to focus on today?"))

        self.spinbox = QSpinBox()
        self.spinbox.setRange(0, MAX_PLANNED_TASKS)
        self.spinbox.setValue(DEFAULT_PLANNED_TASKS)
        self.add_widget(self.spinbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.add_widget(buttons)

        self.setStyleSheet(f"""
            {self.styleSheet()}
            QLabel {{
                color: {TEXT_WHITE};
            }}
            QSpinBox {{
                background-color: rgba(0,0,0,0.3);
                color: {TEXT_WHITE};
                border-radius: 6px;
                border: 1px solid {HOVER_BG};
                padding: 2px 6px;
            }}
        """)

    def planned_tasks(self) -> int:
        return self.spinbox.value()

class FeedbackDialog(ShadowedDialog):
    """
    Dialog to direct users to feedback channels.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent, "Feedback & Requests")
        self.resize(400, 300)
        self._build_ui()

    def _build_ui(self):
        lbl_title = QLabel("Feedback & Requests")
        lbl_title.setStyleSheet(f"color: {GOLD}; font-size: 20px; font-weight: bold;")
        self.add_widget(lbl_title)

        lbl_info = QLabel("Help us improve TaskFlow. Found a bug or have a feature idea?")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet(f"color: {TEXT_GRAY};")
        self.add_widget(lbl_info)

        # GitHub Issues
        btn_gh = QPushButton("🐞 Report Bug / 💡 Feature Request (GitHub)")
        btn_gh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_gh.setStyleSheet(f"background-color: {HOVER_BG}; color: {TEXT_WHITE}; border-radius: 8px; padding: 12px; border: 1px solid {GLASS_BORDER}; text-align: left; font-weight: bold;")
        btn_gh.clicked.connect(self._open_github)
        self.add_widget(btn_gh)

        # Email
        btn_email = QPushButton("📧 Send Email")
        btn_email.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_email.setStyleSheet(f"background-color: {HOVER_BG}; color: {TEXT_WHITE}; border-radius: 8px; padding: 12px; border: 1px solid {GLASS_BORDER}; text-align: left; font-weight: bold;")
        btn_email.clicked.connect(self._open_email)
        self.add_widget(btn_email)

        self.add_stretch()

        btn_close = QPushButton("Close")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(f"background-color: rgba(255,255,255,0.1); color: {TEXT_WHITE}; border-radius: 6px; padding: 8px;")
        btn_close.clicked.connect(self.accept)
        self.add_widget(btn_close)

        self.setStyleSheet(f"{self.styleSheet()} QLabel {{ color: {TEXT_WHITE}; }}")

    def _open_github(self):
        url = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/issues"
        open_url_safe(url)
        self.accept()

    def _open_email(self):
        # Generic mailto
        url = "mailto:?subject=TaskFlow Feedback"
        open_url_safe(url)
        self.accept()

class QuickTipsDialog(ShadowedDialog):
    """
    Dialog showing shortcuts and features.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent, "Quick Tips & Shortcuts")
        self.resize(500, 550)
        self._build_ui()

    def _build_ui(self):
        lbl_title = QLabel("💡 Tips & Tricks")
        lbl_title.setStyleSheet(f"color: {GOLD}; font-size: 22px; font-weight: bold;")
        self.add_widget(lbl_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setSpacing(20)

        def add_section(title, items):
            lbl = QLabel(title)
            lbl.setStyleSheet(f"color: {TEXT_WHITE}; font-weight: bold; font-size: 16px; margin-top: 10px;")
            c_layout.addWidget(lbl)
            for key, desc in items:
                row = QHBoxLayout()
                k_lbl = QLabel(key)
                k_lbl.setStyleSheet(f"color: {GOLD}; font-weight: bold; font-family: monospace; background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px;")
                d_lbl = QLabel(desc)
                d_lbl.setStyleSheet(f"color: {TEXT_GRAY};")
                d_lbl.setWordWrap(True)
                row.addWidget(k_lbl)
                row.addWidget(d_lbl, 1)
                c_layout.addLayout(row)

        add_section("⌨️ Keyboard Shortcuts", [
            ("Ctrl+1-6", "Navigate between pages"),
            ("Ctrl+B", "Toggle Focus Mode (Hide Sidebar)"),
            ("Delete", "Delete selected task"),
            ("Double Click", "Edit task text"),
        ])

        add_section("🧠 Smart Input", [
            ("tomorrow", "Schedules task for tomorrow"),
            ("next week", "Schedules task for next week"),
            ("#Work", "Categorizes task as 'Work'"),
            ("!important", "Marks task as important"),
        ])

        add_section("✨ Features", [
            ("Brain Dump", "Type a list of thoughts, AI sorts them for you."),
            ("Zen Mode", "Click 'Up Next' or any task to focus on just one thing."),
            ("Journal", "Write daily. AI analyzes sentiment to give advice."),
        ])

        c_layout.addStretch()
        scroll.setWidget(content)
        
        # Style the scrollbar
        scrollbar = scroll.verticalScrollBar()
        scrollbar.setStyleSheet(f"""
            QScrollBar:vertical {{
                border: none;
                background: {HOVER_BG};
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: #e0e0e0;
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        self.add_widget(scroll)

        btn_close = QPushButton("Got it")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(f"background-color: {HOVER_BG}; color: {TEXT_WHITE}; border-radius: 8px; padding: 10px;")
        btn_close.clicked.connect(self.accept)
        self.add_widget(btn_close)

        self.setStyleSheet(f"{self.styleSheet()}")

class BackupManagerDialog(ShadowedDialog):
    """
    Dialog to manage backups.
    """
    def __init__(self, paths: Dict[str, str], parent: Optional[QWidget] = None):
        super().__init__(parent, title="Backup Manager")
        self.paths = paths
        self.resize(400, 400)
        self._build_ui()

    def _build_ui(self):
        self.add_widget(QLabel("Available Backups"))
        
        self.list = QListWidget()
        self.list.setStyleSheet(f"background-color: rgba(0,0,0,0.3); color: {TEXT_WHITE}; border: 1px solid {HOVER_BG}; border-radius: 6px;")
        self._refresh_list()
        self.add_widget(self.list)

        btn_create = QPushButton("Create New Backup")
        btn_create.clicked.connect(self._create_backup)
        self.add_widget(btn_create)

        btn_restore = QPushButton("Restore Selected")
        btn_restore.clicked.connect(self._restore_backup)
        self.add_widget(btn_restore)

        self.setStyleSheet(f"{self.styleSheet()} QLabel {{ color: {TEXT_WHITE}; }} QPushButton {{ background-color: {HOVER_BG}; color: {TEXT_WHITE}; border-radius: 6px; padding: 8px; }} QPushButton:hover {{ background-color: {GOLD}; color: {DARK_BG}; }}")

    def _refresh_list(self):
        self.list.clear()
        backups = get_backups(self.paths)
        for b in backups:
            self.list.addItem(b)

    def _create_backup(self):
        name = create_timestamped_backup(self.paths)
        if name:
            QMessageBox.information(self, "Success", f"Backup created: {name}")
            self._refresh_list()
        else:
            QMessageBox.warning(self, "Error", "Failed to create backup.")

    def _restore_backup(self):
        item = self.list.currentItem()
        if not item: return
        
        filename = item.text()
        reply = QMessageBox.question(self, "Restore Backup", f"Are you sure you want to restore '{filename}'?\nCurrent data will be overwritten.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            if restore_backup(self.paths, filename):
                QMessageBox.information(self, "Success", "Backup restored. Please restart TaskFlow.")
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "Failed to restore backup.")

class BrainDumpDialog(ShadowedDialog):
    """
    A dialog for bulk task entry with AI processing options.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent, title="Brain Dump 🧠")
        self.resize(500, 400)
        
        lbl = QLabel("Unload your mind. Type a list or a paragraph, and we'll sort it out.")
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 14px;")
        self.add_widget(lbl)
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("e.g.\n- Buy milk\n- Call John about the project\n- Finish the report by Friday")
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: rgba(0, 0, 0, 0.3);
                color: {TEXT_WHITE};
                border: 1px solid {HOVER_BG};
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }}
            QTextEdit:focus {{
                border: 1px solid {GOLD};
            }}
        """)
        self.add_widget(self.text_edit)
        
        # Options row
        opt_layout = QHBoxLayout()
        self.chk_ai = QCheckBox("Use AI to guess categories & priority")
        self.chk_ai.setChecked(True)
        self.chk_ai.setStyleSheet(f"""
            QCheckBox {{ color: {TEXT_WHITE}; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 4px; border: 1px solid {HOVER_BG}; }}
            QCheckBox::indicator:checked {{ background-color: {GOLD}; border: 1px solid {GOLD}; }}
        """)
        opt_layout.addWidget(self.chk_ai)
        opt_layout.addStretch()
        
        btn_clear = QPushButton("Clear")
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setStyleSheet(f"color: {TEXT_GRAY}; background: transparent; border: none;")
        btn_clear.clicked.connect(self.text_edit.clear)
        opt_layout.addWidget(btn_clear)
        
        self.add_layout(opt_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Process Tasks")
        
        # Style buttons
        for btn in buttons.buttons():
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"background-color: {HOVER_BG}; color: {TEXT_WHITE}; border-radius: 6px; padding: 6px 16px; border: 1px solid {GLASS_BORDER};")
        
        # Highlight primary
        buttons.button(QDialogButtonBox.StandardButton.Ok).setStyleSheet(f"background-color: {GOLD}; color: {DARK_BG}; border-radius: 6px; padding: 6px 16px; font-weight: bold; border: none;")
        
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.add_widget(buttons)

class WaveformWidget(QWidget):
    """
    Visualizes audio amplitude as a dynamic bar chart.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.levels = [0.0] * 30  # Keep last 30 frames
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def update_level(self, level: float):
        self.levels.pop(0)
        self.levels.append(level)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        bar_w = w / len(self.levels)
        center_y = h / 2
        
        for i, level in enumerate(self.levels):
            # Scale level for visibility (non-linear)
            scaled = min(1.0, level ** 0.5)
            bar_h = max(2, h * scaled * 0.8)
            
            x = i * bar_w
            y = center_y - bar_h / 2
            
            painter.setBrush(QColor(GOLD))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setOpacity(0.4 + (scaled * 0.6))
            painter.drawRoundedRect(QRectF(x + 1, y, bar_w - 2, bar_h), 2, 2)

class VoiceDialog(ShadowedDialog):
    """
    Visual feedback during voice recording.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent, title="Voice Input")
        self.resize(300, 220)
        
        lbl_icon = QLabel("🎙️")
        lbl_icon.setStyleSheet("font-size: 48px;")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.add_widget(lbl_icon)
        
        lbl_text = QLabel("Listening...")
        lbl_text.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 18px; font-weight: bold;")
        lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.add_widget(lbl_text)
        
        self.waveform = WaveformWidget()
        self.add_widget(self.waveform)

    def update_level(self, level: float):
        if hasattr(self, "waveform"):
            self.waveform.update_level(level)

class SomedayReviewDialog(ShadowedDialog):
    """
    Dialog to review a few random tasks from Someday.
    """
    def __init__(self, tasks: List[Dict[str, Any]], state: Dict[str, Any], save_callback, parent: Optional[QWidget] = None):
        super().__init__(parent, title="Review Someday Tasks")
        self.tasks = tasks
        self.state = state
        self.save_callback = save_callback
        self.resize(400, 400)
        self._build_ui()

    def _build_ui(self):
        lbl = QLabel("Here are 3 tasks from your Someday list. Still relevant?")
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 14px;")
        self.add_widget(lbl)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.content = QWidget()
        self.content.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setSpacing(10)
        self.content_layout.addStretch() # Push items to top
        self.scroll.setWidget(self.content)
        self.add_widget(self.scroll)
        
        # Insert tasks at the beginning (before stretch)
        for t in self.tasks:
            self._add_task_row(t)
            
        btn_close = QPushButton("Done")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet(f"background-color: {HOVER_BG}; color: {TEXT_WHITE}; border-radius: 6px; padding: 8px 16px; border: 1px solid {GLASS_BORDER};")
        self.add_widget(btn_close)

    def _add_task_row(self, task):
        frame = QFrame()
        frame.setStyleSheet(f"background-color: rgba(0,0,0,0.2); border-radius: 8px; padding: 10px; border: 1px solid {HOVER_BG};")
        fl = QVBoxLayout(frame)
        fl.setSpacing(8)
        
        lbl = QLabel(task.get("text", ""))
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {TEXT_WHITE}; font-weight: bold; font-size: 14px;")
        fl.addWidget(lbl)
        
        btns = QHBoxLayout()
        btns.setSpacing(10)
        
        btn_today = QPushButton("Move to Today")
        btn_today.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_today.setStyleSheet(f"color: {GOLD}; background: transparent; text-align: left; font-weight: bold;")
        btn_today.clicked.connect(lambda: self._move_to_today(task, frame))
        
        btn_del = QPushButton("Delete")
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet(f"color: #ff6b6b; background: transparent; text-align: left;")
        btn_del.clicked.connect(lambda: self._delete_task(task, frame))
        
        btn_keep = QPushButton("Keep")
        btn_keep.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_keep.setStyleSheet(f"color: {TEXT_GRAY}; background: transparent; text-align: left;")
        btn_keep.clicked.connect(lambda: self._keep_task(frame))
        
        btns.addWidget(btn_today)
        btns.addWidget(btn_del)
        btns.addWidget(btn_keep)
        btns.addStretch()
        
        fl.addLayout(btns)
        
        # Insert before the stretch (which is the last item)
        self.content_layout.insertWidget(self.content_layout.count() - 1, frame)

    def _move_to_today(self, task, frame):
        task["section"] = "Today"
        task["updatedAt"] = now_iso()
        self.save_callback()
        self._animate_remove(frame)

    def _delete_task(self, task, frame):
        delete_task(self.state, task.get("id"))
        self.save_callback()
        self._animate_remove(frame)

    def _keep_task(self, frame):
        self._animate_remove(frame)

    def _animate_remove(self, frame):
        effect = QGraphicsOpacityEffect(frame)
        frame.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", frame)
        anim.setDuration(300)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        anim.finished.connect(lambda: self._finalize_remove(frame))
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _finalize_remove(self, frame):
        frame.hide()
        frame.deleteLater()

class WeeklyReviewDialog(ShadowedDialog):
    """
    Dialog for weekly review (Mondays).
    Shows stats and offers to archive completed tasks.
    """
    def __init__(self, state: Dict[str, Any], save_callback, parent: Optional[QWidget] = None):
        super().__init__(parent, title="Weekly Review")
        self.state = state
        self._save_callback = save_callback
        self.resize(400, 300)
        self._build_ui()

    def _build_ui(self):
        lbl_title = QLabel("Weekly Review 📅")
        lbl_title.setStyleSheet(f"color: {GOLD}; font-size: 22px; font-weight: bold;")
        self.add_widget(lbl_title)

        # Stats
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        week_ago_iso = week_ago.isoformat()
        
        completed_count = 0
        for t in self.state.get("tasks", []):
            if t.get("completed") and t.get("updatedAt", "") >= week_ago_iso:
                completed_count += 1
        
        lbl_info = QLabel(f"You completed {completed_count} tasks in the last 7 days.\nReady for a fresh start?")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 14px;")
        self.add_widget(lbl_info)

        # Mood summary
        self.add_widget(QLabel("Mood Trend:"))
        mood_graph = MoodGraphWidget(self.state)
        mood_graph.setFixedHeight(60)
        self.add_widget(mood_graph)

        self.chk_archive = QCheckBox("Archive completed tasks")
        self.chk_archive.setChecked(True)
        self.chk_archive.setStyleSheet(f"color: {TEXT_WHITE};")
        self.add_widget(self.chk_archive)

        self.add_stretch()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        # Style buttons
        for btn in buttons.buttons():
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"background-color: {HOVER_BG}; color: {TEXT_WHITE}; border-radius: 6px; padding: 6px 16px; border: 1px solid {GLASS_BORDER};")
            
        self.add_widget(buttons)

class MoodGraphWidget(QWidget):
    """
    Simple 14‑day mood history bar graph.

    Uses mood entries from the shared state, grouped by date.
    """

    def __init__(self, state: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state = state
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        moods = self.state.get("moods", [])

        # Map mood value -> score
        val_map = {
            "Low energy": 1,
            "Stressed": 1,
            "Okay": 2,
            "Motivated": 3,
            "Great": 4,
        }

        # Build date -> mood value map (last entry per day wins)
        mood_map: Dict[str, str] = {}
        for m in moods:
            d = m.get("date")
            v = m.get("value")
            if d and v:
                mood_map[d] = v

        days = 14
        bar_width = rect.width() / days if days > 0 else rect.width()
        max_h = rect.height() - 10

        painter.setPen(Qt.PenStyle.NoPen)

        today = date.today()

        for i in range(days):
            d = today - timedelta(days=days - 1 - i)
            d_str = str(d)
            val_str = mood_map.get(d_str, "")
            score = val_map.get(val_str, 0)

            if score <= 0:
                # Draw a faint baseline tick
                h = 4
                color = QColor(TEXT_GRAY)
                color.setAlpha(60)
            else:
                h = int(score / 4 * max_h)
                if score <= 1:
                    color = QColor("#ff6b6b")  # red-ish for heavy days
                elif score == 2:
                    color = QColor("#feca57")  # orange
                elif score == 3:
                    color = QColor("#1dd1a1")  # greenish
                else:
                    color = QColor(GOLD)

            x = int(i * bar_width + 2)
            y = rect.height() - h
            w = int(bar_width - 4)

            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(QRectF(x, y, w, h), 4, 4)

        # Baseline
        painter.setBrush(QBrush(QColor(HOVER_BG)))
        painter.drawRect(QRectF(2, rect.height() - 2, rect.width() - 4, 2))


class HabitGraphWidget(QWidget):
    """
    Simple 14‑day habit completion graph.

    Each bar shows how many active habits were checked that day.
    """

    def __init__(self, state: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state = state
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        checks = self.state.get("habitChecks", {})
        habits = self.state.get("habits", [])

        active_habits = [h for h in habits if h.get("active", True)]
        active_count = max(1, len(active_habits))

        days = 14
        bar_width = rect.width() / days if days > 0 else rect.width()
        max_h = rect.height() - 10

        painter.setPen(Qt.PenStyle.NoPen)

        today = date.today()

        for i in range(days):
            d = today - timedelta(days=days - 1 - i)
            d_str = str(d)
            day_checks = checks.get(d_str, {})
            completed = sum(1 for v in day_checks.values() if v)
            ratio = completed / active_count
            h = int(ratio * max_h)

            if h <= 0:
                # draw a faint baseline tick for no completion
                color = QColor(TEXT_GRAY)
                color.setAlpha(60)
            else:
                color = QColor(GOLD if ratio >= 1.0 else TEXT_GRAY)

            x = int(i * bar_width + 2)
            y = rect.height() - h
            w = int(bar_width - 4)

            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(QRectF(x, y, w, h), 4, 4)

        painter.setBrush(QBrush(QColor(HOVER_BG)))
        painter.drawRect(QRectF(2, rect.height() - 2, rect.width() - 4, 2))

class CategoryGraphWidget(QWidget):
    """
    Visualizes task completion by category using simple bars.
    """
    def __init__(self, state: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state = state
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        
        data = get_category_breakdown(self.state)
        if not data:
            painter.setPen(QColor(TEXT_GRAY))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No categorized data yet.")
            return

        total = sum(data.values())
        max_val = max(data.values()) if data.values() else 1
        
        bar_height = 16
        spacing = 8
        y = 10
        
        sorted_cats = sorted(data.items(), key=lambda x: x[1], reverse=True)[:5] # Top 5
        
        for cat, count in sorted_cats:
            # Label
            painter.setPen(QColor(TEXT_WHITE))
            painter.drawText(0, y + 12, f"{cat} ({count})")
            
            # Bar
            bar_width = int((count / max_val) * (rect.width() - 100))
            painter.setBrush(QColor(GOLD))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(100, y, bar_width, bar_height, 4, 4)
            
            y += bar_height + spacing

class ProductivityScoreWidget(QWidget):
    """
    Circular progress bar showing the daily productivity score.
    """
    def __init__(self, state: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state = state
        self.setMinimumSize(140, 140)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
    def paintEvent(self, event) -> None:
        score = get_productivity_score(self.state)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        center = rect.center()
        radius = int(min(rect.width(), rect.height()) / 2 - 10)
        
        # Background track
        painter.setPen(QPen(QColor(HOVER_BG), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawEllipse(center, radius, radius)
        
        # Arc
        painter.setPen(QPen(QColor(GOLD), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        # Qt draws arcs in 1/16th degrees. 360 degrees = 360 * 16.
        # Start at 90 (top), go negative (clockwise).
        span = int((score / 100.0) * 360 * 16)
        painter.drawArc(int(center.x() - radius), int(center.y() - radius), int(radius*2), int(radius*2), 90 * 16, -span)
        
        # Text
        painter.setPen(QColor(TEXT_WHITE))
        f = painter.font()
        f.setPointSize(28)
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(score))
        
        f.setPointSize(10)
        f.setBold(False)
        painter.setFont(f)
        painter.drawText(rect.adjusted(0, 40, 0, 0), Qt.AlignmentFlag.AlignCenter, "Daily Score")

class HourlyChartWidget(QWidget):
    """
    Bar chart showing activity by hour of day.
    """
    def __init__(self, state: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state = state
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        
        data = get_hourly_activity(self.state)
        max_val = max(data.values()) if data else 1
        
        bar_width = rect.width() / 24
        
        for h in range(24):
            val = data.get(h, 0)
            if val > 0:
                h_ratio = val / max_val
                bar_h = h_ratio * (rect.height() - 20)
                x = h * bar_width
                y = rect.height() - bar_h - 15
                
                painter.setBrush(QColor(GOLD))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(QRectF(x + 2, y, bar_width - 4, bar_h), 2, 2)
            
            # Hour labels every 6 hours
            if h % 6 == 0:
                painter.setPen(QColor(TEXT_GRAY))
                painter.drawText(QRectF(h * bar_width, rect.height() - 12, bar_width * 2, 12), Qt.AlignmentFlag.AlignLeft, f"{h:02}")

class HeatmapWidget(QWidget):
    """
    GitHub-style contribution graph (last 52 weeks).
    """
    def __init__(self, state: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state = state
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        data = get_activity_heatmap_data(self.state)
        today = date.today()
        
        # Calculate start date (52 weeks ago, aligned to Sunday)
        start_date = today - timedelta(weeks=52)
        start_date = start_date - timedelta(days=start_date.weekday() + 1) # Align to Sunday
        
        cell_size = 10
        spacing = 3
        
        for week in range(53):
            for day in range(7):
                curr_date = start_date + timedelta(weeks=week, days=day)
                if curr_date > today:
                    continue
                
                date_str = str(curr_date)
                count = data.get(date_str, 0)
                
                # Color based on count
                alpha = 30 if count == 0 else min(255, 60 + count * 40)
                color = QColor(GOLD)
                color.setAlpha(alpha)
                
                x = week * (cell_size + spacing)
                y = day * (cell_size + spacing)
                
                painter.setBrush(color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(x, y, cell_size, cell_size, 2, 2)

class ToastOverlay(QWidget):
    """
    Non-intrusive notification pill that fades in and out.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Style: Dark pill with light text, subtle border
        self.label.setStyleSheet(f"""
            background-color: #252525;
            color: {TEXT_WHITE};
            border: 1px solid {GLASS_BORDER};
            border-radius: 20px;
            padding: 8px 24px;
            font-weight: bold;
            font-size: 14px;
        """)
        
        # Shadow
        shadow = QGraphicsDropShadowEffect(self.label)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 4)
        self.label.setGraphicsEffect(shadow)
        
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(self._on_anim_finished)
        
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.fade_out)
        
        self.hide()

    def show_message(self, text, duration=2500):
        self.label.setText(text)
        self.label.adjustSize() # Recalculate size
        self.resize(self.label.width() + 10, self.label.height() + 10) # slight padding for shadow
        self.label.move(5, 5)
        
        if self.parent():
            p_rect = self.parent().rect()
            x = (p_rect.width() - self.width()) // 2
            y = p_rect.height() - self.height() - 60 # Position near bottom
            self.move(x, y)
            
        self.show()
        self.raise_()
        self.opacity_effect.setOpacity(0.0)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setDirection(QPropertyAnimation.Direction.Forward)
        self.anim.start()
        
        self.timer.start(duration)

    def fade_out(self):
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setDirection(QPropertyAnimation.Direction.Forward)
        self.anim.start()

    def _on_anim_finished(self):
        if self.opacity_effect.opacity() == 0.0:
            self.hide()

class ProjectListRow(QWidget):
    """
    Custom widget for the project list item, showing progress bar.
    """
    def __init__(self, project: Dict[str, Any], tasks: List[Dict[str, Any]], is_focus: bool, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Header: Name + Count
        header = QHBoxLayout()
        name_text = project.get("name", "Untitled")
        if is_focus: name_text += " (Widget)"
        
        name_lbl = QLabel(name_text)
        name_lbl.setStyleSheet(f"color: {project.get('color', GOLD)}; font-weight: bold;")
        header.addWidget(name_lbl)
        
        header.addStretch()
        
        proj_tasks = [t for t in tasks if t.get("projectId") == project["id"]]
        total = len(proj_tasks)
        done = len([t for t in proj_tasks if t.get("completed")])
        
        count_lbl = QLabel(f"{done}/{total}")
        count_lbl.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 11px;")
        header.addWidget(count_lbl)
        
        layout.addLayout(header)
        
        # Progress Bar
        if total > 0:
            bar = QProgressBar()
            bar.setFixedHeight(4)
            bar.setTextVisible(False)
            bar.setRange(0, total)
            bar.setValue(done)
            bar.setStyleSheet(f"QProgressBar {{ border: none; background-color: {HOVER_BG}; border-radius: 2px; }} QProgressBar::chunk {{ background-color: {project.get('color', GOLD)}; border-radius: 2px; }}")
            layout.addWidget(bar)

class VoiceWorker(QThread):
    """
    Background thread to handle recording and transcription to avoid freezing UI.
    """
    finished = pyqtSignal(list) # list of action dicts
    error = pyqtSignal(str)
    amplitude = pyqtSignal(float)

    def __init__(self, listener, parser, duration=5):
        super().__init__()
        self.listener = listener
        self.parser = parser
        self.duration = duration

    def run(self):
        if not self.listener or not self.listener.model:
            self.error.emit("Voice AI model is not loaded yet.")
            return

        # 1. Record
        audio_path = "temp_voice.wav"
        
        # We implement the recording loop here to emit amplitude signals
        if pyaudio:
            try:
                chunk = 1024
                fmt = pyaudio.paInt16
                chans = 1
                rate = 16000
                
                p = pyaudio.PyAudio()
                stream = p.open(format=fmt, channels=chans, rate=rate, input=True, frames_per_buffer=chunk)
                
                frames = []
                for _ in range(0, int(rate / chunk * self.duration)):
                    data = stream.read(chunk)
                    frames.append(data)
                    
                    # Calculate RMS amplitude
                    shorts = struct.unpack("%dh" % (len(data) // 2), data)
                    sum_squares = sum(s**2 for s in shorts)
                    rms = math.sqrt(sum_squares / len(shorts))
                    self.amplitude.emit(min(1.0, rms / 32768.0))
                
                stream.stop_stream()
                stream.close()
                p.terminate()
                
                with wave.open(audio_path, 'wb') as wf:
                    wf.setnchannels(chans)
                    wf.setsampwidth(p.get_sample_size(fmt))
                    wf.setframerate(rate)
                    wf.writeframes(b''.join(frames))
            except Exception as e:
                self.error.emit(f"Recording error: {e}")
                return
        else:
            # Fallback if pyaudio missing (though VoiceListener checks it too)
            audio_path = self.listener.record_audio(duration=self.duration)
            if not audio_path:
                self.error.emit("Recording failed. Check microphone.")
                return

        # 2. Transcribe
        text = self.listener.transcribe(audio_path)
        
        # Check for transcription errors returned as text
        if text.startswith("Error:") or text.startswith("Transcription error:"):
            self.error.emit(text)
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except:
                pass
            return
        
        # 3. Parse
        actions = self.parser.parse(text)
        self.finished.emit(actions)
        
        # Cleanup
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except:
            pass

class BreathingCircle(QWidget):
    """
    A widget that displays a breathing animation (expanding/contracting circle).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scale_factor = 1.0
        self.anim = QVariantAnimation()
        self.anim.setDuration(8000)  # 4s in, 4s out
        self.anim.setStartValue(1.0)
        self.anim.setKeyValueAt(0.5, 1.5) # Expand to 1.5x
        self.anim.setEndValue(1.0)
        self.anim.setLoopCount(-1)
        self.anim.valueChanged.connect(self._update_scale)
        self.text = "Breathe In"

    def _update_scale(self, value):
        self.scale_factor = value
        # Update text based on phase
        progress = self.anim.currentTime() / self.anim.duration()
        if progress < 0.5:
            self.text = "Breathe In"
        else:
            self.text = "Breathe Out"
        self.update()

    def start_animation(self):
        self.anim.start()

    def stop_animation(self):
        self.anim.stop()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        center = rect.center()
        # Base radius
        base_radius = min(rect.width(), rect.height()) / 6
        radius = base_radius * self.scale_factor
        
        # Draw circle
        color = QColor("#4ECDC4") # Teal
        color.setAlpha(150)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, int(radius), int(radius))
        
        # Draw text
        painter.setPen(QColor(255, 255, 255))
        f = painter.font()
        f.setPointSize(16)
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text)

# ============================================================================
# SECTION 5: TASK LIST WIDGETS (TODAY / WEEK / SOMEDAY / PROJECTS)
# ============================================================================

class TaskCalendarWidget(QCalendarWidget):
    """
    Custom calendar that paints dots for tasks.
    """
    taskDropped = pyqtSignal(str, object) # task_id, date

    def __init__(self, state: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state = state
        self.setGridVisible(False)
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.setNavigationBarVisible(True)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        
        # Styling
        self.setStyleSheet(f"""
            QCalendarWidget QWidget {{ alternate-background-color: {CARD_BG}; }}
            QCalendarWidget QAbstractItemView:enabled {{
                color: {TEXT_WHITE};
                background-color: transparent;
                selection-background-color: {HOVER_BG};
                selection-color: {GOLD};
                border-radius: 6px;
            }}
            QCalendarWidget QMenu {{ color: {TEXT_WHITE}; background-color: {CARD_BG}; }}
            QCalendarWidget QSpinBox {{ color: {TEXT_WHITE}; background-color: {DARK_BG}; selection-background-color: {GOLD}; selection-color: {DARK_BG}; }}
            QCalendarWidget QToolButton {{ color: {TEXT_WHITE}; background-color: transparent; icon-size: 24px; border-radius: 4px; }}
            QCalendarWidget QToolButton:hover {{ background-color: {HOVER_BG}; }}
            QCalendarWidget QToolButton#qt_calendar_prevmonth {{ qproperty-icon: url(left_arrow.png); }} 
            QCalendarWidget QToolButton#qt_calendar_nextmonth {{ qproperty-icon: url(right_arrow.png); }}
        """)

    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)
        
        date_str = date.toString(Qt.DateFormat.ISODate)
        tasks = [t for t in self.state.get("tasks", []) if (t.get("schedule") or {}).get("date") == date_str and not t.get("completed")]
        
        if tasks:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            dot_size = 4
            spacing = 3
            total_width = min(len(tasks), 5) * dot_size + (min(len(tasks), 5) - 1) * spacing
            start_x = rect.center().x() - total_width / 2
            y = rect.bottom() - 6
            
            for i, t in enumerate(tasks):
                if i >= 5: break
                color = QColor("#ff6b6b") if t.get("important") else (QColor("#4ECDC4") if t.get("category") == "Work" else QColor(GOLD))
                painter.setBrush(color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(start_x + i * (dot_size + spacing) + dot_size/2, y), dot_size/2, dot_size/2)
            painter.restore()

    def mouseMoveEvent(self, event):
        # Show tooltip with task count
        # Note: QCalendarWidget structure is complex, this is a best-effort mapping
        super().mouseMoveEvent(event)
        # We can't easily map pixel to date without internal access, 
        # but we can show a general tooltip if hovering a cell with tasks?
        # For now, let's rely on the visual dots.
        pass

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/taskflow-task"):
            event.accept()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/taskflow-task"):
            event.accept()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/taskflow-task"):
            task_id = event.mimeData().text()
            # Drop on the calendar sets it to the currently selected date (simplest reliable interaction)
            # Enhancing to drop on specific cell requires internal QTableView access which is fragile in PyQt6
            self.taskDropped.emit(task_id, self.selectedDate())
            event.accept()
        else:
            super().dropEvent(event)

class ReorderableListWidget(QListWidget):
    """
    A QListWidget that supports internal drag-and-drop reordering.
    """
    orderChanged = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        # Allow both internal move and dragging out
        self.setDragDropMode(QListWidget.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)

    def mimeData(self, items):
        mime = super().mimeData(items)
        if items:
            tid = items[0].data(Qt.ItemDataRole.UserRole)
            mime.setData("application/taskflow-task", tid.encode())
            mime.setText(tid)
        return mime

    def dropEvent(self, event) -> None:
        super().dropEvent(event)
        self.orderChanged.emit()

class TaskListWidget(QWidget):
    """
    Simple vertical task list for a given section (Today, This Week, Someday).

    Handles:
    - Quick add
    - Per-task actions (complete, delete, rename, move, mark important, assign project)
    - Section-wide actions (mark all done, clear completed, send completed to Someday)
    - Optional "What should I do next?" / focus suggestion for Today
    """
    requestFocus = pyqtSignal(str)

    def __init__(self, state: Dict[str, Any], section: str, save_callback, ai_engine=None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state = state
        self.section = section
        self._save_callback = save_callback
        self.ai_engine = ai_engine

        self._build_ui()
        self.refresh()

    # ────────────────────────────────────────────────────────────────────
    # UI construction
    # ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(6)

        lbl = QLabel(self.section)
        lbl.setObjectName("PageHeader")
        header.addWidget(lbl)

        header.addStretch(1)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet(
            f"""
            QLabel {{
                color: {TEXT_GRAY};
                font-size: 12px;
                background-color: {HOVER_BG};
                border-radius: 10px;
                padding: 2px 8px;
            }}
            """
        )
        header.addWidget(self.progress_label)

        header.addStretch(1)

        # Today-only helper button
        if self.section == "Today":
            self.btn_next = QPushButton("What should I do next?")
            self.btn_next.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {HOVER_BG};
                    color: {GOLD};
                    font-weight: bold;
                    border-radius: 12px;
                    padding: 4px 10px;
                    border: 1px solid {GLASS_BORDER};
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 40);
                }}
                """
            )
            self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_next.clicked.connect(self._suggest_next_task)
            header.addWidget(self.btn_next)

            # Magic Sort Button (Today only)
            self.btn_sort = QPushButton("✨")
            self.btn_sort.setFixedSize(28, 28)
            self.btn_sort.setToolTip("Magic Sort: Reorder based on your habits & time of day")
            self.btn_sort.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_sort.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: transparent;
                    border-radius: 14px;
                    color: {GOLD};
                    font-size: 14px;
                }}
                QPushButton:hover {{ background-color: {HOVER_BG}; }}
                """
            )
            self.btn_sort.clicked.connect(self._magic_sort)
            header.addWidget(self.btn_sort)

        # Someday review button
        if self.section == "Someday":
            self.btn_review = QPushButton("Review 3 Random")
            self.btn_review.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {HOVER_BG};
                    color: {GOLD};
                    font-weight: bold;
                    border-radius: 12px;
                    padding: 4px 10px;
                    border: 1px solid {GLASS_BORDER};
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 40);
                }}
                """
            )
            self.btn_review.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_review.clicked.connect(self._review_someday_tasks)
            header.addWidget(self.btn_review)

        # Section menu button
        self.menu_btn = QPushButton("⋯")
        self.menu_btn.setFixedSize(26, 26)
        self.menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border-radius: 13px;
                border: 1px solid rgba(255,255,255,40);
                color: #f2f2f2;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,30);
            }
            """
        )
        self.menu_btn.clicked.connect(self._show_section_menu)
        header.addWidget(self.menu_btn)

        layout.addLayout(header)

        # Quick add row
        self.quick_add_input = QLineEdit()
        placeholder = "Quick add…" if self.section == "Today" else f"Add task to {self.section}…"
        self.quick_add_input.setPlaceholderText(placeholder + " (use #Work for category)")
        self.quick_add_input.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid {HOVER_BG};
                border-radius: 6px;
                padding: 4px 8px;
                color: {TEXT_WHITE};
            }}
            """
        )
        self.quick_add_input.returnPressed.connect(self._on_quick_add)
        layout.addWidget(self.quick_add_input)

        hint_label = QLabel("Tip: Right-click tasks for options.")
        hint_label.setStyleSheet(f"color: {TEXT_GRAY}; font-style: italic; font-size: 11px;")
        layout.addWidget(hint_label)

        # Empty label
        self.empty_label = QLabel("")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.empty_label.setStyleSheet(f"color: {TEXT_GRAY}; font-style: italic;")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        # Task list
        self.tasks_list = ReorderableListWidget()
        self.tasks_list.orderChanged.connect(self._on_reorder)
        
        
        # Enable selection for keyboard navigation/deletion
        self.tasks_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        
        # Style selection to be subtle
        self.tasks_list.setStyleSheet(f"""
            QListWidget::item:selected {{ background-color: {HOVER_BG}; border-radius: 8px; }}
        """)
        layout.addWidget(self.tasks_list, 1)

    # ────────────────────────────────────────────────────────────────────
    # Refresh & rendering
    # ────────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Rebuild the list for the current section."""
        scroll_pos = self.tasks_list.verticalScrollBar().value()
        
        # Preserve selection
        selected_id = None
        if self.tasks_list.currentItem():
            selected_id = self.tasks_list.currentItem().data(Qt.ItemDataRole.UserRole)
            
        self.tasks_list.setUpdatesEnabled(False)
        self.tasks_list.clear()

        tasks = tasks_in_section(self.state, self.section)
        total = len(tasks)
        completed = len([t for t in tasks if t.get("completed")])

        self.progress_label.setText(f"{completed} / {total} done")

        # Empty state text
        if total == 0:
            self.tasks_list.setVisible(False)
            self.empty_label.setVisible(True)
            if self.section == "Today":
                self.empty_label.setText(
                    "No tasks for Today.\n\nUse Brain Dump to unload your mind, then pick 1 small win."
                )
            elif self.section == "This Week":
                self.empty_label.setText(
                    "No tasks for This Week.\n\nBrain Dump helps you plan ahead."
                )
            elif self.section == "Someday":
                self.empty_label.setText(
                    "No ideas yet.\n\nBrain Dump is the fastest way to capture them."
                )
            else:
                self.empty_label.setText(f"No tasks in {self.section}.")
        else:
            self.tasks_list.setVisible(True)
            self.empty_label.setVisible(False)

            # Render rows
            for t in tasks:
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, t.get("id"))

                row = TaskRowWidget(t)
                row.toggled.connect(self._on_toggle_task)
                row.deleted.connect(self._on_delete_task)
                row.contextMenuRequested.connect(
                    lambda pos, tid, r=row: self._show_task_menu(tid, r.mapToGlobal(pos))
                )
                row.editRequested.connect(self._rename_task)
                row.focusRequested.connect(self.requestFocus)

                self.tasks_list.addItem(item)
                item.setSizeHint(row.sizeHint())
                self.tasks_list.setItemWidget(item, row)

                # Cascade animation for visible items
                if total < 20: # Only animate if list isn't huge to save perf
                    AnimationManager.fade_in(row, duration=300, delay=(len(self.tasks_list)-1) * 40)

        self.tasks_list.setUpdatesEnabled(True)
        
        # Restore selection
        if selected_id:
            for i in range(self.tasks_list.count()):
                item = self.tasks_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == selected_id:
                    self.tasks_list.setCurrentItem(item)
                    break
                    
        self.tasks_list.verticalScrollBar().setValue(scroll_pos)

    def _on_reorder(self):
        """Update the order field in the state based on the new list order."""
        for i in range(self.tasks_list.count()):
            item = self.tasks_list.item(i)
            tid = item.data(Qt.ItemDataRole.UserRole)
            # Find task and update order
            for t in self.state.get("tasks", []):
                if t.get("id") == tid:
                    t["order"] = i
                    break
        self._save_callback()

    # ────────────────────────────────────────────────────────────────────
    # Handlers & actions
    # ────────────────────────────────────────────────────────────────────

    def _on_quick_add(self) -> None:
        text = self.quick_add_input.text().strip()
        if not text:
            return
            
        # Use AI to infer category
        category = "Personal" # Default
        if self.ai_engine:
            context = {
                "time_of_day": current_time_of_day(),
                "day_of_week": datetime.now().strftime("%A"),
                "mood": get_today_mood(self.state).get("value", "Unknown") if get_today_mood(self.state) else "Unknown"
            }
            pred_cat = self.ai_engine.predict_category(text, context)
            if pred_cat:
                category = pred_cat
        
        # Simple section logic for now (can be expanded)
        target_section = self.section
        
        # 10.0: AI Analysis
        difficulty = 1
        xp = 10
        duration = 0
        
        if self.ai_engine:
            difficulty = self.ai_engine.analyze_task_complexity(text)
            xp = difficulty * 15 # Higher scaling
            duration = self.ai_engine.estimate_duration(text)
        
        task = add_task(
            self.state, 
            text=text, 
            section=target_section, 
            category=category, 
            important=False,
            schedule=None,
            difficulty=difficulty,
            xpReward=xp,
            estimatedDuration=duration
        )
        
        # Dopamine: Flash input success
        original_style = self.quick_add_input.styleSheet()
        self.quick_add_input.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: rgba(255, 215, 0, 0.15);
                border: 1px solid {GOLD};
                border-radius: 6px;
                padding: 4px 8px;
                color: {TEXT_WHITE};
            }}
            """
        )
        QTimer.singleShot(250, lambda: self.quick_add_input.setStyleSheet(original_style))
        
        self._save_callback()
        self.quick_add_input.clear()
        self.refresh()

        # If task stayed in this section, animate it
        if target_section == self.section:
            for i in range(self.tasks_list.count()):
                item = self.tasks_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == task["id"]:
                    self.tasks_list.scrollToItem(item)
                    row = self.tasks_list.itemWidget(item)
                    if row:
                        AnimationManager.fade_in(row)
                    break
        else:
            # Task moved elsewhere
            self.empty_label.setText(f"Task added to {target_section}.")
            self.empty_label.setVisible(True)
            QTimer.singleShot(2000, self.refresh)

    def _on_toggle_task(self, task_id: str) -> None:
        task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
        if not task:
            return

        is_completing = not task.get("completed", False)

        if is_completing:
            if winsound:
                try: winsound.MessageBeep(winsound.MB_OK)
                except: pass
            
            # Trigger confetti via main window
            if self.window() and hasattr(self.window(), "celebrate"):
                self.window().celebrate()

            # 10.0: XP Reward
            xp_gain = calculate_xp_for_task(task)
            stats = self.state.setdefault("stats", {})
            old_xp = stats.get("xp", 0)
            new_xp = old_xp + xp_gain
            stats["xp"] = new_xp
            
            # Level Up Check (Level = 1 + XP/500)
            if int(1 + (new_xp / 500)) > int(1 + (old_xp / 500)):
                self.window().show_toast(f"🎉 LEVEL UP! You are now Level {int(1 + (new_xp / 500))}!")
            else:
                self.window().show_toast(f"Completed! +{xp_gain} XP")

            for i in range(self.tasks_list.count()):
                item = self.tasks_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == task_id:
                    row = self.tasks_list.itemWidget(item)
                    if row:
                        AnimationManager.slide_and_fade_out(row, on_finished=lambda: self._finalize_toggle(task_id))
                    return
        else:
            toggle_task_completed(self.state, task_id)
            self._save_callback()
            self.refresh()

    def _finalize_toggle(self, task_id: str):
        toggle_task_completed(self.state, task_id)
        self._save_callback()
        # self.refresh() is called via the data_changed signal from save_callback

    def _on_delete_task(self, task_id: str) -> None:
        delete_task(self.state, task_id)
        self._save_callback()
        self.refresh()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            item = self.tasks_list.currentItem()
            if item:
                tid = item.data(Qt.ItemDataRole.UserRole)
                self._on_delete_task(tid)
        super().keyPressEvent(event)

    def _show_section_menu(self) -> None:
        menu = QMenu(self)
        mark_all_done = menu.addAction("Mark all done")
        clear_completed = menu.addAction("Clear completed tasks")
        send_completed_someday = None

        if self.section != "Someday":
            send_completed_someday = menu.addAction("Send completed to Someday")

        action = menu.exec(
            self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft())
        )
        if action is None:
            return

        if action is mark_all_done:
            for task in tasks_in_section(self.state, self.section):
                if not task.get("completed"):
                    task["completed"] = True
                    task["updatedAt"] = now_iso()
            self._save_callback()
            self.refresh()
        elif action is clear_completed:
            self.state["tasks"] = [
                t
                for t in self.state.get("tasks", [])
                if t.get("section") != self.section or not t.get("completed")
            ]
            self._save_callback()
            self.refresh()
        elif send_completed_someday and action is send_completed_someday:
            for task in tasks_in_section(self.state, self.section):
                if task.get("completed"):
                    task["section"] = "Someday"
                    task["updatedAt"] = now_iso()
            self._save_callback()
            self.refresh()

    def _show_task_menu(self, task_id: str, global_pos) -> None:
        menu = QMenu(self)
        task = next(
            (t for t in self.state.get("tasks", []) if t.get("id") == task_id), None
        )
        if not task:
            return

        is_important = task.get("important", False)

        act_rename = menu.addAction("Rename")
        act_important = menu.addAction(
            "Unmark important" if is_important else "Mark as important"
        )
        
        menu.addSeparator()
        act_schedule = menu.addAction("Schedule...")
        act_recur = menu.addAction("Repeat...")

        # 10.0: AI Breakdown
        menu.addSeparator()
        act_breakdown = menu.addAction("✨ Break down (AI)")
        act_zen = menu.addAction("🧘 Focus (Zen Mode)")

        move_menu = menu.addMenu("Move to…")
        for sec in ["Today", "Tomorrow", "This Week", "Someday"]:
            if sec != self.section:
                move_menu.addAction(sec)

        proj_menu = menu.addMenu("Assign to project")
        projects = self.state.get("projects", [])
        if not projects:
            proj_menu.setEnabled(False)
        else:
            for p in projects:
                act = proj_menu.addAction(p.get("name", "Untitled"))
                act.setData(p.get("id"))

        action = menu.exec(global_pos)
        if not action:
            return

        if action is act_rename:
            self._rename_task(task_id)
        elif action is act_important:
            self._set_task_important(task_id, not is_important)
        elif action is act_schedule:
            self._prompt_schedule(task_id)
        elif action is act_recur:
            self._prompt_recurrence(task_id)
        elif action is act_breakdown:
            self._on_break_down_task(task_id)
        elif action is act_zen:
            self.requestFocus.emit(task_id)
        elif action.parent() is move_menu:
            new_section = action.text()
            self._move_task_section(task_id, new_section)
        elif action.parent() is proj_menu:
            proj_id = action.data()
            self._assign_task_project(task_id, proj_id)

    def _rename_task(self, task_id: str) -> None:
        task = next(
            (t for t in self.state.get("tasks", []) if t.get("id") == task_id), None
        )
        if not task:
            return
        current_text = task.get("text", "")
        new_text, ok = QInputDialog.getText(
            self, "Rename task", "New name:", text=current_text
        )
        if ok and new_text.strip():
            task["text"] = new_text.strip()
            task["updatedAt"] = now_iso()
            self._save_callback()
            self.refresh()

    def _prompt_schedule(self, task_id: str) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Pick Date")
        l = QVBoxLayout(dlg)
        cal = QCalendarWidget()
        l.addWidget(cal)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        l.addWidget(btns)
        
        if dlg.exec() == QDialog.DialogCode.Accepted:
            date_str = cal.selectedDate().toString(Qt.DateFormat.ISODate)
            self._set_task_schedule(task_id, date_str)

    def _set_task_schedule(self, task_id: str, date_str: str) -> None:
        task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
        if not task: return
        
        task["schedule"] = {"date": date_str}
        # Auto-move based on date
        if date_str > today_str():
            task["section"] = "Scheduled"
        elif date_str <= today_str():
            task["section"] = "Today"
            
        task["updatedAt"] = now_iso()
        self._save_callback()
        self.refresh()

    def _prompt_recurrence(self, task_id: str) -> None:
        items = ["None", "Daily", "Weekly", "Monthly"]
        val, ok = QInputDialog.getItem(self, "Repeat Task", "Frequency:", items, 0, False)
        if ok:
            task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
            if task:
                task["recurrence"] = None if val == "None" else {"type": val.lower()}
                task["updatedAt"] = now_iso()
                self._save_callback()
                self.refresh()

    def _set_task_important(self, task_id: str, important: bool) -> None:
        task = next(
            (t for t in self.state.get("tasks", []) if t.get("id") == task_id), None
        )
        if not task:
            return
        task["important"] = important
        task["updatedAt"] = now_iso()
        self._save_callback()
        self.refresh()

    def _move_task_section(self, task_id: str, new_section: str) -> None:
        if new_section not in SECTIONS:
            return
        task = next(
            (t for t in self.state.get("tasks", []) if t.get("id") == task_id), None
        )
        if not task:
            return
        task["section"] = new_section
        task["updatedAt"] = now_iso()
        self._save_callback()
        self.refresh()

    def _assign_task_project(self, task_id: str, project_id: Optional[str]) -> None:
        task = next(
            (t for t in self.state.get("tasks", []) if t.get("id") == task_id), None
        )
        if not task:
            return
        task["projectId"] = project_id
        task["updatedAt"] = now_iso()
        self._save_callback()
        self.refresh()

    def _on_break_down_task(self, task_id: str) -> None:
        """Uses AI to split a task into subtasks."""
        task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
        if not task or not self.ai_engine:
            return
            
        subtasks_text = self.ai_engine.generate_subtasks(task.get("text", ""))
        
        if not subtasks_text:
            self.window().show_toast("Could not generate subtasks.")
            return
            
        # Add as true subtasks
        for st_text in subtasks_text:
            add_subtask(
                self.state,
                parent_task_id=task_id,
                text=st_text
            )
            
        self._save_callback()
        self.refresh()
        self.window().show_toast(f"Created {len(subtasks_text)} subtasks for '{task['text']}'.")

    def _suggest_next_task(self) -> None:
        """
        Highlight a gentle next step for Today.

        Picks the first incomplete task, preferring important ones and respecting order.
        """
        if self.section != "Today":
            return

        # Dopamine: Pulse button
        effect = QGraphicsOpacityEffect(self.btn_next)
        self.btn_next.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(200)
        anim.setKeyValueAt(0.0, 1.0)
        anim.setKeyValueAt(0.5, 0.5)
        anim.setKeyValueAt(1.0, 1.0)
        anim.finished.connect(lambda: self.btn_next.setGraphicsEffect(None))
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

        tasks = tasks_in_section(self.state, "Today")
        candidates = [
            t for t in tasks if not t.get("completed")
        ][:MAX_FOCUS_CANDIDATES]
        if not candidates:
            # Show a subtle hint when nothing is left
            QMessageBox.information(
                self,
                "Nothing urgent",
                "Nothing urgent left for Today.\nYou can rest or check your Projects.",
            )
            return

        # Smart scoring based on Mood + AI Difficulty
        mood = get_today_mood(self.state)
        mood_val = mood.get("value") if mood else "Okay"
        
        # If low energy, prefer easy tasks. If motivated, prefer hard/important.
        prefer_easy = mood_val in ["Low energy", "Stressed"]
        
        def score_task(t):
            s = 0
            if t.get("important"): s += 10
            if t.get("due_time"): s += 5
            
            diff = t.get("difficulty", 1)
            if prefer_easy:
                # Higher score for lower difficulty
                s += (5 - diff) * 2
            else:
                # Bonus for tackling hard things
                s += diff
                
            return s
            
        target = max(candidates, key=score_task)
        target_id = target.get("id")

        # Find the corresponding item
        for i in range(self.tasks_list.count()):
            item = self.tasks_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == target_id:
                self.tasks_list.scrollToItem(item)
                row = self.tasks_list.itemWidget(item)
                if row:
                    self._flash_row(row)
                break

    def _magic_sort(self) -> None:
        """Reorders the Today list using AI logic."""
        tasks = tasks_in_section(self.state, "Today")
        incomplete = [t for t in tasks if not t.get("completed")]
        completed = [t for t in tasks if t.get("completed")]
        
        # Rank incomplete tasks
        ranked = incomplete
        if self.ai_engine:
            context = {
                "time_of_day": current_time_of_day(),
                "day_of_week": datetime.now().strftime("%A"),
                "mood": get_today_mood(self.state).get("value", "Unknown") if get_today_mood(self.state) else "Unknown"
            }
            ranked = self.ai_engine.rank_tasks(incomplete, context)
        
        # Apply new order (0, 1, 2...)
        for i, t in enumerate(ranked + completed):
            t["order"] = i
        
        self._save_callback()
        self.refresh()
        
        # Visual feedback
        self.btn_sort.setStyleSheet(f"background-color: {GOLD}; color: {DARK_BG}; border-radius: 14px;")
        QTimer.singleShot(400, lambda: self.btn_sort.setStyleSheet(f"background-color: transparent; border-radius: 14px; color: {GOLD};"))

    def _flash_row(self, row: QWidget) -> None:
        """Temporarily highlight a row to draw attention."""
        effect = QGraphicsOpacityEffect(row)
        row.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(250)
        anim.setStartValue(0.4)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: row.setGraphicsEffect(None))
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _review_someday_tasks(self) -> None:
        tasks = tasks_in_section(self.state, "Someday")
        incomplete = [t for t in tasks if not t.get("completed")]
        
        if not incomplete:
            self.show_toast("No tasks in Someday to review.")
            return
            
        # Pick 3 random
        count = min(3, len(incomplete))
        picks = random.sample(incomplete, count)
        
        dlg = SomedayReviewDialog(picks, self.state, self._save_callback, self)
        dlg.exec()
        self.refresh()

class ProjectTaskListWidget(QWidget):
    """
    Task list widget specifically for a single project.

    Shows only tasks with projectId == current project.
    Supports:
    - Quick add into this project (default section Someday)
    - Send selected to Today
    - Mark all project tasks done
    """

    def __init__(
        self,
        state: Dict[str, Any],
        save_callback,
        ai_engine=None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.state = state
        self._save_callback = save_callback
        self.ai_engine = ai_engine
        self._project_id: Optional[str] = None

        self._build_ui()
        self.refresh()

    # ────────────────────────────────────────────────────────────────────
    # UI
    # ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        # Info line + actions
        info_row = QHBoxLayout()
        info_row.setSpacing(6)

        self.info_label = QLabel("No project selected.")
        self.info_label.setStyleSheet(f"color: {TEXT_GRAY};")
        info_row.addWidget(self.info_label, 1)

        # AI Suggest Button
        self.btn_suggest = QPushButton("✨ Suggest Tasks")
        self.btn_suggest.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_suggest.setToolTip("Use AI to generate tasks for this project")
        self.btn_suggest.clicked.connect(self._on_suggest_tasks)
        self.btn_suggest.setVisible(False) # Hidden by default until project selected
        info_row.addWidget(self.btn_suggest)

        self.btn_send_today = QPushButton("Send selected to Today")
        self.btn_send_today.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send_today.clicked.connect(self._on_send_selected_to_today)
        info_row.addWidget(self.btn_send_today)

        self.btn_mark_all = QPushButton("Mark all done")
        self.btn_mark_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mark_all.clicked.connect(self._on_mark_all_done)
        info_row.addWidget(self.btn_mark_all)

        self.btn_clear_completed = QPushButton("Clear completed")
        self.btn_clear_completed.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_completed.clicked.connect(self._on_clear_completed)
        info_row.addWidget(self.btn_clear_completed)

        layout.addLayout(info_row)

        # Quick add
        self.quick_add_input = QLineEdit()
        self.quick_add_input.setPlaceholderText("Add task to this project…")
        self.quick_add_input.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid {HOVER_BG};
                border-radius: 6px;
                padding: 4px 8px;
                color: {TEXT_WHITE};
            }}
            """
        )
        self.quick_add_input.returnPressed.connect(self._on_quick_add)
        layout.addWidget(self.quick_add_input)

        # Empty label
        self.empty_label = QLabel("No project selected.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.empty_label.setStyleSheet(f"color: {TEXT_GRAY}; font-style: italic;")
        layout.addWidget(self.empty_label)

        # Task list
        self.tasks_list = QListWidget()
        self.tasks_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.tasks_list.setStyleSheet(
            "QListWidget { background-color: transparent; border: none; }"
        )
        layout.addWidget(self.tasks_list, 1)

    # ────────────────────────────────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────────────────────────────────

    def set_project(self, project_id: Optional[str]) -> None:
        self._project_id = project_id
        self.refresh()

    # ────────────────────────────────────────────────────────────────────
    # Refresh
    # ────────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        self.tasks_list.clear()

        if not self._project_id:
            self._set_enabled(False)
            self.info_label.setText("No project selected.")
            self.empty_label.setText("Select a project on the left to see its tasks.")
            self.empty_label.setVisible(True)
            return

        self._set_enabled(True)

        tasks = tasks_for_project(self.state, self._project_id)
        
        # Sort: Incomplete first, then Important, then by order
        tasks.sort(key=lambda t: (
            1 if t.get("completed") else 0,
            0 if t.get("important") else 1,
            t.get("order", 0)
        ))

        open_count = len([t for t in tasks if not t.get("completed")])
        done_count = len([t for t in tasks if t.get("completed")])

        in_today = len(
            [
                t
                for t in tasks
                if t.get("section") == "Today" and not t.get("completed")
            ]
        )

        self.info_label.setText(
            f"{open_count} open · {done_count} done · {in_today} in Today"
        )

        if not tasks:
            self.empty_label.setText("No tasks in this project. Add one above.")
            self.empty_label.setVisible(True)
            return

        self.empty_label.setVisible(False)

        for t in tasks:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, t.get("id"))

            row = TaskRowWidget(t, show_focus_button=False)
            row.toggled.connect(self._on_toggle_task)
            row.deleted.connect(self._on_delete_task)
            row.contextMenuRequested.connect(
                lambda pos, tid, r=row: self._show_task_menu(tid, r.mapToGlobal(pos))
            )
            row.editRequested.connect(self._rename_task)

            self.tasks_list.addItem(item)
            item.setSizeHint(row.sizeHint())
            self.tasks_list.setItemWidget(item, row)

    def _set_enabled(self, enabled: bool) -> None:
        self.quick_add_input.setEnabled(enabled)
        self.btn_send_today.setEnabled(enabled)
        self.btn_mark_all.setEnabled(enabled)
        self.btn_clear_completed.setEnabled(enabled)
        self.btn_suggest.setEnabled(enabled)
        self.tasks_list.setEnabled(enabled)

    # ────────────────────────────────────────────────────────────────────
    # Handlers
    # ────────────────────────────────────────────────────────────────────

    def _on_quick_add(self) -> None:
        text = self.quick_add_input.text().strip()
        if not text or not self._project_id:
            return
            
        # AI Enrichment
        difficulty = 1
        xp = 10
        duration = 0
        category = "Work" # Default for projects
        
        if self.ai_engine:
            difficulty = self.ai_engine.analyze_task_complexity(text)
            xp = difficulty * 15
            duration = self.ai_engine.estimate_duration(text)
            # We could predict category, but usually projects imply a category context

        task = add_task(
            self.state,
            text=text,
            section="Someday",
            project_id=self._project_id,
            category=category,
            difficulty=difficulty,
            xpReward=xp,
            estimatedDuration=duration
        )
        
        # Dopamine: Flash input success (Consistent with main list)
        original_style = self.quick_add_input.styleSheet()
        self.quick_add_input.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: rgba(255, 215, 0, 0.15);
                border: 1px solid {GOLD};
                border-radius: 6px;
                padding: 4px 8px;
                color: {TEXT_WHITE};
            }}
            """
        )
        QTimer.singleShot(250, lambda: self.quick_add_input.setStyleSheet(original_style))

        self._save_callback()
        self.quick_add_input.clear()
        self.refresh()

        # Animate the new item
        for i in range(self.tasks_list.count()):
            item = self.tasks_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == task["id"]:
                self.tasks_list.scrollToItem(item)
                row = self.tasks_list.itemWidget(item)
                if row:
                    AnimationManager.fade_in(row)
                break

    def _on_toggle_task(self, task_id: str) -> None:
        task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
        if not task:
            return

        is_completing = not task.get("completed", False)

        if is_completing:
            if winsound:
                try: winsound.MessageBeep(winsound.MB_OK)
                except: pass
                
            for i in range(self.tasks_list.count()):
                item = self.tasks_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == task_id:
                    row = self.tasks_list.itemWidget(item)
                    if row:
                        AnimationManager.slide_and_fade_out(row, on_finished=lambda: self._finalize_toggle(task_id))
                    return
        else:
            toggle_task_completed(self.state, task_id)
            self._save_callback()
            self.refresh()

    def _finalize_toggle(self, task_id: str):
        """This is called after the completion animation finishes."""
        toggle_task_completed(self.state, task_id)
        self._save_callback()
        # self.refresh() is called via the data_changed signal from save_callback

    def _on_delete_task(self, task_id: str) -> None:
        delete_task(self.state, task_id)
        self._save_callback()
        self.refresh()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            item = self.tasks_list.selectedItems()
            if item:
                tid = item[0].data(Qt.ItemDataRole.UserRole)
                self._on_delete_task(tid)
        super().keyPressEvent(event)

    def _on_send_selected_to_today(self) -> None:
        if not self._project_id:
            return
        for item in self.tasks_list.selectedItems():
            tid = item.data(Qt.ItemDataRole.UserRole)
            for t in self.state.get("tasks", []):
                if t.get("id") == tid:
                    t["section"] = "Today"
                    t["updatedAt"] = now_iso()
        self._save_callback()
        self.refresh()

    def _on_mark_all_done(self) -> None:
        if not self._project_id:
            return
        for t in tasks_for_project(self.state, self._project_id):
            if not t.get("completed"):
                t["completed"] = True
                t["updatedAt"] = now_iso()
        self._save_callback()
        self.refresh()

    def _on_clear_completed(self) -> None:
        if not self._project_id:
            return
        
        # Remove completed tasks belonging to this project
        original_count = len(self.state.get("tasks", []))
        self.state["tasks"] = [
            t for t in self.state.get("tasks", [])
            if not (t.get("projectId") == self._project_id and t.get("completed"))
        ]
        
        if len(self.state["tasks"]) < original_count:
            self._save_callback()
            self.refresh()

    def _show_task_menu(self, task_id: str, global_pos) -> None:
        menu = QMenu(self)
        task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
        if not task: return

        act_rename = menu.addAction("Rename")
        act_important = menu.addAction("Unmark important" if task.get("important") else "Mark as important")
        
        move_menu = menu.addMenu("Move to…")
        for sec in ["Today", "Tomorrow", "This Week", "Someday"]:
            if sec != task.get("section"):
                move_menu.addAction(sec)
        act_delete = menu.addAction("Delete")

        action = menu.exec(global_pos)
        if not action: return

        if action is act_rename:
            self._rename_task(task_id)
        elif action is act_important:
            self._toggle_important(task_id)
        elif action.parent() is move_menu:
            self._move_task_section(task_id, action.text())
        elif action is act_delete:
            self._on_delete_task(task_id)

    def _rename_task(self, task_id: str) -> None:
        task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
        if not task: return
        new_text, ok = QInputDialog.getText(self, "Rename task", "New name:", text=task.get("text", ""))
        if ok and new_text.strip():
            task["text"] = new_text.strip()
            task["updatedAt"] = now_iso()
            self._save_callback()
            self.refresh()

    def _toggle_important(self, task_id: str) -> None:
        task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
        if not task: return
        task["important"] = not task.get("important")
        task["updatedAt"] = now_iso()
        self._save_callback()
        self.refresh()

    def _move_task_section(self, task_id: str, new_section: str) -> None:
        task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
        if not task: return
        task["section"] = new_section
        task["updatedAt"] = now_iso()
        self._save_callback()
        self.refresh()

    def _on_suggest_tasks(self) -> None:
        if not self._project_id or not self.ai_engine:
            return
            
        proj = get_project_by_id(self.state, self._project_id)
        if not proj: return
        
        suggestions = self.ai_engine.generate_project_tasks(proj.get("name", ""))
        if not suggestions:
            return
            
        for text in suggestions:
            add_task(
                self.state,
                text=text,
                section="Someday",
                project_id=self._project_id
            )
        self._save_callback()
        self.refresh()
        
        # Feedback
        if self.window():
            self.window().show_toast(f"Added {len(suggestions)} suggested tasks.")

class SearchWidget(QWidget):
    """
    Global search page to find tasks across all sections.
    """
    def __init__(self, state: Dict[str, Any], save_callback, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state = state
        self._save_callback = save_callback
        self._build_ui()
        
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._execute_search)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QLabel("Search")
        header.setObjectName("PageHeader")
        layout.addWidget(header)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tasks...")
        self.search_input.setStyleSheet(f"background-color: rgba(0,0,0,0.3); color: {TEXT_WHITE}; border: 1px solid {HOVER_BG}; border-radius: 6px; padding: 8px;")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._perform_search)
        layout.addWidget(self.search_input)

        self.results_list = QListWidget()
        self.results_list.setStyleSheet(f"QListWidget {{ background: transparent; border: none; }} QListWidget::item:selected {{ background-color: {HOVER_BG}; border-radius: 8px; }}")
        layout.addWidget(self.results_list, 1)
        
        self.lbl_no_results = QLabel("No matching tasks found.")
        self.lbl_no_results.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_no_results.setStyleSheet(f"color: {TEXT_GRAY}; font-style: italic; margin-top: 20px;")
        self.lbl_no_results.hide()
        layout.addWidget(self.lbl_no_results)

    def _perform_search(self, text: str):
        self._search_timer.start()

    def _execute_search(self):
        self.results_list.clear()
        self.lbl_no_results.hide()
        self.results_list.show()
        
        text = self.search_input.text().strip().lower()
        if not text: return

        tasks = self.state.get("tasks", [])
        matches = [t for t in tasks if text in t.get("text", "").lower()]
        
        if not matches:
            self.results_list.hide()
            self.lbl_no_results.show()
            return
        
        for t in matches:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, t.get("id"))
            
            row = TaskRowWidget(
                task=t, show_delete_button=False, show_focus_button=False
            )
            row.toggled.connect(self._toggle_task)
            
            self.results_list.addItem(item)
            item.setSizeHint(row.sizeHint())
            self.results_list.setItemWidget(item, row)

    def _toggle_task(self, task_id):
        toggle_task_completed(self.state, task_id)
        self._save_callback()
        self._perform_search(self.search_input.text()) # Refresh results


class JournalWidget(QWidget):
    """
    Rich text daily journal with formatting and a cleaner UI.
    """
    def __init__(self, state: Dict[str, Any], save_callback, ai_engine=None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state = state
        self._save_callback = save_callback
        self.ai_engine = ai_engine
        self._current_date = today_str()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Left: Date List
        left_panel = QFrame()
        left_panel.setObjectName("GlassCard")
        left_panel.setFixedWidth(200)
        left_panel.setStyleSheet(f"#GlassCard {{ background-color: rgba(0,0,0,0.2); border-right: 1px solid {GLASS_BORDER}; border-radius: 0px; }}")
        l_left = QVBoxLayout(left_panel)
        l_left.setContentsMargins(0, 10, 0, 10)
        
        lbl_entries = QLabel("  ENTRIES")
        lbl_entries.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        l_left.addWidget(lbl_entries)
        
        self.date_list = QListWidget()
        self.date_list.setStyleSheet(f"""
            QListWidget {{ background: transparent; border: none; outline: none; }}
            QListWidget::item {{ padding: 8px 12px; color: {TEXT_WHITE}; border-left: 3px solid transparent; }}
            QListWidget::item:selected {{ background-color: {HOVER_BG}; border-left: 3px solid {GOLD}; color: {GOLD}; }}
            QListWidget::item:hover {{ background-color: rgba(255,255,255,0.05); }}
        """)
        self.date_list.itemSelectionChanged.connect(self._on_date_selected)
        l_left.addWidget(self.date_list)
        layout.addWidget(left_panel)

        # Right: Editor
        right_panel = QFrame()
        right_panel.setStyleSheet("background: transparent;")
        l_right = QVBoxLayout(right_panel)
        l_right.setContentsMargins(0, 0, 0, 0)
        l_right.setSpacing(10)
        
        self.lbl_date_header = QLabel("")
        self.lbl_date_header.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 22px; font-weight: bold; margin-bottom: 5px;")
        l_right.addWidget(self.lbl_date_header)

        # --- Toolbar ---
        toolbar = QFrame()
        toolbar.setStyleSheet(f"background-color: {HOVER_BG}; border-radius: 8px; padding: 4px;")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(4, 4, 4, 4)
        tb_layout.setSpacing(6)

        def create_fmt_btn(text, tooltip, callback):
            btn = QPushButton(text)
            btn.setFixedSize(32, 32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {TEXT_WHITE}; font-weight: bold; border-radius: 4px; }} QPushButton:hover {{ background: rgba(255,255,255,0.1); }}")
            btn.clicked.connect(callback)
            return btn

        tb_layout.addWidget(create_fmt_btn("B", "Bold", self._toggle_bold))
        tb_layout.addWidget(create_fmt_btn("I", "Italic", self._toggle_italic))
        tb_layout.addWidget(create_fmt_btn("U", "Underline", self._toggle_underline))
        tb_layout.addWidget(create_fmt_btn("•", "Bullet List", self._toggle_list))
        
        # Font Size
        self.combo_size = QComboBox()
        self.combo_size.addItems(["12", "14", "16", "18", "24"])
        self.combo_size.setCurrentText("14")
        self.combo_size.setFixedWidth(60)
        self.combo_size.setStyleSheet(f"background-color: rgba(0,0,0,0.3); color: {TEXT_WHITE}; border: 1px solid {GLASS_BORDER}; border-radius: 4px;")
        self.combo_size.currentTextChanged.connect(self._change_font_size)
        tb_layout.addWidget(self.combo_size)

        # AI Insight Button
        btn_ai = QPushButton("✨ AI Insight")
        btn_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ai.setToolTip("Get AI feedback on your entry")
        btn_ai.setStyleSheet(f"background-color: {GOLD}; color: {DARK_BG}; border-radius: 4px; padding: 4px 8px; font-weight: bold;")
        btn_ai.clicked.connect(self._on_ai_insight)
        tb_layout.addWidget(btn_ai)

        # Saved Indicator
        self.lbl_saved = QLabel("Saved")
        self.lbl_saved.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 10px; margin-left: 10px;")
        tb_layout.addWidget(self.lbl_saved)

        tb_layout.addStretch()
        l_right.addWidget(toolbar)

        # --- Editor ---
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Write your thoughts here...")
        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.setStyleSheet(f"QTextEdit {{ background-color: rgba(0,0,0,0.2); color: {TEXT_WHITE}; border: 1px solid {GLASS_BORDER}; border-radius: 12px; padding: 16px; font-size: 14px; selection-background-color: {GOLD}; selection-color: {DARK_BG}; }}")
        l_right.addWidget(self.editor)
        
        layout.addWidget(right_panel, 1)

    def refresh(self) -> None:
        self.date_list.blockSignals(True)
        self.date_list.clear()
        
        # Always ensure Today is present or at top
        dates = {e["date"] for e in self.state.get("journal", [])}
        dates.add(today_str())
        sorted_dates = sorted(list(dates), reverse=True)

        for d in sorted_dates:
            item = QListWidgetItem(d if d != today_str() else "Today")
            item.setData(Qt.ItemDataRole.UserRole, d)
            self.date_list.addItem(item)
            if d == self._current_date:
                self.date_list.setCurrentItem(item)
        
        self.date_list.blockSignals(False)
        
        # Only reload editor if we are not currently typing in it
        if not self.editor.hasFocus():
            self._load_entry(self._current_date)

    def _on_date_selected(self) -> None:
        item = self.date_list.currentItem()
        if item:
            self._current_date = item.data(Qt.ItemDataRole.UserRole)
            self._load_entry(self._current_date)

    def _load_entry(self, date_str: str) -> None:
        self.lbl_date_header.setText(
            date_str if date_str != today_str() else f"Today ({date_str})"
        )

        effect = QGraphicsOpacityEffect(self.editor)
        self.editor.setGraphicsEffect(effect)
        anim_out = QPropertyAnimation(effect, b"opacity")
        anim_out.setDuration(ANIM_DURATION_FAST)
        anim_out.setStartValue(1.0)
        anim_out.setEndValue(0.0)
        anim_out.setEasingCurve(QEasingCurve.Type.InCubic)

        def on_fade_out_finished():
            entry = get_journal_entry(self.state, date_str)
            self.editor.blockSignals(True)
            content = entry.get("text", "") if entry else ""
            
            # Smart load: HTML vs Plain Text
            if "<!DOCTYPE HTML" in content or "<html>" in content:
                self.editor.setHtml(content)
            else:
                self.editor.setPlainText(content)
            self.editor.blockSignals(False)
            anim_in = QPropertyAnimation(effect, b"opacity")
            anim_in.setDuration(ANIM_DURATION_MEDIUM)
            anim_in.setStartValue(0.0)
            anim_in.setEndValue(1.0)
            anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim_in.finished.connect(lambda: self.editor.setGraphicsEffect(None))
            anim_in.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

        anim_out.finished.connect(on_fade_out_finished)
        anim_out.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _on_text_changed(self) -> None:
        # Save as HTML to preserve formatting
        html_content = self.editor.toHtml()
        set_journal_entry(self.state, self._current_date, html_content)
        
        # Visual feedback
        self.lbl_saved.setText("Saving...")
        QTimer.singleShot(800, lambda: self.lbl_saved.setText("Saved"))
        
        self._save_callback()

    # --- Formatting Handlers ---
    def _toggle_bold(self):
        fmt = self.editor.currentCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold if fmt.fontWeight() != QFont.Weight.Bold else QFont.Weight.Normal)
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()

    def _toggle_italic(self):
        fmt = self.editor.currentCharFormat()
        fmt.setFontItalic(not fmt.fontItalic())
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()

    def _toggle_underline(self):
        fmt = self.editor.currentCharFormat()
        fmt.setFontUnderline(not fmt.fontUnderline())
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()

    def _toggle_list(self):
        self.editor.textCursor().createList(QTextListFormat.Style.ListDisc)
        self.editor.setFocus()

    def _change_font_size(self, text):
        size = float(text)
        fmt = self.editor.currentCharFormat()
        fmt.setFontPointSize(size)
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()

    def _on_ai_insight(self):
        text = self.editor.toPlainText().strip()
        if not text:
            return
        
        if self.ai_engine:
            insight = self.ai_engine.analyze_journal_sentiment(text)
            QMessageBox.information(self, "AI Insight", insight)
        else:
            QMessageBox.information(self, "AI Insight", "AI Engine not available.")

# ============================================================================
# SECTION 6: HUB WINDOW - LAYOUT, NAVIGATION & PAGES
# ============================================================================


class HubWindow(QMainWindow):
    data_changed = pyqtSignal()
    """Main TaskFlow Hub window: planning + mental health workspace."""

    def __init__(self, state: Dict[str, Any], paths: Dict[str, str], ai_engine=None):
        super().__init__()
        self.state = state
        self.paths = paths
        self.ai_engine = ai_engine

        # Voice AI components
        self.voice_listener = None
        self.command_parser = None
        self._voice_worker = None

        self._zen_task_id = None
        self._pomodoro_mode = False
        self._pomodoro_count = 0
        self._zen_session_type = "focus"
        self._consecutive_focus_sessions = 0
        self._panic_breathing_timer = None
        self._panic_phase_counter = 0
        # Prevent app from exiting when window is closed (if tray is enabled)
        QApplication.setQuitOnLastWindowClosed(False)

        # Confetti Overlay
        self.confetti = ConfettiOverlay(self)
        self.confetti.resize(self.size())
        self.toast = ToastOverlay(self)
        self.toast.resize(self.size())

        # Geometry
        geom = self.state.get("uiGeometry")
        if geom and isinstance(geom, list) and len(geom) == 4:
            x, y, w, h = geom
            self.setGeometry(x, y, w, h)

        self.setWindowTitle(f"{APP_NAME} Hub v{APP_VERSION}")
        self.setWindowIcon(QIcon("icon.ico"))

        # Debounced save timer
        self._save_timer = QTimer(self)
        self._save_timer.setInterval(SAVE_DEBOUNCE_MS)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._do_save)

        # Focus session tracking (in-memory)
        self._session_completed_today = 0
        
        # Confetti cooldown (15 seconds)
        self._last_confetti_time = 0

        self._build_ui()
        self._refresh_home()

        # Apply shadows to all glass cards
        for widget in self.findChildren(QFrame, "GlassCard"):
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(0, 0, 0, 80))
            shadow.setOffset(0, 4)
            widget.setGraphicsEffect(shadow)

        # Setup System Tray
        self._setup_tray()

        # Setup Audio
        self._init_audio()
        
        # Listen for data changes to refresh UI (e.g. from Widget)
        self.data_changed.connect(self._on_data_changed)
        
        # Apply startup settings
        settings = self.state.get("settings", {})
        if settings.get("startInFocusMode", False):
            self._toggle_focus_mode()
            
        # Initialize Voice AI in background
        if VOICE_AVAILABLE and self.state.get("settings", {}).get("voiceEnabled", True):
            threading.Thread(target=self._init_voice_ai, daemon=True).start()

    def resizeEvent(self, event):
        if hasattr(self, "confetti"):
            self.confetti.resize(self.size())
        if hasattr(self, "toast"):
            # Toast resizes itself on show, but we ensure it stays centered if needed
            pass
        super().resizeEvent(event)

    def start_post_load_tasks(self) -> None:
        """Starts background checks and dialogs after the window is fully visible."""
        self._check_updates_async()
        QTimer.singleShot(500, self._run_start_of_day_flow)
        # Show a helpful tip after a short delay
        QTimer.singleShot(3000, self._show_tip_of_the_day)

    def _init_voice_ai(self):
        """Loads the Whisper model in the background."""
        try:
            self.voice_listener = VoiceListener(model_size="tiny")
            self.command_parser = CommandParser()
        except Exception as e:
            print(f"Failed to initialize Voice AI: {e}")

    def _setup_shortcuts(self) -> None:
        """Initialize keyboard shortcuts (called once during startup)."""
        QShortcut(QKeySequence("Ctrl+1"), self, activated=lambda: self._switch_page(self.page_home))
        QShortcut(QKeySequence("Ctrl+2"), self, activated=lambda: self._switch_page(self.page_today))
        QShortcut(QKeySequence("Ctrl+3"), self, activated=lambda: self._switch_page(self.page_week))
        QShortcut(QKeySequence("Ctrl+4"), self, activated=lambda: self._switch_page(self.page_someday))
        QShortcut(QKeySequence("Ctrl+5"), self, activated=lambda: self._switch_page(self.page_projects))
        QShortcut(QKeySequence("Ctrl+6"), self, activated=lambda: self._switch_page(self.page_stats))
        QShortcut(QKeySequence("Ctrl+T"), self, activated=lambda: self._switch_page(self.page_today))
        QShortcut(QKeySequence("Ctrl+P"), self, activated=lambda: self._switch_page(self.page_projects))
        QShortcut(QKeySequence("Ctrl+B"), self, activated=self._toggle_focus_mode)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: self._switch_page(self.page_search))
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._focus_quick_add)

    def celebrate(self) -> None:
        """Trigger confetti with a 10-second cooldown to prevent spamming."""
        current_time = time.time()
        if current_time - self._last_confetti_time >= 10:
            self.confetti.burst()
            self._last_confetti_time = current_time

    def _setup_tray(self):
        """Initialize the system tray icon."""
        self.tray_icon = QSystemTrayIcon(self)
        
        # Robust icon loading
        icon_path = "icon.ico"
        if not os.path.exists(icon_path):
             # Try relative to script location
             script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
             icon_path = os.path.join(script_dir, "icon.ico")
             
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # Fallback icon to prevent warning
            self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        
        tray_menu = QMenu()
        
        act_show = tray_menu.addAction("Show TaskFlow")
        act_show.triggered.connect(self.showNormal)
        act_show.triggered.connect(self.activateWindow)
        
        act_quick = tray_menu.addAction("Quick Add Task")
        act_quick.triggered.connect(self._tray_quick_add)
        
        tray_menu.addSeparator()
        
        act_quit = tray_menu.addAction("Quit")
        act_quit.triggered.connect(self._force_quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _tray_quick_add(self):
        """Open the window and focus the Today input field."""
        self.showNormal()
        self.activateWindow()
        self._switch_page(self.page_today)
        self.page_today.quick_add_input.setFocus()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()

    def _init_audio(self):
        self.media_player = None
        if QMediaPlayer and QAudioOutput:
            self.media_player = QMediaPlayer()
            self.audio_output = QAudioOutput()
            self.media_player.setAudioOutput(self.audio_output)
            
            # Load saved volume
            saved_volume = self.state.get("settings", {}).get("zenVolume", 0.5)
            self.audio_output.setVolume(saved_volume)
            
            if hasattr(self, "slider_volume"):
                self.slider_volume.setValue(int(saved_volume * 100))

    def _prevent_sleep(self):
        """Prevent the system from sleeping during a Zen session."""
        if os.name == 'nt' and ctypes:
            try:
                # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
            except Exception:
                pass

    def _allow_sleep(self):
        """Allow the system to sleep again."""
        if os.name == 'nt' and ctypes:
            try:
                # ES_CONTINUOUS
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            except Exception:
                pass

    # ────────────────────────────────────────────────────────────────────
    # UI construction
    # ────────────────────────────────────────────────────────────────────

    def _create_nav_group(self, nav_layout: QVBoxLayout, title: str, buttons: List[QPushButton]) -> None:
        """Helper to create a titled group of navigation buttons."""
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 11px; font-weight: bold; margin-top: 16px; margin-bottom: 4px; letter-spacing: 1px;")
        nav_layout.addWidget(lbl)
        for btn in buttons:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.setMinimumHeight(34)
            nav_layout.addWidget(btn)

    def _build_ui(self) -> None:
        self.setStyleSheet(
            f"""
            QMainWindow {{
                background-color: {DARK_BG};
            }}
            QLabel#TitleLabel {{
                color: {GOLD};
                font-size: 20px;
                font-weight: bold;
            }}
            QLabel#PageHeader {{
                font-size: 20px;
                font-weight: bold;
                color: {GOLD};
                background: transparent;
            }}
            QFrame#GlassCard {{
                background-color: {GLASS_BG};
                border: 1px solid {GLASS_BORDER};
                border-radius: 16px;
            }}
            QFrame#NavBar {{
                background-color: rgba(16, 16, 18, 220);
                border-right: 1px solid {GLASS_BORDER};
            }}
            /* Sidebar Buttons */
            QFrame#NavBar QPushButton {{
                text-align: left;
                padding-left: 16px;
                border: none;
                background-color: transparent;
                border-radius: 6px;
                font-weight: 600;
            }}
            QFrame#NavBar QPushButton:hover {{
                background-color: {HOVER_BG};
            }}
            QFrame#NavBar QPushButton:checked {{
                background-color: {HOVER_BG};
                color: {GOLD};
                border-left: 3px solid {GOLD};
                border-top-left-radius: 0;
                border-bottom-left-radius: 0;
            }}
            QLabel {{
                color: {TEXT_WHITE};
            }}
            QTextEdit, QComboBox {{
                background-color: rgba(0, 0, 0, 0.3);
                color: {TEXT_WHITE};
                border-radius: 8px;
                border: 1px solid {HOVER_BG};
            }}
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.05);
                color: {TEXT_WHITE};
                border-radius: 8px;
                border: 1px solid {HOVER_BG};
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.15);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.25);
            }}
            QListWidget {{
                background-color: transparent;
                color: {TEXT_WHITE};
                border: none;
            }}
            /* Custom Scrollbars */
            QScrollBar:vertical {{
                border: none;
                background: {DARK_BG};
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {HOVER_BG};
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            """
        )

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # Left navigation
        self.nav_frame = QFrame()
        self.nav_frame.setObjectName("NavBar")
        self.nav_frame.setFixedWidth(180)
        nav_layout = QVBoxLayout(self.nav_frame)
        nav_layout.setContentsMargins(10, 20, 10, 20)
        nav_layout.setSpacing(12)

        title = QLabel(f"{APP_NAME} Hub")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(title)
        nav_layout.addSpacing(6)

        # --- Navigation Groups ---
        self.btn_home = QPushButton("🏠 Home")
        self.btn_stats = QPushButton("📊 Stats")
        self.btn_profile = QPushButton("🤖 AI Coach")
        self._create_nav_group(nav_layout, "DASHBOARD", [self.btn_home, self.btn_stats, self.btn_profile])

        self.btn_today = QPushButton("☀️ Today")
        self.btn_scheduled = QPushButton("📅 Scheduled")
        self.btn_week = QPushButton("🗓️ This Week")
        self.btn_someday = QPushButton("💡 Someday")
        self._create_nav_group(nav_layout, "TASKS", [self.btn_today, self.btn_scheduled, self.btn_week, self.btn_someday])

        self.btn_projects = QPushButton("📂 Projects")
        self.btn_journal = QPushButton("📓 Journal")
        self._create_nav_group(nav_layout, "ORGANIZE", [self.btn_projects, self.btn_journal])

        self.btn_search = QPushButton("🔍 Search")
        self.btn_focus = QPushButton("🧘 Focus Mode")
        self.btn_panic = QPushButton("🆘 Panic Relief")
        self._create_nav_group(nav_layout, "TOOLS", [self.btn_search, self.btn_focus, self.btn_panic])

        nav_layout.addStretch(1)

        # Bottom Actions - Separator between Focus Mode and Settings
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet(f"background-color: {GLASS_BORDER}; margin-top: 8px; margin-bottom: 8px;")
        sep.setFixedHeight(1)
        nav_layout.addWidget(sep)

        self.btn_tips = QPushButton("💡 Tips")
        self.btn_settings = QPushButton("⚙️ Settings")
        self.btn_feedback = QPushButton("💬 Feedback")
        self.btn_check_updates = QPushButton("🔄 Check updates")
        self.btn_quit = QPushButton("🚪 Exit Hub")

        # Add Settings, Feedback, Tips
        for btn in (self.btn_settings, self.btn_feedback, self.btn_tips):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            nav_layout.addWidget(btn)

        # Separator after Tips
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        sep2.setStyleSheet(f"background-color: {GLASS_BORDER}; margin-top: 8px; margin-bottom: 8px;")
        sep2.setFixedHeight(1)
        nav_layout.addWidget(sep2)

        # Add Check updates and Exit Hub
        for btn in (self.btn_check_updates, self.btn_quit):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            nav_layout.addWidget(btn)

        root.addWidget(self.nav_frame)

        # Right pages
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        # Build pages
        self._build_home_page()
        self._build_task_pages()
        self._build_projects_page()
        self._build_stats_page()
        self._build_scheduled_page()
        self._build_settings_page()
        self._build_panic_page()
        self._build_zen_page()
        self.page_search = SearchWidget(self.state, self.schedule_save)
        self.page_profile = CoachWidget(self.ai_engine)
        self.page_profile.message_requested.connect(self.show_toast)

        # Add pages to stack
        self.stack.addWidget(self.page_home)
        self.stack.addWidget(self.page_today)
        self.stack.addWidget(self.page_week)
        self.stack.addWidget(self.page_scheduled)
        self.stack.addWidget(self.page_someday)
        self.stack.addWidget(self.page_projects)
        self.stack.addWidget(self.page_journal)
        self.stack.addWidget(self.page_stats)
        self.stack.addWidget(self.page_settings)
        self.stack.addWidget(self.page_panic)
        self.stack.addWidget(self.page_profile)
        self.stack.addWidget(self.page_zen)
        self.stack.addWidget(self.page_search)

        # Map pages to buttons for active state management
        self.nav_map = {
            self.page_home: self.btn_home,
            self.page_today: self.btn_today,
            self.page_week: self.btn_week,
            self.page_scheduled: self.btn_scheduled,
            self.page_someday: self.btn_someday,
            self.page_projects: self.btn_projects,
            self.page_journal: self.btn_journal,
            self.page_stats: self.btn_stats,
            self.page_settings: self.btn_settings,
            self.page_panic: self.btn_panic,
            self.page_profile: self.btn_profile,
            self.page_search: self.btn_search,
        }

        # Connect nav
        self.btn_home.clicked.connect(lambda: self._switch_page(self.page_home))
        self.btn_today.clicked.connect(lambda: self._switch_page(self.page_today))
        self.btn_week.clicked.connect(lambda: self._switch_page(self.page_week))
        self.btn_scheduled.clicked.connect(lambda: self._switch_page(self.page_scheduled))
        self.btn_someday.clicked.connect(lambda: self._switch_page(self.page_someday))
        self.btn_projects.clicked.connect(lambda: self._switch_page(self.page_projects))
        self.btn_journal.clicked.connect(lambda: self._switch_page(self.page_journal))
        self.btn_stats.clicked.connect(lambda: self._switch_page(self.page_stats))
        self.btn_profile.clicked.connect(lambda: self._switch_page(self.page_profile))
        self.btn_settings.clicked.connect(lambda: self._switch_page(self.page_settings))
        self.btn_feedback.clicked.connect(self._open_feedback_dialog)
        self.btn_tips.clicked.connect(self._open_tips_dialog)
        self.btn_search.clicked.connect(lambda: self._switch_page(self.page_search))
        self.btn_panic.clicked.connect(self.enter_panic_mode)
        self.btn_quit.clicked.connect(self.close)
        self.btn_check_updates.clicked.connect(lambda: self._check_updates_async(manual=True))
        self.btn_focus.clicked.connect(self._toggle_focus_mode)
        
        # Set Home as the default/initial page
        self._switch_page(self.page_home)
        self.btn_home.setChecked(True)
        
        # Initialize keyboard shortcuts
        self._setup_shortcuts()

    def show_toast(self, message: str):
        """Displays a non-intrusive toast notification."""
        self.toast.show_message(message)

    def _focus_quick_add(self):
        """Shortcut handler to focus the primary input of the current page."""
        current = self.stack.currentWidget()
        if isinstance(current, TaskListWidget):
            current.quick_add_input.setFocus()
        elif current is self.page_home:
            self.idea_input.setFocus()
        elif current is self.page_projects:
            self.project_task_widget.quick_add_input.setFocus()
        elif current is self.page_scheduled:
            if self.sched_stack.currentWidget() == self.view_list:
                self.scheduled_list_widget.quick_add_input.setFocus()
            else:
                self.cal_quick_add.setFocus()
        elif current is self.page_search:
            self.page_search.search_input.setFocus()

    # ────────────────────────────────────────────────────────────────────
    # Page builders
    # ────────────────────────────────────────────────────────────────────
    
    def _build_home_header(self, layout: QVBoxLayout) -> None:
        """Builds the header section of the home page."""
        top_row = QHBoxLayout()
        
        # Left: Greeting + XP Bar
        left_col = QVBoxLayout()
        self.lbl_greeting = QLabel("Hello.")
        self.lbl_greeting.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 26px; font-weight: bold;")
        left_col.addWidget(self.lbl_greeting)
        
        # XP Bar Container
        xp_container = QHBoxLayout()
        self.lbl_level = QLabel("Lvl 1")
        self.lbl_level.setStyleSheet(f"color: {GOLD}; font-weight: bold; font-size: 12px;")
        xp_container.addWidget(self.lbl_level)
        
        self.xp_bar = QProgressBar()
        self.xp_bar.setFixedHeight(6)
        self.xp_bar.setFixedWidth(120)
        self.xp_bar.setTextVisible(False)
        self.xp_bar.setStyleSheet(f"QProgressBar {{ background-color: {HOVER_BG}; border-radius: 3px; border: none; }} QProgressBar::chunk {{ background-color: {GOLD}; border-radius: 3px; }}")
        xp_container.addWidget(self.xp_bar)
        
        left_col.addLayout(xp_container)
        top_row.addLayout(left_col)
        
        top_row.addStretch()
        
        # Right: Streak, Plan, Date
        right_col = QVBoxLayout()
        right_col.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        stats_row = QHBoxLayout()
        self.lbl_streak = QLabel("🔥 0")
        self.lbl_streak.setStyleSheet(f"color: {GOLD}; font-size: 16px; font-weight: bold; margin-right: 10px;")
        stats_row.addWidget(self.lbl_streak)

        btn_plan = QPushButton("Plan")
        btn_plan.setToolTip("Run Daily Planning")
        btn_plan.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_plan.setStyleSheet(f"background-color: {HOVER_BG}; color: {TEXT_WHITE}; border-radius: 6px; padding: 4px 12px; border: 1px solid {GLASS_BORDER}; font-size: 12px;")
        btn_plan.clicked.connect(lambda: self._run_daily_planning(force=True))
        stats_row.addWidget(btn_plan)
        
        right_col.addLayout(stats_row)
        
        lbl_date = QLabel(datetime.now().strftime("%A, %B %d"))
        lbl_date.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 14px; margin-top: 4px;")
        lbl_date.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(lbl_date)
        
        top_row.addLayout(right_col)
        
        layout.addLayout(top_row)

    def _build_home_focus_card(self) -> QFrame:
        """Builds the 'Today's Focus' card for the home page."""
        card = QFrame()
        card.setObjectName("GlassCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        
        layout.addWidget(QLabel("🎯 Today's Focus"))
        
        self.btn_primary_goal = QPushButton("No main goal set.")
        self.btn_primary_goal.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_primary_goal.setStyleSheet(f"color: {GOLD}; font-size: 18px; font-weight: bold; margin-top: 5px; text-align: left; background: transparent; border: none;")
        self.btn_primary_goal.clicked.connect(self._edit_primary_goal)
        layout.addWidget(self.btn_primary_goal)
        
        self.today_summary_line = QLabel("Loading...")
        self.today_summary_line.setStyleSheet(f"color: {TEXT_GRAY}; margin-top: 5px;")
        layout.addWidget(self.today_summary_line)
        
        layout.addSpacing(15)
        layout.addWidget(QLabel("Up Next:"))
        self.btn_up_next = QPushButton("No tasks.")
        self.btn_up_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_up_next.setStyleSheet(f"text-align: left; color: {TEXT_WHITE}; background: transparent; border: none;")
        layout.addWidget(self.btn_up_next)
        
        layout.addStretch()
        
        btn_open_today = QPushButton("Open Today View →")
        btn_open_today.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_today.setStyleSheet(f"background-color: {HOVER_BG}; color: {TEXT_WHITE}; border-radius: 8px; padding: 8px; border: 1px solid {GLASS_BORDER};")
        btn_open_today.clicked.connect(lambda: self._switch_page(self.page_today))
        layout.addWidget(btn_open_today)
        return card

    def _build_home_page(self) -> None:
        self.page_home = QWidget()
        layout = QVBoxLayout(self.page_home)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        self._build_home_header(layout)

        # 2. Main Dashboard Grid
        grid = QGridLayout()
        grid.setSpacing(20)
        
        # --- Card 1: Focus (Top Left) ---
        self.card_focus = self._build_home_focus_card()
        grid.addWidget(self.card_focus, 0, 0)
        
        # --- Card 2: Insights & Wellness (Top Right) ---
        self.card_insights = QFrame()
        self.card_insights.setObjectName("GlassCard")
        l_insights = QVBoxLayout(self.card_insights)
        l_insights.setContentsMargins(20, 20, 20, 20)
        
        l_insights.addWidget(QLabel("🧠 AI Insights"))
        
        self.suggestion_label = QLabel("Analyzing...")
        self.suggestion_label.setWordWrap(True)
        self.suggestion_label.setStyleSheet(f"font-style: italic; color: {TEXT_WHITE}; font-size: 14px;")
        l_insights.addWidget(self.suggestion_label)
        
        l_insights.addSpacing(15)
        
        self.snapshot_summary = QLabel("Mood & Habits")
        self.snapshot_summary.setStyleSheet(f"color: {GOLD}; font-weight: bold;")
        l_insights.addWidget(self.snapshot_summary)
        
        # Habits Container
        self.habits_container = QWidget()
        self.habits_layout = QHBoxLayout(self.habits_container)
        self.habits_layout.setContentsMargins(0, 0, 0, 0)
        self.habits_layout.setSpacing(8)
        self.habits_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        l_insights.addWidget(self.habits_container)

        self.snapshot_hint = QLabel("")
        self.snapshot_hint.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 11px;")
        l_insights.addWidget(self.snapshot_hint)
        
        l_insights.addStretch()
        
        # --- Card 3: Quick Capture (Bottom) ---
        self.card_capture = QFrame()
        self.card_capture.setObjectName("GlassCard")
        l_capture = QVBoxLayout(self.card_capture)
        l_capture.setContentsMargins(20, 20, 20, 20)
        
        l_capture.addWidget(QLabel("💡 Quick Capture"))
        
        cap_row = QHBoxLayout()
        self.idea_input = QLineEdit()
        self.idea_input.setPlaceholderText("Type an idea or task...")
        self.idea_input.setClearButtonEnabled(True)
        self.idea_input.returnPressed.connect(self._on_add_idea)
        cap_row.addWidget(self.idea_input, 1)
        
        btn_brain_dump = QPushButton("🧠 Brain Dump")
        btn_brain_dump.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_brain_dump.setStyleSheet(f"background-color: {HOVER_BG}; color: {TEXT_WHITE}; border-radius: 8px; padding: 8px; border: 1px solid {GLASS_BORDER};")
        btn_brain_dump.clicked.connect(self._on_brain_dump)
        cap_row.addWidget(btn_brain_dump)
        
        # Voice Input Button
        self.btn_voice = QPushButton("🎙️")
        self.btn_voice.setFixedSize(40, 32)
        self.btn_voice.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_voice.setStyleSheet(f"background-color: {HOVER_BG}; color: {TEXT_WHITE}; border-radius: 8px; border: 1px solid {GLASS_BORDER}; font-size: 16px;")
        self.btn_voice.clicked.connect(self._on_voice_input)
        cap_row.addWidget(self.btn_voice)
        
        l_capture.addLayout(cap_row)
        
        # Recent ideas list (small)
        self.ideas_list = QListWidget()
        self.ideas_list.setFixedHeight(60)
        self.ideas_list.setStyleSheet("QListWidget { background: transparent; border: none; }")
        self.ideas_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ideas_list.customContextMenuRequested.connect(self._on_idea_menu)
        l_capture.addWidget(self.ideas_list)
        
        grid.addWidget(self.card_insights, 0, 1)
        grid.addWidget(self.card_capture, 1, 0, 1, 2) # Span 2 columns
        
        # Column weights
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        
        layout.addLayout(grid)
        
        # Quote at bottom
        self.quote_label = QLabel("")
        self.quote_label.setWordWrap(True)
        self.quote_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.quote_label.setStyleSheet(f"color: {TEXT_GRAY}; font-style: italic; margin-top: 10px;")
        layout.addWidget(self.quote_label)

    def _edit_primary_goal(self):
        """Allow user to edit the main goal directly from the dashboard."""
        stats = self.state.setdefault("stats", {})
        daily_logs = stats.setdefault("dailyLogs", {})
        today = today_str()
        current_goal = daily_logs.get(today, {}).get("primaryGoal", "")
        
        text, ok = QInputDialog.getText(self, "Today's Focus", "What is your main goal?", text=current_goal)
        if ok:
            if today not in daily_logs: daily_logs[today] = {}
            daily_logs[today]["primaryGoal"] = text.strip()
            self.schedule_save()
            self._refresh_home()

    def _build_task_pages(self) -> None:
        self.page_today = TaskListWidget(self.state, "Today", self.schedule_save)
        self.page_week = TaskListWidget(self.state, "This Week", self.schedule_save)
        self.page_someday = TaskListWidget(self.state, "Someday", self.schedule_save)
        self.page_journal = JournalWidget(self.state, self.schedule_save, self.ai_engine)
        
        # Connect Focus Signals
        for page in (self.page_today, self.page_week, self.page_someday):
            page.requestFocus.connect(self.enter_zen_mode)

    def _build_scheduled_page(self) -> None:
        self.page_scheduled = QWidget()
        main_layout = QVBoxLayout(self.page_scheduled)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Header with Toggle
        header = QHBoxLayout()
        self.btn_sched_toggle = QPushButton("Show List View")
        self.btn_sched_toggle.setCheckable(True)
        self.btn_sched_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sched_toggle.setStyleSheet(f"background-color: {HOVER_BG}; color: {TEXT_WHITE}; border-radius: 6px; padding: 6px 12px; border: 1px solid {GLASS_BORDER};")
        self.btn_sched_toggle.toggled.connect(self._toggle_scheduled_view)
        header.addStretch()
        header.addWidget(self.btn_sched_toggle)
        main_layout.addLayout(header)

        self.sched_stack = QStackedWidget()
        main_layout.addWidget(self.sched_stack)

        # --- View 1: Calendar Split View ---
        self.view_calendar = QWidget()
        cal_layout = QHBoxLayout(self.view_calendar)
        cal_layout.setContentsMargins(0, 0, 0, 0)
        
        cal_container = QFrame()
        cal_container.setObjectName("GlassCard")
        cal_frame_layout = QVBoxLayout(cal_container)
        
        self.calendar = TaskCalendarWidget(self.state)
        self.calendar.selectionChanged.connect(self._on_calendar_date_changed)
        self.calendar.taskDropped.connect(self._on_calendar_drop)
        cal_frame_layout.addWidget(self.calendar)
        
        # Legend
        legend = QHBoxLayout()
        for col, label in [(GOLD, "Task"), ("#ff6b6b", "Important"), ("#4ECDC4", "Work")]:
            l = QLabel(f"● {label}")
            l.setStyleSheet(f"color: {col}; font-size: 10px;")
            legend.addWidget(l)
        legend.addStretch()
        cal_frame_layout.addLayout(legend)
        
        cal_layout.addWidget(cal_container, 1)
        
        # Right: Task List for Date
        list_container = QFrame()
        list_container.setObjectName("GlassCard")
        list_container.setFixedWidth(300)
        list_layout = QVBoxLayout(list_container)
        
        self.lbl_cal_date = QLabel("Selected Date")
        self.lbl_cal_date.setObjectName("PageHeader")
        list_layout.addWidget(self.lbl_cal_date)
        
        self.cal_task_list = QListWidget()
        self.cal_task_list.setStyleSheet("background: transparent; border: none;")
        list_layout.addWidget(self.cal_task_list)
        
        # Quick add for this date
        self.cal_quick_add = QLineEdit()
        self.cal_quick_add.setPlaceholderText("Add task to this date...")
        self.cal_quick_add.returnPressed.connect(self._on_cal_quick_add)
        self.cal_quick_add.setStyleSheet(f"background-color: rgba(0,0,0,0.3); border: 1px solid {HOVER_BG}; border-radius: 6px; padding: 6px; color: {TEXT_WHITE};")
        list_layout.addWidget(self.cal_quick_add)
        
        cal_layout.addWidget(list_container)
        self.sched_stack.addWidget(self.view_calendar)

        # --- View 2: Full List View ---
        self.view_list = QWidget()
        list_view_layout = QVBoxLayout(self.view_list)
        list_view_layout.setContentsMargins(0, 0, 0, 0)
        
        # We reuse TaskListWidget but for "Scheduled" section
        self.scheduled_list_widget = TaskListWidget(self.state, "Scheduled", self.schedule_save, self.ai_engine)
        list_view_layout.addWidget(self.scheduled_list_widget)
        
        self.sched_stack.addWidget(self.view_list)
        
        # Initialize
        self._on_calendar_date_changed()

    def _toggle_scheduled_view(self, checked: bool):
        if checked:
            self.btn_sched_toggle.setText("Show Calendar View")
            self.sched_stack.setCurrentWidget(self.view_list)
            self.scheduled_list_widget.refresh()
        else:
            self.btn_sched_toggle.setText("Show List View")
            self.sched_stack.setCurrentWidget(self.view_calendar)
            self._on_calendar_date_changed()

    def _on_calendar_drop(self, task_id, qdate):
        date_str = qdate.toString(Qt.DateFormat.ISODate)
        self._set_task_schedule(task_id, date_str)

    def _on_calendar_date_changed(self):
        date = self.calendar.selectedDate()
        date_str = date.toString(Qt.DateFormat.ISODate)
        self.lbl_cal_date.setText(date.toString("dddd, MMMM d"))
        
        self.cal_task_list.clear()
        tasks = [t for t in self.state.get("tasks", []) if (t.get("schedule") or {}).get("date") == date_str]
        tasks.sort(key=lambda t: (t.get("completed", False), t.get("order", 0)))
        
        for t in tasks:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, t.get("id"))
            row = TaskRowWidget(t)
            row.toggled.connect(self._on_toggle_task_calendar)
            row.deleted.connect(self._on_delete_task_calendar)
            row.contextMenuRequested.connect(
                lambda pos, tid, r=row: self._show_calendar_task_menu(tid, r.mapToGlobal(pos))
            )
            row.focusRequested.connect(self.enter_zen_mode)

            item.setSizeHint(row.sizeHint())
            self.cal_task_list.addItem(item)
            self.cal_task_list.setItemWidget(item, row)

    def _show_calendar_task_menu(self, task_id, global_pos):
        menu = QMenu(self)
        act_del = menu.addAction("Delete")
        if menu.exec(global_pos) == act_del:
            self._on_delete_task_calendar(task_id)

    def _on_toggle_task_calendar(self, task_id):
        toggle_task_completed(self.state, task_id)
        self.schedule_save()
        self._on_calendar_date_changed()
        self.calendar.update()

    def _on_delete_task_calendar(self, task_id):
        delete_task(self.state, task_id)
        self.schedule_save()
        self._on_calendar_date_changed()
        self.calendar.update()

    def _on_cal_quick_add(self):
        text = self.cal_quick_add.text().strip()
        if not text: return
        
        date_str = self.calendar.selectedDate().toString(Qt.DateFormat.ISODate)
        
        # Use shared parser for smart entry
        meta = parse_task_input(text)
        category = meta.get("category")
        important = meta.get("important", False)
        
        add_task(
            self.state,
            text=meta["text"],
            section="Scheduled",
            category=category,
            important=important,
            schedule={"date": date_str}
        )
        
        if date_str == today_str():
            self.state["tasks"][-1]["section"] = "Today"
            
        self.schedule_save()
        self.cal_quick_add.clear()
        self._on_calendar_date_changed()
        self.calendar.update()

    def _build_projects_page(self) -> None:
        self.page_projects = QWidget()
        layout = QVBoxLayout(self.page_projects)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        content = QHBoxLayout()
        layout.addLayout(content, 1)

        # Left card: list of projects
        card_plist = QFrame()
        card_plist.setObjectName("GlassCard")
        card_plist.setFixedWidth(280)
        l_plist = QVBoxLayout(card_plist)
        l_plist.setContentsMargins(12, 12, 12, 12)
        l_plist.setSpacing(8)

        plist_header = QLabel("Projects")
        plist_header.setObjectName("PageHeader")
        l_plist.addWidget(plist_header)

        self.project_list = QListWidget()
        self.project_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.project_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.project_list.customContextMenuRequested.connect(self._on_project_menu)
        l_plist.addWidget(self.project_list, 1)

        self.empty_projects_label = QLabel(
            "You can create your first project with the 'New project' button."
        )
        self.empty_projects_label.setWordWrap(True)
        self.empty_projects_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_projects_label.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 12px;")
        self.empty_projects_label.setVisible(False)
        l_plist.addWidget(self.empty_projects_label)

        btns_proj = QHBoxLayout()
        self.btn_add_project = QPushButton("New project")
        self.btn_rename_project = QPushButton("Rename")
        self.btn_delete_project = QPushButton("Delete")
        btns_proj.addWidget(self.btn_add_project)
        btns_proj.addWidget(self.btn_rename_project)
        btns_proj.addWidget(self.btn_delete_project)
        l_plist.addLayout(btns_proj)

        content.addWidget(card_plist)

        # Right card: project tasks
        self.project_detail = QFrame()
        self.project_detail.setObjectName("GlassCard")
        project_detail_layout = QVBoxLayout(self.project_detail)
        project_detail_layout.setContentsMargins(16, 16, 16, 16)
        project_detail_layout.setSpacing(8)

        self.project_detail_title = QLabel("Select a project")
        self.project_detail_title.setObjectName("PageHeader")
        project_detail_layout.addWidget(self.project_detail_title)

        self.project_task_widget = ProjectTaskListWidget(self.state, self.schedule_save, self.ai_engine)
        project_detail_layout.addWidget(self.project_task_widget)

        content.addWidget(self.project_detail, 1)

        # Connect
        self.btn_add_project.clicked.connect(self._on_add_project)
        self.btn_rename_project.clicked.connect(self._on_rename_project)
        self.btn_delete_project.clicked.connect(self._on_delete_project)
        self.project_list.itemSelectionChanged.connect(self._on_project_selected)

    def _build_stats_page(self) -> None:
        self.page_stats = QWidget()
        layout = QVBoxLayout(self.page_stats)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Top Row: Score + Summary
        top_row = QHBoxLayout()
        
        # Score Card
        card_score = QFrame()
        card_score.setObjectName("GlassCard")
        l_score = QVBoxLayout(card_score)
        l_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_widget = ProductivityScoreWidget(self.state)
        l_score.addWidget(self.score_widget)
        top_row.addWidget(card_score)

        # Summary Card
        card_top = QFrame()
        card_top.setObjectName("GlassCard")
        l_top = QVBoxLayout(card_top)
        l_top.addWidget(QLabel("Insights"))
        self.stats_summary_label = QLabel("")
        self.stats_summary_label.setWordWrap(True)
        l_top.addWidget(self.stats_summary_label)
        top_row.addWidget(card_top, 1)
        
        layout.addLayout(top_row)

        # Heatmap Card
        card_heat = QFrame()
        card_heat.setObjectName("GlassCard")
        l_heat = QVBoxLayout(card_heat)
        l_heat.addWidget(QLabel("Activity Heatmap (Last 52 Weeks)"))
        self.heatmap_widget = HeatmapWidget(self.state)
        l_heat.addWidget(self.heatmap_widget)
        layout.addWidget(card_heat)

        # Middle Row: Hourly + Categories
        graphs_layout = QHBoxLayout()
        
        # Hourly
        card_hourly = QFrame()
        card_hourly.setObjectName("GlassCard")
        l_hourly = QVBoxLayout(card_hourly)
        l_hourly.addWidget(QLabel("Most Productive Hours"))
        self.hourly_chart = HourlyChartWidget(self.state)
        l_hourly.addWidget(self.hourly_chart)
        graphs_layout.addWidget(card_hourly)

        # Categories
        card_cat = QFrame()
        card_cat.setObjectName("GlassCard")
        l_cat = QVBoxLayout(card_cat)
        l_cat.addWidget(QLabel("Focus Breakdown"))
        self.category_graph = CategoryGraphWidget(self.state)
        l_cat.addWidget(self.category_graph)
        graphs_layout.addWidget(card_cat)
        
        layout.addLayout(graphs_layout)

        # Bottom Row: Mood + Habits
        bottom_row = QHBoxLayout()

        # Mood Graph
        card_mood = QFrame()
        card_mood.setObjectName("GlassCard")
        l_mood = QVBoxLayout(card_mood)
        l_mood.addWidget(QLabel("Mood History"))
        self.mood_graph = MoodGraphWidget(self.state)
        l_mood.addWidget(self.mood_graph)
        
        # Mood Input (Compact)
        mood_input_row = QHBoxLayout()
        self.mood_combo = QComboBox()
        self.mood_combo.addItems(MOOD_OPTIONS)
        self.mood_save_btn = QPushButton("Log")
        self.mood_save_btn.clicked.connect(self._on_save_mood)
        mood_input_row.addWidget(self.mood_combo)
        mood_input_row.addWidget(self.mood_save_btn)
        l_mood.addLayout(mood_input_row)
        
        # Hidden note field for simplicity in stats view, or keep it if needed
        self.mood_note = QTextEdit()
        self.mood_note.setVisible(False) # Hidden in this new layout to save space
        self.mood_message = QLabel("") # Hidden
        
        bottom_row.addWidget(card_mood)

        # Habit Graph
        card_habit = QFrame()
        card_habit.setObjectName("GlassCard")
        l_habit = QVBoxLayout(card_habit)
        l_habit.addWidget(QLabel("Habit Consistency"))
        self.habit_graph = HabitGraphWidget(self.state)
        l_habit.addWidget(self.habit_graph)
        bottom_row.addWidget(card_habit)
        
        layout.addLayout(bottom_row)
        
        # We removed the habits list from stats page to make room for charts.
        # Habits are still accessible on Home page.
        self.habits_list = QListWidget() # Dummy to prevent errors if referenced elsewhere
        self.habits_header_label = QLabel()
        self.habit_message = QLabel()

    def _build_settings_page(self) -> None:
        self.page_settings = QWidget()
        layout = QVBoxLayout(self.page_settings)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        card = QFrame()
        card.setObjectName("GlassCard")
        l_card = QVBoxLayout(card)
        l_card.setContentsMargins(16, 16, 16, 16)
        l_card.setSpacing(12)

        header = QLabel("Settings")
        header.setObjectName("PageHeader")
        l_card.addWidget(header)

        # --- Widget Settings ---
        self.setting_widget_enabled = QCheckBox("Enable companion widget")
        self.setting_widget_enabled.toggled.connect(self._on_settings_changed)
        l_card.addWidget(self.setting_widget_enabled)

        widget_tasks_layout = QHBoxLayout()
        widget_tasks_layout.addWidget(QLabel("Tasks to show in widget:"))
        self.setting_widget_task_count = QComboBox()
        self.setting_widget_task_count.addItems(["3", "5", "8", "10"])
        self.setting_widget_task_count.currentIndexChanged.connect(self._on_settings_changed)
        widget_tasks_layout.addWidget(self.setting_widget_task_count)
        l_card.addLayout(widget_tasks_layout)

        # --- Hub Settings ---
        self.setting_hub_maximized = QCheckBox("Start Hub maximized")
        self.setting_hub_maximized.toggled.connect(self._on_settings_changed)
        l_card.addWidget(self.setting_hub_maximized)

        self.setting_start_focus = QCheckBox("Start in Focus Mode (Sidebar hidden)")
        self.setting_start_focus.toggled.connect(self._on_settings_changed)
        self.setting_start_focus.setToolTip("Automatically hide the sidebar when the app starts for a cleaner look.")
        l_card.addWidget(self.setting_start_focus)

        # --- System Settings ---
        l_card.addSpacing(10)
        lbl_sys = QLabel("System")
        lbl_sys.setStyleSheet(f"color: {GOLD}; font-weight: bold;")
        l_card.addWidget(lbl_sys)

        self.setting_close_to_tray = QCheckBox("Close button minimizes to tray")
        self.setting_close_to_tray.toggled.connect(self._on_settings_changed)
        l_card.addWidget(self.setting_close_to_tray)

        self.setting_start_windows = QCheckBox("Start TaskFlow with Windows")
        self.setting_start_windows.toggled.connect(self._on_settings_changed)
        l_card.addWidget(self.setting_start_windows)

        # --- Voice Settings ---
        if VOICE_AVAILABLE:
            l_card.addSpacing(10)
            lbl_voice = QLabel("Voice & AI")
            lbl_voice.setStyleSheet(f"color: {GOLD}; font-weight: bold;")
            l_card.addWidget(lbl_voice)
            
            self.setting_voice_enabled = QCheckBox("Enable Voice Input Features")
            self.setting_voice_enabled.setToolTip("Uncheck to disable the microphone button and unload AI models to save memory.")
            self.setting_voice_enabled.toggled.connect(self._on_settings_changed)
            l_card.addWidget(self.setting_voice_enabled)

        # --- Maintenance ---
        l_card.addSpacing(10)
        lbl_maint = QLabel("Maintenance")
        lbl_maint.setStyleSheet(f"color: {GOLD}; font-weight: bold;")
        l_card.addWidget(lbl_maint)

        btn_archive = QPushButton("Archive All Completed Tasks")
        btn_archive.clicked.connect(self._archive_all_completed)
        l_card.addWidget(btn_archive)

        btn_backups = QPushButton("Manage Backups")
        btn_backups.clicked.connect(self._open_backup_manager)
        l_card.addWidget(btn_backups)

        # --- Data Management ---
        l_card.addSpacing(10)
        lbl_data = QLabel("Data & AI")
        lbl_data.setStyleSheet(f"color: {GOLD}; font-weight: bold;")
        l_card.addWidget(lbl_data)

        btn_open_data = QPushButton("Open Data Folder (Edit .json)")
        btn_open_data.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_data.clicked.connect(self._open_data_folder)
        btn_open_data.setStyleSheet(f"background-color: {HOVER_BG}; color: {TEXT_WHITE}; border: 1px solid {GLASS_BORDER}; border-radius: 6px; padding: 8px;")
        l_card.addWidget(btn_open_data)

        l_card.addStretch(1)
        
        lbl_ver = QLabel(f"TaskFlow v{APP_VERSION}")
        lbl_ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_ver.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 12px;")
        l_card.addWidget(lbl_ver)

        layout.addWidget(card)

    def _on_settings_changed(self):
        settings = self.state.setdefault("settings", {})
        
        # Voice Toggle Logic
        if VOICE_AVAILABLE and hasattr(self, "setting_voice_enabled"):
            was_enabled = settings.get("voiceEnabled", True)
            is_enabled = self.setting_voice_enabled.isChecked()
            settings["voiceEnabled"] = is_enabled
            
            if is_enabled and not was_enabled:
                if not self.voice_listener:
                    self.show_toast("Loading Voice AI...")
                    threading.Thread(target=self._init_voice_ai, daemon=True).start()
            elif not is_enabled and was_enabled:
                self.voice_listener = None
                self.command_parser = None
                self.show_toast("Voice AI unloaded.")
        
        settings["widgetEnabled"] = self.setting_widget_enabled.isChecked()
        settings["widgetTaskCount"] = int(self.setting_widget_task_count.currentText())
        settings["startWithHubMaximized"] = self.setting_hub_maximized.isChecked()
        settings["startInFocusMode"] = self.setting_start_focus.isChecked()
        settings["closeToTray"] = self.setting_close_to_tray.isChecked()
        settings["startWithWindows"] = self.setting_start_windows.isChecked()
        
        self._set_startup_registry(settings["startWithWindows"])
        self.schedule_save()

    def _refresh_settings(self):
        settings = self.state.get("settings", {})
        self.setting_widget_enabled.setChecked(settings.get("widgetEnabled", True))
        self.setting_widget_task_count.setCurrentText(str(settings.get("widgetTaskCount", 5)))
        self.setting_hub_maximized.setChecked(settings.get("startWithHubMaximized", True))
        self.setting_start_focus.setChecked(settings.get("startInFocusMode", False))
        self.setting_close_to_tray.setChecked(settings.get("closeToTray", True))
        self.setting_start_windows.setChecked(settings.get("startWithWindows", False))
        if VOICE_AVAILABLE and hasattr(self, "setting_voice_enabled"):
            self.setting_voice_enabled.setChecked(settings.get("voiceEnabled", True))

    def _set_startup_registry(self, enabled: bool):
        """Add or remove the app from Windows startup registry."""
        if not winreg: return
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            if enabled:
                exe = sys.executable
                # If running as script, use python.exe + script path. If frozen (exe), use exe path.
                if getattr(sys, "frozen", False):
                    cmd = f'"{exe}"'
                else:
                    script = os.path.abspath(sys.argv[0])
                    cmd = f'"{exe}" "{script}"'
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Registry error: {e}")

    def _archive_all_completed(self):
        count = 0
        for t in self.state.get("tasks", []):
            if t.get("completed") and t.get("section") != "Archived":
                t["section"] = "Archived"
                t["updatedAt"] = now_iso()
                count += 1
        if count > 0:
            self.schedule_save()
            self.show_toast(f"Moved {count} tasks to Archive.")

    def _open_backup_manager(self):
        dlg = BackupManagerDialog(self.paths, self)
        dlg.exec()

    def _open_data_folder(self):
        folder = self.paths["dir"]
        # On Windows, os.startfile is more reliable for folders than webbrowser
        if sys.platform == "win32":
            os.startfile(folder)
        else:
            open_url_safe(folder)

    # ────────────────────────────────────────────────────────────────────
    # Navigation & page switching
    # ────────────────────────────────────────────────────────────────────

    def _animate_page_in(self) -> None:
        effect = QGraphicsOpacityEffect(self.stack)
        self.stack.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(PAGE_FADE_DURATION_MS)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: self.stack.setGraphicsEffect(None))
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def open_page(self, page_key: str) -> None:
        """Public method to switch pages by a string key."""
        page_map = {
            "home": self.page_home,
            "today": self.page_today,
            "calendar": self.page_scheduled,
            "week": self.page_week,
            "scheduled": self.page_scheduled,
            "someday": self.page_someday,
            "projects": self.page_projects,
            "journal": self.page_journal,
            "stats": self.page_stats,
            "settings": self.page_settings,
            "search": self.page_search,
        }
        target_page = page_map.get(page_key.lower())
        if target_page:
            self._switch_page(target_page)

    def _switch_page(self, page: QWidget) -> None:
        # Update sidebar active state (always, even if same page)
        for btn in self.nav_map.values():
            btn.setChecked(False)
        if page in self.nav_map:
            self.nav_map[page].setChecked(True)
        
        # Clear dialog button highlights when navigating to a page
        self._set_button_highlight(self.btn_feedback, False)
        self._set_button_highlight(self.btn_tips, False)
        self._set_button_highlight(self.btn_settings, False)
        
        # Apply highlight to Settings if navigating to settings page
        if page is self.page_settings:
            self._set_button_highlight(self.btn_settings, True)

        # Only animate and refresh if actually switching pages
        if self.stack.currentWidget() is page:
            return

        self.stack.setCurrentWidget(page)
        AnimationManager.fade_in(self.stack, duration=PAGE_FADE_DURATION_MS)

        if page is self.page_home:
            self._refresh_home()
            self._animate_home_cascade()
        elif page is self.page_today:
            self.page_today.refresh()
        elif page is self.page_week:
            self.page_week.refresh()
        elif page is self.page_scheduled:
            self._on_calendar_date_changed()
            self.calendar.update()
        elif page is self.page_someday:
            self.page_someday.refresh()
        elif page is self.page_journal:
            self.page_journal.refresh()
            # Refresh home insights in case journal changed
            self._refresh_home() 
        elif page is self.page_projects:
            self._refresh_projects()
        elif page is self.page_stats:
            self._refresh_stats_and_habits()
        elif page is self.page_settings:
            self._refresh_settings()
        elif page is self.page_profile:
            self.page_profile.refresh()
        elif page is self.page_search:
            self.page_search.search_input.setFocus()

    def _animate_home_cascade(self) -> None:
        """Cascading fade-in for home page cards."""
        cards = [self.card_focus, self.card_insights, self.card_capture]
        for i, card in enumerate(cards):
            AnimationManager.fade_in(card, duration=400, delay=i*100)

    def _toggle_focus_mode(self) -> None:
        """Toggle the visibility of the sidebar."""
        visible = self.nav_frame.isVisible()
        self.nav_frame.setVisible(not visible)
        self.btn_focus.setChecked(visible) # If it was visible, it's now hidden (checked state implies 'Focus Mode Active')
        
        if visible:
            # We just hid it
            self.statusBar().showMessage("Focus Mode Active. Press Ctrl+B to restore sidebar.", 3000)
        else:
            # We just showed it - celebrate exiting focus mode
            self.statusBar().showMessage("Sidebar restored.", 2000)
            self.celebrate()

    def _set_button_highlight(self, btn: QPushButton, highlighted: bool) -> None:
        """Apply or remove highlight styling to a button."""
        if highlighted:
            btn.setStyleSheet(f"""
                background-color: {HOVER_BG};
                color: {TEXT_WHITE};
                border-radius: 6px;
                font-weight: 600;
                padding-left: 16px;
                border: none;
                text-align: left;
            """)
        else:
            btn.setStyleSheet("")

    def _open_feedback_dialog(self):
        self._set_button_highlight(self.btn_feedback, True)
        dlg = FeedbackDialog(self)
        dlg.exec()
        self._set_button_highlight(self.btn_feedback, False)

    def _open_tips_dialog(self):
        self._set_button_highlight(self.btn_tips, True)
        dlg = QuickTipsDialog(self)
        dlg.exec()
        self._set_button_highlight(self.btn_tips, False)

    def _build_panic_page(self) -> None:
        self.page_panic = QWidget()
        layout = QVBoxLayout(self.page_panic)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(40)
        
        lbl = QLabel("Panic Relief")
        lbl.setStyleSheet(f"color: {GOLD}; font-size: 28px; font-weight: bold;")
        layout.addWidget(lbl, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.panic_background = BreathingCircle()
        self.panic_background.setMinimumSize(400, 400)
        layout.addWidget(self.panic_background, 1)
        
        lbl_instr = QLabel("Follow the circle. Breathe in as it expands, out as it shrinks.")
        lbl_instr.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 14px;")
        layout.addWidget(lbl_instr, 0, Qt.AlignmentFlag.AlignCenter)
        
        btn_exit = QPushButton("I'm feeling better")
        btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exit.setFixedSize(200, 50)
        btn_exit.setStyleSheet(f"background-color: {HOVER_BG}; color: {TEXT_WHITE}; border-radius: 25px; font-size: 16px; border: 1px solid {GLASS_BORDER};")
        btn_exit.clicked.connect(self.exit_panic_mode)
        layout.addWidget(btn_exit, 0, Qt.AlignmentFlag.AlignCenter)

    def enter_panic_mode(self) -> None:
        self.nav_frame.setVisible(False)
        self._switch_page(self.page_panic)
        self.panic_background.start_animation()
        # Play calming sound if available
        self._play_soundscape("Rain")

    def _build_zen_page(self):
        self.page_zen = QWidget()
        layout = QVBoxLayout(self.page_zen)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        
        self.zen_lbl_emoji = QLabel("📝")
        self.zen_lbl_emoji.setStyleSheet("font-size: 64px;")
        self.zen_lbl_emoji.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.zen_lbl_emoji)
        
        self.zen_lbl_text = QLabel("Task")
        self.zen_lbl_text.setWordWrap(True)
        self.zen_lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zen_lbl_text.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 28px; font-weight: bold; margin: 10px;")
        self.zen_lbl_text.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 28px; font-weight: bold; margin: 10px; background-color: rgba(0,0,0,0.4); border-radius: 8px; padding: 5px 10px;")
        layout.addWidget(self.zen_lbl_text)
        
        self.zen_lbl_note = QLabel("")
        self.zen_lbl_note.setWordWrap(True)
        self.zen_lbl_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zen_lbl_note.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 14px; font-style: italic; margin-bottom: 10px;")
        self.zen_lbl_note.setVisible(False)
        layout.addWidget(self.zen_lbl_note)
        
        self.zen_timer_lbl = QLabel("25:00")
        self.zen_timer_lbl.setStyleSheet(f"color: {GOLD}; font-size: 80px; font-weight: bold;")
        self.zen_timer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.zen_timer_lbl)
        
        # Break Controls
        break_layout = QHBoxLayout()
        break_layout.setSpacing(10)
        
        btn_focus = QPushButton("🎯 25m")
        btn_focus.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_focus.setStyleSheet(f"background-color: rgba(255,255,255,0.1); color: {TEXT_WHITE}; border-radius: 15px; padding: 8px 16px;")
        btn_focus.clicked.connect(lambda: self._start_manual_timer(25, "focus"))
        
        btn_break_short = QPushButton("☕ 5m")
        btn_break_short.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_break_short.setStyleSheet(f"background-color: rgba(255,255,255,0.1); color: {TEXT_WHITE}; border-radius: 15px; padding: 8px 16px;")
        btn_break_short.clicked.connect(lambda: self._start_manual_timer(5, "break"))
        
        btn_break_long = QPushButton("🧘 15m")
        btn_break_long.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_break_long.setStyleSheet(f"background-color: rgba(255,255,255,0.1); color: {TEXT_WHITE}; border-radius: 15px; padding: 8px 16px;")
        btn_break_long.clicked.connect(lambda: self._start_manual_timer(15, "break"))

        self.btn_pomodoro = QPushButton("🍅 Pomodoro")
        self.btn_pomodoro.setCheckable(True)
        self.btn_pomodoro.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pomodoro.setStyleSheet(f"background-color: rgba(255,255,255,0.1); color: {TEXT_WHITE}; border-radius: 15px; padding: 8px 16px;")
        self.btn_pomodoro.toggled.connect(self._toggle_pomodoro)

        break_layout.addStretch()
        break_layout.addWidget(btn_focus)
        break_layout.addWidget(btn_break_short)
        break_layout.addWidget(btn_break_long)
        break_layout.addWidget(self.btn_pomodoro)
        break_layout.addStretch()
        layout.addLayout(break_layout)
        
        layout.addSpacing(30)

        # Primary Actions
        action_layout = QHBoxLayout()
        action_layout.setSpacing(20)
        
        self.zen_btn_complete = QPushButton("✅ Complete Task")
        self.zen_btn_complete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zen_btn_complete.setFixedSize(180, 50)
        self.zen_btn_complete.setStyleSheet(f"background-color: {GOLD}; color: {DARK_BG}; border-radius: 25px; font-weight: bold; font-size: 16px;")
        self.zen_btn_complete.clicked.connect(self._complete_zen_task)
        
        btn_exit = QPushButton("Exit Focus")
        btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exit.setFixedSize(140, 50)
        btn_exit.setStyleSheet(f"background-color: rgba(255,255,255,0.1); color: {TEXT_WHITE}; border-radius: 25px; border: 1px solid {GLASS_BORDER}; font-size: 14px;")
        btn_exit.clicked.connect(self.exit_zen_mode)
        
        action_layout.addStretch()
        action_layout.addWidget(self.zen_btn_complete)
        action_layout.addWidget(btn_exit)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        layout.addSpacing(20)

        # Distraction Pad
        self.zen_distraction = QLineEdit()
        self.zen_distraction.setPlaceholderText("Distraction? Type it here to clear your mind...")
        self.zen_distraction.setFixedWidth(400)
        self.zen_distraction.setStyleSheet(f"background-color: rgba(0,0,0,0.3); color: {TEXT_WHITE}; border: 1px solid {HOVER_BG}; border-radius: 8px; padding: 10px;")
        self.zen_distraction.returnPressed.connect(self._on_zen_distraction)
        layout.addWidget(self.zen_distraction)
        
        # Soundscapes
        sound_layout = QHBoxLayout()
        sound_layout.setSpacing(10)
        sound_layout.addStretch()
        
        lbl_sound = QLabel("🎵 Soundscape:")
        lbl_sound.setStyleSheet(f"color: {TEXT_GRAY};")
        sound_layout.addWidget(lbl_sound)
        
        self.combo_sound = QComboBox()
        self.combo_sound.addItems(["Silent", "Rain", "Cafe", "Forest", "Ocean", "Fireplace", "Calm Piano", "White Noise"])
        self.combo_sound.setFixedWidth(120)
        self.combo_sound.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_sound.currentTextChanged.connect(self._on_soundscape_changed)
        sound_layout.addWidget(self.combo_sound)
        
        sound_layout.addStretch()
        layout.addLayout(sound_layout)

        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setFixedWidth(100)
        self.slider_volume.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider_volume.setToolTip("Soundscape Volume")
        self.slider_volume.valueChanged.connect(self._on_zen_volume_changed)
        sound_layout.addWidget(self.slider_volume)
        
        sound_layout.addStretch()

    def _update_zen_background(self, soundscape: str):
        """Changes the background of the Zen page based on the soundscape."""
        style = f"background-color: {DARK_BG};" # Default
        """Changes the background of the Zen page with a fade animation."""
        # If an animation is already running, let it finish to avoid glitches.
        if self.page_zen.graphicsEffect() is not None:
            return
        style = f"background-color: {DARK_BG};"  # Default
        
        image_map = {
            "Rain": "rain.jpg",
            "Forest": "forest.jpg",
            "Cafe": "cafe.jpg",
            "Ocean": "ocean.jpg",
            "Fireplace": "fireplace.jpg",
        }
        
        image_name = image_map.get(soundscape)
        
        if image_name:
            # Path logic adapted from _play_soundscape
            base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            # Assume images are in assets/images
            image_path = os.path.join(base_dir, "assets", "images", image_name)
            
            if not os.path.exists(image_path):
                if not getattr(sys, 'frozen', False):
                    # Fallback for running from source (ui/hub.py -> TaskFlow/assets/images)
                    image_path = os.path.join(os.path.dirname(__file__), "..", "assets", "images", image_name)

            if os.path.exists(image_path):
                css_path = image_path.replace('\\', '/')
                style = f"border-image: url('{css_path}') 0 0 0 0 stretch stretch;"

        final_style = f"QWidget {{ {style} }}"

        # Avoid animation if style is the same or page is not visible
        if self.page_zen.styleSheet() == final_style or not self.page_zen.isVisible():
            self.page_zen.setStyleSheet(final_style)
            return

        # Animate: Fade out, change background, fade in
        effect = QGraphicsOpacityEffect(self.page_zen)
        self.page_zen.setGraphicsEffect(effect)
        
        self.page_zen.setStyleSheet(f"QWidget {{ {style} }}")
        anim_out = QPropertyAnimation(effect, b"opacity", self.page_zen)
        anim_out.setDuration(250)  # Fast fade out
        anim_out.setStartValue(1.0)
        anim_out.setEndValue(0.0)
        anim_out.setEasingCurve(QEasingCurve.Type.InCubic)
        
        def on_faded_out():
            self.page_zen.setStyleSheet(final_style)
            
            anim_in = QPropertyAnimation(effect, b"opacity", self.page_zen)
            anim_in.setDuration(350)  # Slower fade in
            anim_in.setStartValue(0.0)
            anim_in.setEndValue(1.0)
            anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim_in.finished.connect(lambda: self.page_zen.setGraphicsEffect(None))
            anim_in.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

        anim_out.finished.connect(on_faded_out)
        anim_out.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def enter_zen_mode(self, task_id: str):
        t = next((x for x in self.state["tasks"] if x["id"] == task_id), None)
        if not t: return
        
        self._zen_task_id = task_id
        self.zen_lbl_text.setText(t.get("text", ""))
        
        # Show note if exists
        note = t.get("note", "")
        if note:
            self.zen_lbl_note.setText(note)
            self.zen_lbl_note.setVisible(True)
        else:
            self.zen_lbl_note.setVisible(False)

        # Hide sidebar for focus
        self.nav_frame.setVisible(False)
        self.btn_focus.setChecked(True)

        # Restore sound preference
        saved_sound = self.state.get("settings", {}).get("zenSoundscape", "Silent")
        self.combo_sound.setCurrentText(saved_sound)
        self._update_zen_background(saved_sound)
        
        self._switch_page(self.page_zen)
        
        # Start default 25m
        self._start_zen_timer(25, "focus")

    def _toggle_pomodoro(self, checked: bool):
        self._pomodoro_mode = checked
        if checked:
            self.btn_pomodoro.setStyleSheet(f"background-color: {GOLD}; color: {DARK_BG}; border-radius: 15px; padding: 8px 16px; font-weight: bold;")
            self._pomodoro_count = 0
            self._start_zen_timer(25, "focus")
        else:
            self.btn_pomodoro.setStyleSheet(f"background-color: rgba(255,255,255,0.1); color: {TEXT_WHITE}; border-radius: 15px; padding: 8px 16px;")

    def _start_manual_timer(self, minutes: int, session_type: str):
        """Starts a timer and disables Pomodoro mode since this is a manual override."""
        if hasattr(self, "btn_pomodoro"):
            self.btn_pomodoro.setChecked(False)
        self._pomodoro_mode = False
        self._start_zen_timer(minutes, session_type)

    def _start_zen_timer(self, minutes: int, session_type: str = "focus"):
        if session_type == "break":
            self._consecutive_focus_sessions = 0 # Reset counter when a break starts
        self._zen_session_type = session_type
        self._play_soundscape()
        self._zen_seconds = minutes * 60
        self._zen_session_duration = minutes
        self._zen_end_time = datetime.now() + timedelta(seconds=self._zen_seconds)
        self._prevent_sleep()

        if hasattr(self, "_zen_timer"):
            self._zen_timer.stop()
        self._zen_timer = QTimer(self)
        self._zen_timer.timeout.connect(self._update_zen_timer)
        self._zen_timer.start(500) # More frequent updates
        self._update_zen_timer() # Update label immediately

    def _update_zen_timer(self):
        if not hasattr(self, "_zen_end_time"):
            return

        remaining = (self._zen_end_time - datetime.now()).total_seconds()

        if remaining > 0:
            m = int(remaining) // 60
            s = int(remaining) % 60
            self.zen_timer_lbl.setText(f"{m:02}:{s:02}")
        else:
            self.zen_timer_lbl.setText("00:00")
            self._zen_timer.stop()
            self._allow_sleep()

            if winsound:
                try: winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except: pass
            
            # Notify if minimized or in background
            if self.isMinimized() or not self.isActiveWindow():
                msg = "Great focus! Time for a break." if self._zen_session_type == "focus" else "Break over. Ready to focus?"
                self.tray_icon.showMessage("Timer Complete", msg, QSystemTrayIcon.MessageIcon.Information, 4000)
                QApplication.alert(self)
            
            if self._zen_session_type == "focus":
                self.celebrate()

            # Log the completed session
            if self._zen_session_type == "focus":
                log_activity(self.state, "completed", "focusSession", self._zen_task_id, {"duration": self._zen_session_duration})
                self._consecutive_focus_sessions += 1
                self.schedule_save()

            if self._pomodoro_mode:
                self._handle_pomodoro_transition()
            else:
                self._stop_soundscape()
                
                # AI Suggestion: Suggest a break after multiple focus sessions
                if self._zen_session_type == "focus" and self._consecutive_focus_sessions >= 2:
                    reply = QMessageBox.question(self, "Time for a Break?", 
                                                 f"You've focused for {self._consecutive_focus_sessions} sessions straight. Great work!\n\nWould you like to take a 5-minute break?",
                                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if reply == QMessageBox.StandardButton.Yes:
                        self._start_zen_timer(5, "break") # This will reset the counter
                    else:
                        # User declined, reset counter to avoid asking again immediately
                        self._consecutive_focus_sessions = 0
                        self.show_toast("Okay, keep up the great work!")
                else:
                    self.show_toast("Session Complete!")

    def _handle_pomodoro_transition(self):
        if self._zen_session_type == "focus":
            self._pomodoro_count += 1
            # Determine break length (Long break every 4th session)
            is_long = (self._pomodoro_count % 4 == 0)
            duration = 15 if is_long else 5
            
            reply = QMessageBox.question(self, "Pomodoro Focus Complete", f"Great job! You've completed {self._pomodoro_count} session(s).\nStart {duration}m break?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                self._start_zen_timer(duration, "break")
            else:
                self.btn_pomodoro.setChecked(False)
                self._stop_soundscape()
        else: # was break
            reply = QMessageBox.question(self, "Break Over", "Ready to focus again (25m)?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                self._start_zen_timer(25, "focus")
            else:
                self.btn_pomodoro.setChecked(False)
                self._stop_soundscape()

    def _on_zen_distraction(self):
        text = self.zen_distraction.text().strip()
        if text:
            # Add to ideas
            add_idea(self.state, f"Zen Thought: {text}")
            self.schedule_save()
            self.zen_distraction.clear()
            # Visual feedback
            self.show_toast("Saved to Ideas! Stay focused.")
        if not text:
            return

        # Parse input
        meta = parse_task_input(text)
        
        # AI Enrichment
        difficulty = 1
        xp = 10
        duration = 0
        
        if self.ai_engine:
            # Predict Category if missing
            if not meta["category"]:
                context = {
                    "time_of_day": current_time_of_day(),
                    "day_of_week": datetime.now().strftime("%A"),
                    "mood": get_today_mood(self.state).get("value", "Unknown") if get_today_mood(self.state) else "Unknown"
                }
                meta["category"] = self.ai_engine.predict_category(meta["text"], context)
            
            # Analyze Complexity & Duration
            difficulty = self.ai_engine.analyze_task_complexity(meta["text"])
            xp = difficulty * 15
            duration = self.ai_engine.estimate_duration(meta["text"])

        # Add as task
        add_task(
            self.state,
            text=meta["text"],
            section=meta["section"],
            category=meta["category"],
            important=meta["important"],
            tags=meta.get("tags", []),
            difficulty=difficulty,
            xpReward=xp,
            estimatedDuration=duration
        )

        self.schedule_save()
        self.zen_distraction.clear()
        
        # Visual feedback
        self.show_toast(f"Saved to {meta['section']}! Stay focused.")

    def _on_soundscape_changed(self, text):
        self.state.setdefault("settings", {})["zenSoundscape"] = text
        self.schedule_save()
        if self.isVisible() and self.stack.currentWidget() == self.page_zen:
            self._update_zen_background(text)
            self._play_soundscape()

    def _on_zen_volume_changed(self, value: int):
        if not self.media_player: return
        # Convert 0-100 to 0.0-1.0 for QAudioOutput
        volume = value / 100.0
        self.audio_output.setVolume(volume)
        
        # Save setting
        self.state.setdefault("settings", {})["zenVolume"] = volume
        self.schedule_save()

    def _play_soundscape(self, sound_name: Optional[str] = None):
        if not self.media_player: return
        
        sound = sound_name or self.combo_sound.currentText()
        if sound == "Silent":
            self.media_player.stop()
            return
            
        # Map names to files (assuming they exist in a 'sounds' folder)
        filename = f"{sound.lower().replace(' ', '_')}.mp3"
        
        # Look in current directory or a 'sounds' subdirectory
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        sound_path = os.path.join(base_dir, "sounds", filename)
        
        if not os.path.exists(sound_path):
            # Fallback to check if running from source
            if not getattr(sys, 'frozen', False):
                sound_path = os.path.join(os.path.dirname(__file__), "sounds", filename)
        
        if os.path.exists(sound_path):
            self.media_player.setSource(QUrl.fromLocalFile(sound_path))
            self.media_player.setLoops(QMediaPlayer.Loops.Infinite)
            self.media_player.play()

    def _stop_soundscape(self):
        if self.media_player:
            self.media_player.stop()

    def _complete_zen_task(self):
        if not self._zen_task_id:
            return
        
        toggle_task_completed(self.state, self._zen_task_id)
        
        if winsound:
            try: winsound.MessageBeep(winsound.MB_OK)
            except: pass
        self.celebrate()
        
        self.schedule_save()
        self.exit_zen_mode()

    def exit_panic_mode(self):
        self.panic_background.stop_animation()
        self._stop_soundscape()
        if self._panic_breathing_timer:
            self._panic_breathing_timer.stop()
        self.nav_frame.setVisible(True)
        self._switch_page(self.page_home)

    def exit_zen_mode(self):
        self._consecutive_focus_sessions = 0 # Reset on manual exit
        self._pomodoro_mode = False
        if hasattr(self, "btn_pomodoro"):
            self.btn_pomodoro.setChecked(False)
        self._update_zen_background("Silent") # Reset background
        self._stop_soundscape()
        self._allow_sleep()
        self._zen_task_id = None
        if hasattr(self, "_zen_timer"):
            self._zen_timer.stop()
        self.nav_frame.setVisible(True)
        self.btn_focus.setChecked(False)
        self._switch_page(self.page_home)

    # ────────────────────────────────────────────────────────────────────
    # Home page logic
    # ────────────────────────────────────────────────────────────────────

    def _refresh_home(self) -> None:
        stats = self.state.get("stats", {})
        mood = get_today_mood(self.state)
        mood_value = mood.get("value") if mood else None
        
        # Update Streak & XP
        streak = stats.get("currentStreak", 0)
        xp = stats.get("xp", 0)
        level = int(1 + (xp / 500)) # Simple level formula
        current_level_xp = xp % 500
        
        self.lbl_streak.setText(f"🔥 {streak}")
        self.lbl_level.setText(f"Lvl {level}")
        self.xp_bar.setValue(int((current_level_xp / 500) * 100))
        self.xp_bar.setToolTip(f"{current_level_xp} / 500 XP to Level {level + 1}")
        
        # Update Greeting
        name = get_user_name(self.state)
        if hasattr(self, "lbl_greeting"):
            tod = current_time_of_day().capitalize()
            self.lbl_greeting.setText(f"Good {tod}, {name}.")

        # Card 1: Today at a glance
        counts = count_today_tasks(self.state)
        total = counts["total"]
        done = counts["completed"]
        important_left = len([
            t for t in tasks_in_section(self.state, "Today")
            if t.get("important") and not t.get("completed")
        ])

        if total == 0:
            summary_line = "Nothing planned for Today yet. It's okay to have a light day."
        else:
            summary_line = f"{done} of {total} tasks done"
            if important_left > 0:
                summary_line += f" · {important_left} important left."
        self.today_summary_line.setText(summary_line)

        # Show Primary Goal
        daily_logs = stats.get("dailyLogs", {})
        today_log = daily_logs.get(today_str())
        if today_log and today_log.get("primaryGoal"):
            self.btn_primary_goal.setText(f"★ {today_log['primaryGoal']}")
            self.btn_primary_goal.setToolTip("Click to edit")
        else:
            self.btn_primary_goal.setText("Set a main goal +")

        tasks = [t for t in tasks_in_section(self.state, "Today") if not t.get("completed")]
        if not tasks:
            self.btn_up_next.setText("No tasks for today. You can keep it light.")
            self.btn_up_next.setEnabled(False)
        else:
            # Pick the most important one
            top_task = tasks[0]
            txt = top_task.get("text", "")
            if top_task.get("important"):
                txt = f"🔥 {txt}"
            
            self.btn_up_next.setText(txt)
            self.btn_up_next.setEnabled(True)
            
            # Disconnect previous connections to avoid multiple firings
            try: self.btn_up_next.clicked.disconnect()
            except TypeError: pass
            
            self.btn_up_next.clicked.connect(lambda: self.enter_zen_mode(top_task["id"]))

        # Use AI for the home suggestion
        if self.ai_engine:
            suggestions = self.ai_engine.get_proactive_suggestions(self.state)
            if suggestions:
                self.suggestion_label.setText(f"💡 {suggestions[0]['text']}")
            else:
                self.suggestion_label.setText(f"<i>AI Coach is analyzing...</i>")
        else:
            self.suggestion_label.setText(f"<i>AI Coach is ready.</i>")

        # Card 3: Ideas list
        self.ideas_list.clear()
        for idea in self.state.get("ideas", []):
            item = QListWidgetItem(idea.get("text", ""))
            item.setData(Qt.ItemDataRole.UserRole, idea.get("id"))
            self.ideas_list.addItem(item)

        # Card 2: Mood & habits snapshot
        mood_str = f"You're in '{mood_value}' mode" if mood_value else "No mood checked in yet"
        checks = get_today_habit_checks(self.state)
        habits = [h for h in self.state.get("habits", []) if h.get("active", True)]
        habits_done = sum(1 for h in habits if checks.get(h.get("id", ""), False))
        habits_str = f"{habits_done} of {len(habits)} habits done" if habits else "No habits set up"
        self.snapshot_summary.setText(f"{mood_str} · {habits_str}.")
        self.snapshot_hint.setText("Even one habit is enough to count today.")
        
        # Refresh Habit Buttons
        while self.habits_layout.count():
            child = self.habits_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        for h in habits:
            is_done = checks.get(h["id"], False)
            # Use first letter of habit name
            letter = h["name"][0].upper() if h["name"] else "?"
            
            btn = QPushButton(letter)
            btn.setFixedSize(32, 32)
            btn.setCheckable(True)
            btn.setChecked(is_done)
            btn.setToolTip(h["name"])
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Dynamic Style
            bg = GOLD if is_done else "rgba(255,255,255,0.1)"
            fg = DARK_BG if is_done else TEXT_WHITE
            border = GOLD if is_done else HOVER_BG
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    color: {fg};
                    border: 1px solid {border};
                    border-radius: 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    border: 1px solid {GOLD};
                    background-color: {GOLD if is_done else HOVER_BG};
                    color: {DARK_BG if is_done else TEXT_WHITE};
                }}
            """)
            
            # Connect with closure to capture ID
            btn.clicked.connect(lambda checked, hid=h["id"]: self._on_toggle_habit_from_home(hid, checked))
            self.habits_layout.addWidget(btn)

        # Bottom area
        idx = hash(today_str()) % len(MOTIVATIONAL_QUOTES) if MOTIVATIONAL_QUOTES else 0
        quote = MOTIVATIONAL_QUOTES[idx] if MOTIVATIONAL_QUOTES else ""
        self.quote_label.setText(f'"{quote}"')

    def _on_toggle_habit_from_home(self, habit_id, checked):
        set_habit_checked(self.state, habit_id, checked)
        self.schedule_save()
        self._refresh_home()
        if checked:
            self.celebrate()

    def _mood_message_for_value(self, value: str) -> str:
        if value == "Low energy":
            return "Low days happen. You’re allowed to go slow and do tiny steps."
        if value == "Stressed":
            return "Stress is heavy. You don’t have to win the whole day, just make it softer."
        if value == "Okay":
            return "An okay day is still a real day. One or two gentle wins are enough."
        if value == "Motivated":
            return "Nice, you’re motivated. Let’s use that energy without burning you out."
        if value == "Great":
            return "Enjoy the good days. You don’t need to be perfect to deserve them."
        return "There are good days and bad days. You still deserve kindness on all of them."

    # ────────────────────────────────────────────────────────────────────
    # Projects page logic
    # ────────────────────────────────────────────────────────────────────

    def _refresh_projects(self) -> None:
        self.project_list.clear()
        projects = self.state.get("projects", [])
        tasks = self.state.get("tasks", [])
        current_widget_proj_id = self.state.get("widgetCurrentProjectId")

        for p in projects:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, p.get("id"))
            self.project_list.addItem(item)
            
            row = ProjectListRow(p, tasks, is_focus=(p.get("id") == current_widget_proj_id))
            item.setSizeHint(row.sizeHint())
            self.project_list.setItemWidget(item, row)

        self.empty_projects_label.setVisible(self.project_list.count() == 0)
        self.project_detail_title.setText("Select a project")
        self.project_task_widget.set_project(None)

    def _on_add_project(self) -> None:
        name, ok = QInputDialog.getText(self, "New project", "Project name:")
        if not ok or not name.strip():
            return
        proj = add_project(self.state, name.strip())
        self.schedule_save()
        self._refresh_projects()
        # Select the new project
        for i in range(self.project_list.count()):
            item = self.project_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == proj.get("id"):
                self.project_list.setCurrentItem(item)
                break

    def _on_rename_project(self) -> None:
        item = self.project_list.currentItem()
        if not item:
            return
        pid = item.data(Qt.ItemDataRole.UserRole)
        proj = get_project_by_id(self.state, pid)
        if not proj:
            return
        new_name, ok = QInputDialog.getText(
            self, "Rename project", "New name:", text=proj.get("name", "")
        )
        if ok and new_name.strip():
            proj["name"] = new_name.strip()
            proj["updatedAt"] = now_iso()
            self.schedule_save()
            self._refresh_projects()

    def _duplicate_project(self, project_id: str) -> None:
        new_proj = duplicate_project(self.state, project_id)
        if new_proj:
            self.schedule_save()
            self._refresh_projects()

    def _on_project_menu(self, pos) -> None:
        item = self.project_list.itemAt(pos)
        if not item: return
        
        menu = QMenu(self)
        act_dup = menu.addAction("Duplicate")
        act_ren = menu.addAction("Rename")
        act_del = menu.addAction("Delete")
        
        action = menu.exec(self.project_list.mapToGlobal(pos))
        if not action: return
        
        if action == act_dup:
            self._duplicate_project(item.data(Qt.ItemDataRole.UserRole))
        elif action == act_ren:
            self._on_rename_project()
        elif action == act_del:
            self._on_delete_project()

    def _on_delete_project(self) -> None:
        item = self.project_list.currentItem()
        if not item:
            return
        pid = item.data(Qt.ItemDataRole.UserRole)
        proj = get_project_by_id(self.state, pid)
        if not proj:
            return
        reply = QMessageBox.question(
            self,
            "Delete project",
            f"Are you sure you want to delete '{proj.get('name', 'Untitled')}'?\n"
            "This will unassign it from all tasks.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        # Unassign project from tasks
        for t in self.state.get("tasks", []):
            if t.get("projectId") == pid:
                t["projectId"] = None
        # Remove project
        self.state["projects"] = [
            p for p in self.state.get("projects", []) if p.get("id") != pid
        ]
        self.schedule_save()
        self._refresh_projects()

    def _on_project_selected(self) -> None:
        items = self.project_list.selectedItems()
        if not items:
            self.project_detail_title.setText("Select a project")
            self.project_task_widget.set_project(None)
            self.state["widgetCurrentProjectId"] = None
            self.schedule_save()
            return
        item = items[0]
        pid = item.data(Qt.ItemDataRole.UserRole)
        proj = get_project_by_id(self.state, pid)
        if not proj:
            self.project_detail_title.setText("Project not found")
            self.project_task_widget.set_project(None)
            self.state["widgetCurrentProjectId"] = None
            self.schedule_save()
            return
        self.project_detail_title.setText(proj.get("name", "Untitled"))
        self.project_task_widget.set_project(pid)
        self.state["widgetCurrentProjectId"] = pid
        self.project_task_widget.btn_suggest.setVisible(True) # Show suggest button when project selected
        self.schedule_save()

    # ────────────────────────────────────────────────────────────────────
    # Stats & habits logic
    # ────────────────────────────────────────────────────────────────────

    def _refresh_stats_and_habits(self) -> None:
        # Generate insights using analytics engine
        rate = get_completion_rate(self.state)
        hour = get_most_productive_hour(self.state)
        
        summary_html = (
            f"<p style='font-size:16px; margin-bottom:4px;'><b>Completion Rate:</b> <span style='color:{GOLD}'>{int(rate)}%</span></p>"
            f"<p style='font-size:14px; color:{TEXT_GRAY};'>Most productive around {hour}:00</p>"
        )

        self.stats_summary_label.setText(summary_html)

        # Refresh graphs
        self.mood_graph.update()
        self.habit_graph.update()
        self.category_graph.update()
        self.score_widget.update()
        self.heatmap_widget.update()
        self.hourly_chart.update()

    def _on_toggle_habit(self, habit_id: str, checked: bool) -> None:
        set_habit_checked(self.state, habit_id, checked)
        self.schedule_save()
        # Also refresh header counts quickly
        self._refresh_stats_and_habits()

    def _on_add_idea(self) -> None:
        text = self.idea_input.text().strip()
        if not text:
            return
        idea = add_idea(self.state, text)
        self.schedule_save()
        self.idea_input.clear()
        
        item = QListWidgetItem(idea.get("text", ""))
        item.setData(Qt.ItemDataRole.UserRole, idea.get("id"))
        self.ideas_list.insertItem(0, item)

    def _on_idea_menu(self, pos) -> None:
        item = self.ideas_list.itemAt(pos)
        if not item: return
        menu = QMenu(self)
        act_del = menu.addAction("Delete")
        action = menu.exec(self.ideas_list.mapToGlobal(pos))
        if action == act_del:
            self._delete_idea(item.data(Qt.ItemDataRole.UserRole))

    def _delete_idea(self, idea_id: str) -> None:
        delete_idea(self.state, idea_id)
        self.schedule_save()
        self._refresh_home()

    def _on_brain_dump(self, onboarding: bool = False) -> None:
        dlg = BrainDumpDialog(self)
        if onboarding:
            dlg.setWindowTitle("Welcome! Let's start with a Brain Dump 🧠")

        if dlg.exec() == QDialog.DialogCode.Accepted:
            text = dlg.text_edit.toPlainText().strip()
            if not text: return
            
            created_ids = []
            use_ai = dlg.chk_ai.isChecked()
            
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            
            for line in lines:
                # Use shared parser from core.model
                meta = parse_task_input(line)
                
                # AI Category Prediction
                if use_ai and self.ai_engine and not meta["category"]:
                    context = {
                        "time_of_day": current_time_of_day(),
                        "day_of_week": datetime.now().strftime("%A"),
                        "mood": get_today_mood(self.state).get("value", "Unknown") if get_today_mood(self.state) else "Unknown"
                    }
                    meta["category"] = self.ai_engine.predict_category(meta["text"], context)
                
                # AI Complexity
                diff = 1
                xp = 10
                dur = 0
                if self.ai_engine:
                    diff = self.ai_engine.analyze_task_complexity(meta["text"])
                    xp = diff * 15
                    dur = self.ai_engine.estimate_duration(meta["text"])
                
                t = add_task(
                    self.state, 
                    text=meta["text"], 
                    section=meta["section"], 
                    category=meta["category"], 
                    important=meta["important"],
                    difficulty=diff,
                    xpReward=xp,
                    estimatedDuration=dur
                )
                created_ids.append(t["id"])
            
            self.schedule_save()
            
            if created_ids:
                self.confetti.burst()
                QMessageBox.information(self, "Brain Dump", f"Captured {len(created_ids)} items.")
                
                # Navigate to where tasks went
                if any(t["section"] == "Today" for t in self.state["tasks"] if t["id"] in created_ids):
                    self._switch_page(self.page_today)
                else:
                    self._switch_page(self.page_someday)

    def _on_voice_input(self):
        """Handles the voice button click."""
        if not VOICE_AVAILABLE:
            QMessageBox.warning(self, "Voice Not Available", "Voice dependencies (pyaudio, faster_whisper) are missing.")
            return
            
        # Check if disabled in settings
        if not self.state.get("settings", {}).get("voiceEnabled", True):
            reply = QMessageBox.question(
                self, 
                "Voice Disabled", 
                "Voice features are currently disabled in Settings.\nWould you like to enable them now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                # Enable and trigger load
                self.state.setdefault("settings", {})["voiceEnabled"] = True
                if hasattr(self, "setting_voice_enabled"):
                    self.setting_voice_enabled.setChecked(True)
                self._on_settings_changed() # This will trigger the load
            return
            
        if not self.voice_listener or not self.voice_listener.model:
            self.show_toast("Voice AI is still loading... please wait.")
            return
            
        if self.voice_listener.load_error:
            QMessageBox.warning(self, "Voice Error", f"Voice AI failed to load: {self.voice_listener.load_error}")
            return

        # Show listening dialog
        self.voice_dialog = VoiceDialog(self)
        self.voice_dialog.show()
        
        # Start worker (5 seconds recording for now)
        self._voice_worker = VoiceWorker(self.voice_listener, self.command_parser, duration=5)
        self._voice_worker.finished.connect(self._on_voice_finished)
        self._voice_worker.error.connect(self._on_voice_error)
        self._voice_worker.amplitude.connect(self.voice_dialog.update_level)
        self._voice_worker.start()

    def _on_voice_error(self, msg):
        if hasattr(self, "voice_dialog"):
            self.voice_dialog.close()
        QMessageBox.warning(self, "Voice Error", msg)

    def _on_voice_finished(self, actions):
        if hasattr(self, "voice_dialog"):
            self.voice_dialog.close()
            
        if not actions:
            self.show_toast("Could not understand command.")
            return
            
        count = 0
        for action in actions:
            self._process_voice_action(action)
            count += 1
            
        self.show_toast(f"Processed {count} voice commands.")
        self.schedule_save()
        self._refresh_home()
        self.confetti.burst()

    def _process_voice_action(self, action):
        """Executes a single parsed voice action."""
        intent = action.get("intent")
        
        if intent == "create_task":
            # Map parsed date/time to schedule dict
            schedule = None
            if action.get("due_date"):
                schedule = {"date": action["due_date"], "time": action.get("due_time")}
            
            section = "Today" if not schedule else "Scheduled"
            
            add_task(self.state, text=action["text"], section=section, schedule=schedule)
            
        elif intent == "create_project":
            add_project(self.state, action.get("name", "New Project"))
            
        elif intent == "set_goal":
            # Set today's primary goal
            today = today_str()
            self.state["stats"].setdefault("dailyLogs", {}).setdefault(today, {})["primaryGoal"] = action["text"]
            
        elif intent == "log_mood":
            set_today_mood(self.state, action["value"], action.get("note", ""))

    # ────────────────────────────────────────────────────────────────────
    # Updates, saving & close
    # ────────────────────────────────────────────────────────────────────

    def _check_updates_async(self, manual: bool = False) -> None:
        if requests is None:
            if manual:
                QMessageBox.warning(self, "Update Check", "The 'requests' library is missing. Cannot check for updates.")
            return

        def worker():
            latest_version, download_url, error = fetch_latest_release()
            QTimer.singleShot(
                0,
                lambda: self._on_update_check_result(latest_version, download_url, error, manual),
            )

        threading.Thread(target=worker, daemon=True).start()

    def _on_update_check_result(
        self,
        latest_version: Optional[str],
        download_url: Optional[str],
        error: Optional[str],
        manual: bool,
    ) -> None:
        if error:
            if manual:
                QMessageBox.warning(self, "Update Check Failed", f"Error checking for updates:\n{error}")
            return
            
        if not latest_version:
            if manual:
                QMessageBox.information(self, "Update Check", "Could not determine the latest version.")
            return
            
        stats = self.state.setdefault("stats", {})
        
        # If manual check, we ignore the "ignored version" preference to show it anyway
        if not manual and stats.get("lastIgnoredVersion") == latest_version:
            return
            
        if not is_newer_version(latest_version, APP_VERSION):
            if manual:
                self.show_toast(f"You are up to date (v{APP_VERSION}).")
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Update available")
        msg.setText(
            f"A new version of TaskFlow is available: {latest_version}.\n\n"
            f"Your version: {APP_VERSION}."
        )
        checkbox = QCheckBox("Don't remind me about this version again")
        msg.setCheckBox(checkbox)
        if download_url:
            msg.setInformativeText(
                "Would you like to open the download page?"
            )
            msg.setStandardButtons(
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
            )
            ret = msg.exec()
            if ret == QMessageBox.StandardButton.Ok:
                open_url_safe(download_url)
        else:
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()

        if checkbox.isChecked():
            stats["lastIgnoredVersion"] = latest_version
            self.schedule_save()

    def _on_save_mood(self) -> None:
        value = self.mood_combo.currentText()
        
        # Preserve existing note if the editor is hidden/empty
        existing = get_today_mood(self.state)
        note = existing.get("note", "") if existing else ""
        
        if self.mood_note.isVisible():
            note = self.mood_note.toPlainText().strip()
            
        set_today_mood(self.state, value, note)
        self.schedule_save()
        self._refresh_stats_and_habits()

    def _on_data_changed(self) -> None:
        """Refresh the currently visible page when data changes."""
        current = self.stack.currentWidget()
        if current is self.page_today:
            self.page_today.refresh()
        elif current is self.page_week:
            self.page_week.refresh()
        elif current is self.page_scheduled:
            self._on_calendar_date_changed()
            self.calendar.update()
        elif current is self.page_someday:
            self.page_someday.refresh()
        elif current is self.page_projects:
            self.project_task_widget.refresh()
        elif current is self.page_stats:
            self._refresh_stats_and_habits()
        elif current is self.page_home:
            self._refresh_home()

    def _show_tip_of_the_day(self) -> None:
        """Shows a tip from the AI engine if available."""
        if self.ai_engine and hasattr(self.ai_engine, "get_tip_of_the_day"):
            tip = self.ai_engine.get_tip_of_the_day()
            if tip:
                self.show_toast(f"💡 AI Tip: {tip}")

    def _run_onboarding_flow(self) -> None:
        """Show the brain dump dialog on first launch if no tasks exist."""
        stats = self.state.setdefault("stats", {})
        if not stats.get("didShowBrainDumpOnboarding", False):
            if not self.state.get("tasks"):
                self._on_brain_dump(onboarding=True)
                stats["didShowBrainDumpOnboarding"] = True
                self.schedule_save()

    def _run_welcome_flow(self) -> None:
        """Show the welcome dialog once per day to set mood and primary goal."""
        today = today_str()
        daily_logs = self.state.setdefault("stats", {}).setdefault("dailyLogs", {})
        if today not in daily_logs:
            dlg = WelcomeDialog(self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                data = dlg.get_data()
                daily_logs[today] = data
                if data.get("mood"):
                    set_today_mood(self.state, data["mood"])
                self.schedule_save()
                self._refresh_home()

    def _run_weekly_review_flow(self) -> None:
        """On Mondays, show the weekly review dialog if it hasn't been shown today."""
        if datetime.now().weekday() != 0:  # 0 is Monday
            return

        today = today_str()
        stats = self.state.setdefault("stats", {})
        if stats.get("lastWeeklyReviewDate") != today:
            dlg = WeeklyReviewDialog(self.state, self.schedule_save, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                stats["lastWeeklyReviewDate"] = today
                if dlg.chk_archive.isChecked():
                    for t in self.state.get("tasks", []):
                        if t.get("completed") and t.get("section") != "Archived":
                            t["section"] = "Archived"
                            t["updatedAt"] = now_iso()
                self.schedule_save()
                self._refresh_home()

    def _run_start_of_day_flow(self) -> None:
        """Check if we need to show the Welcome Screen or Daily Planning."""
        # The order of these flows is intentional.
        self._run_onboarding_flow()
        self._run_welcome_flow()
        self._run_daily_planning()
        self._run_weekly_review_flow()

    def _run_daily_planning(self, force: bool = False) -> None:
        stats = self.state.setdefault("stats", {})
        last_planning_date = stats.get("lastPlanningDate")
        today = today_str()
        if last_planning_date == today and not force:
            return

        # Count carried-over Today tasks
        today_tasks = [
            t for t in self.state.get("tasks", []) if t.get("section") == "Today" and not t.get("completed")
        ]
        dlg = DailyPlanningDialog(len(today_tasks), self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            planned = dlg.planned_tasks()
            stats["plannedTasksToday"] = planned
            stats["targetTasksToday"] = planned
            mood = get_today_mood(self.state)
            stats["moodAtStart"] = mood.get("value") if mood else None
            stats["lastPlanningDate"] = today
            self.schedule_save()

    def schedule_save(self) -> None:
        self._save_timer.start()
        self.data_changed.emit()

    def _do_save(self) -> None:
        # Persist window geometry
        g = self.geometry()
        self.state["uiGeometry"] = [g.x(), g.y(), g.width(), g.height()]
        save_state(self.paths, self.state)
        # Generate and save the User Training JSON ("User JSON")

    def _force_quit(self):
        """Really quit the application."""
        self._do_save()
        QApplication.quit()

    def closeEvent(self, event) -> None:
        # Check if we should minimize to tray instead
        settings = self.state.get("settings", {})
        if settings.get("closeToTray", True) and self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "TaskFlow", 
                "Running in background. Click icon to restore.", 
                QSystemTrayIcon.MessageIcon.Information, 
                2000
            )
            event.ignore()
            return
            
        self._do_save()
        super().closeEvent(event)


# ============================================================================
# SECTION 7: ENTRY POINT
# ============================================================================

def debug_main() -> None:
    """For running the Hub in isolation for development."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    paths = get_data_paths()
    state = load_state(paths)
    rollover_tasks(state)
    save_state(paths, state)

    splash = SplashWindow()
    splash.show()
    app.processEvents()
    
    # Simulate loading time
    start_time = time.time()
    min_duration_ms = 3000
    
    progress_timer = QTimer()

    def show_hub():
        # Keep reference to avoid GC
        show_hub.window = HubWindow(state, paths)
        if state.get("settings", {}).get("startWithHubMaximized", True):
            show_hub.window.showMaximized()
        else:
            show_hub.window.show()
            
        show_hub.window.start_post_load_tasks()

    def update_progress():
        elapsed_ms = (time.time() - start_time) * 1000
        
        if elapsed_ms >= min_duration_ms:
            splash.set_progress(100)
            splash.finish_loading()
            progress_timer.stop()
            QTimer.singleShot(400, show_hub)
        else:
            # Keep filling progress bar linearly up to 90% over minimum duration
            progress = min(90, (elapsed_ms / min_duration_ms) * 100)
            splash.set_progress(int(progress))
            
    progress_timer.timeout.connect(update_progress)
    progress_timer.start(50)

    sys.exit(app.exec())


if __name__ == "__main__":
    debug_main()
