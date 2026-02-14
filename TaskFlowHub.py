# ============================================================================
# SECTION 1: IMPORTS & SETUP
# ============================================================================

from __future__ import annotations

import sys
import os
import json
import html
import random
import threading
import webbrowser
import re
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Callable

from PyQt6.QtCore import (
    Qt,
    QTimer,
    QSize,
    QPropertyAnimation,
    QEasingCurve,
    QRectF,
    QPoint,
    QParallelAnimationGroup,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPen,
    QBrush,
    QShortcut,
    QKeySequence,
)
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
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
    QCalendarWidget,
)

try:
    import requests
except ImportError:
    requests = None


# Shared model & theme (data model, colors, constants, helpers)
from taskflowmodel import (
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
    add_idea,
    delete_idea,
    get_today_widget_note,
    set_today_widget_note,
    get_journal_entry,
    set_journal_entry,
    count_today_tasks,
    add_task,
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
    parse_version_tuple,
    is_newer_version,
    GITHUB_OWNER,
    GITHUB_REPO,
    GITHUB_API_LATEST,
)

# Import new analytics engine
import taskflowanalytics
import taskflowai

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


class SplashWindow(QMainWindow):
    """
    Soft startup screen with a watery gradient and a rotating quote.

    Shown briefly at app launch before the main hub window.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)

        self._build_ui()
        self._center_on_screen()

        # Start fully transparent, then fade in
        self._opacity_effect.setOpacity(0.0)
        self._fade_in()

    def _build_ui(self) -> None:
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(600, 360)

        central = QWidget(self)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Background card with gradient + glass
        card = QFrame()
        card.setObjectName("SplashCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(16)

        title = QLabel(APP_NAME)
        f = title.font()
        f.setPointSize(24)
        f.setBold(True)
        title.setFont(f)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        quote = QLabel(self._pick_quote())
        quote.setWordWrap(True)
        quote.setAlignment(Qt.AlignmentFlag.AlignCenter)
        quote.setStyleSheet(f"color: {TEXT_GRAY}; font-style: italic;")

        subtitle = QLabel("A gentle space to plan and breathe.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {TEXT_WHITE};")

        card_layout.addWidget(title)
        card_layout.addWidget(quote)
        card_layout.addWidget(subtitle)

        layout.addWidget(card)

        # Style
        self.setStyleSheet(
            f"""
            QMainWindow {{
                background-color: transparent;
            }}
            QFrame#SplashCard {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(20, 30, 60, 220),
                    stop:1 rgba(10, 15, 30, 220)
                );
                border-radius: 24px;
                border: 1px solid {GLASS_BORDER};
            }}
            """
        )

        # Light shadow for depth
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 12)
        card.setGraphicsEffect(shadow)

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

    def _fade_in(self) -> None:
        anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        anim.setDuration(SPLASH_FADE_MS)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(self._hold_then_fade_out)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _hold_then_fade_out(self) -> None:
        QTimer.singleShot(
            max(0, SPLASH_DURATION_MS - 2 * SPLASH_FADE_MS),
            self._fade_out,
        )

    def _fade_out(self) -> None:
        anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        anim.setDuration(SPLASH_FADE_MS)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.finished.connect(self._on_finished)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _on_finished(self) -> None:
        self.close()


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


class WelcomeDialog(QDialog):
    """
    Start-of-Day screen to capture mood and main focus.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Welcome Back")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Greeting
        lbl_greet = QLabel(f"Good {current_time_of_day()}.")
        lbl_greet.setStyleSheet(f"color: {GOLD}; font-size: 22px; font-weight: bold;")
        layout.addWidget(lbl_greet)

        layout.addWidget(QLabel("How are you feeling right now?"))

        self.mood_combo = QComboBox()
        self.mood_combo.addItems(MOOD_OPTIONS)
        layout.addWidget(self.mood_combo)

        layout.addWidget(QLabel("What is your one main goal for today?"))
        self.goal_input = QLineEdit()
        self.goal_input.setPlaceholderText("e.g. Finish the report")
        layout.addWidget(self.goal_input)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Start Day")
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.setStyleSheet(f"""
            QDialog {{ background-color: {CARD_BG}; }}
            QLabel {{ color: {TEXT_WHITE}; }}
            QLineEdit, QComboBox {{ background-color: rgba(0,0,0,0.3); color: {TEXT_WHITE}; border: 1px solid {HOVER_BG}; border-radius: 6px; padding: 6px; }}
        """)

    def get_data(self) -> Dict[str, Any]:
        return {
            "mood": self.mood_combo.currentText(),
            "primaryGoal": self.goal_input.text().strip()
        }

# ============================================================================
# SECTION 4: DIALOGS & SMALL VISUAL WIDGETS
# ============================================================================


class DailyPlanningDialog(QDialog):
    """
    Gentle dialog shown once per day to set a realistic number of tasks.

    It acknowledges leftover tasks and encourages a light plan.
    """

    def __init__(self, incomplete_today_count: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Daily planning")
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        if incomplete_today_count > 0:
            info = (
                f"You have {incomplete_today_count} incomplete task(s) carried over."
                "\nLet's set a gentle plan for today."
            )
        else:
            info = "Ready for a fresh start. Let's plan today lightly."
        info_label = QLabel(info)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        layout.addWidget(QLabel("How many tasks do you realistically want to focus on today?"))

        self.spinbox = QSpinBox()
        self.spinbox.setRange(0, MAX_PLANNED_TASKS)
        self.spinbox.setValue(DEFAULT_PLANNED_TASKS)
        layout.addWidget(self.spinbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Style to match glass theme
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {CARD_BG};
            }}
            QLabel {{
                color: {TEXT_WHITE};
            }}
            QSpinBox {{
                background-color: {CARD_BG};
                color: {TEXT_WHITE};
                border-radius: 6px;
                border: 1px solid {HOVER_BG};
                padding: 2px 6px;
            }}
            """
        )

    def planned_tasks(self) -> int:
        return self.spinbox.value()

class BrainDumpDialog(QDialog):
    """
    A dialog for bulk task entry with AI processing options.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Brain Dump 🧠")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        lbl = QLabel("Unload your mind. Type a list or a paragraph, and we'll sort it out.")
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 14px;")
        layout.addWidget(lbl)
        
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
        layout.addWidget(self.text_edit)
        
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
        
        layout.addLayout(opt_layout)
        
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
        layout.addWidget(buttons)
        
        self.setStyleSheet(f"background-color: {CARD_BG};")

    def get_text(self) -> str:
        return self.text_edit.toPlainText()
        
    def use_ai(self) -> bool:
        return self.chk_ai.isChecked()

class ProfileWidget(QWidget):
    """
    Page to configure the AI persona and user details.
    """
    def __init__(self, state: Dict[str, Any], save_callback, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state = state
        self._save_callback = save_callback
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        header = QLabel("AI Coach Settings")
        header.setObjectName("PageHeader")
        layout.addWidget(header)

        # Form
        form_card = QFrame()
        form_card.setObjectName("GlassCard")
        f_layout = QVBoxLayout(form_card)
        f_layout.setSpacing(15)

        f_layout.addWidget(QLabel("What should I call you?"))
        self.name_input = QLineEdit()
        self.name_input.textChanged.connect(self._save)
        f_layout.addWidget(self.name_input)

        f_layout.addWidget(QLabel("What is your primary role? (e.g. Student, Developer)"))
        self.role_input = QLineEdit()
        self.role_input.textChanged.connect(self._save)
        f_layout.addWidget(self.role_input)

        f_layout.addWidget(QLabel("Coaching Style"))
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Gentle", "Direct", "Stoic", "Hype"])
        self.style_combo.currentTextChanged.connect(self._save)
        f_layout.addWidget(self.style_combo)

        layout.addWidget(form_card)
        layout.addStretch(1)

    def refresh(self):
        p = self.state.get("userProfile", {})
        self.name_input.setText(p.get("name", ""))
        self.role_input.setText(p.get("role", ""))
        self.style_combo.setCurrentText(p.get("style", "Gentle"))

    def _save(self):
        p = self.state.setdefault("userProfile", {})
        p["name"] = self.name_input.text()
        p["role"] = self.role_input.text()
        p["style"] = self.style_combo.currentText()
        self._save_callback()

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
        
        data = taskflowanalytics.get_category_breakdown(self.state)
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
        score = taskflowanalytics.get_productivity_score(self.state)
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
        
        data = taskflowanalytics.get_hourly_activity(self.state)
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
        
        data = taskflowanalytics.get_activity_heatmap_data(self.state)
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

# ============================================================================
# SECTION 4.5: SHARED UI HELPERS
# ============================================================================


def animate_widget_entry(widget: QWidget):
    """Fade in animation for newly added widgets."""
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(ANIM_DURATION_MEDIUM)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.finished.connect(lambda: widget.setGraphicsEffect(None))
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

def create_task_row_widget(
    task: Dict[str, Any],
    on_toggle: Callable[[bool, str], None],
    on_delete: Callable[[bool, str], None],
    on_context_menu: Callable[[QPoint, str], None]
) -> QWidget:
    """
    Creates a standardized task row widget used in multiple lists.
    """
    row = QWidget()
    row.setObjectName("TaskRow")
    row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    row.setStyleSheet(f"""
        #TaskRow {{
            border-radius: 8px;
            background-color: transparent;
        }}
        #TaskRow:hover {{ background-color: {HOVER_BG}; }}
    """)
    row.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    hl = QHBoxLayout(row)
    hl.setContentsMargins(6, 2, 6, 2)
    hl.setSpacing(6)

    chk = QPushButton("✔" if task.get("completed") else "")
    chk.setFixedSize(QSize(22, 22))
    chk.setCheckable(True)
    chk.setChecked(task.get("completed", False))
    chk.setStyleSheet(
        f"""
        QPushButton {{
            background-color: transparent;
            border-radius: 11px;
            border: 1px solid {HOVER_BG};
            color: {GOLD};
            font-weight: bold;
        }}
        QPushButton:checked {{
            background-color: {GOLD};
            color: {DARK_BG};
        }}
        """
    )

    # Build label with metadata (schedule/recurrence)
    text_content = task.get("text", "")
    meta_info = []
    
    sched = task.get("schedule")
    if sched and isinstance(sched, dict) and sched.get("date"):
        meta_info.append(f"📅 {sched['date']}")
    
    rec = task.get("recurrence")
    if rec and isinstance(rec, dict) and rec.get("type"):
        meta_info.append(f"↻ {rec['type']}")

    cat = task.get("category")
    if cat:
        meta_info.append(f"🏷 {cat}")

    lbl = QLabel()
    lbl.setWordWrap(True)
    if task.get("completed"):
        lbl.setStyleSheet(f"color: {TEXT_GRAY}; text-decoration: line-through;")
    elif task.get("important"):
        lbl.setStyleSheet(f"color: {GOLD}; font-weight: bold;")
    else:
        lbl.setStyleSheet(f"color: {TEXT_WHITE};")
    
    if meta_info:
        safe_text = html.escape(text_content)
        meta_html = f"<br><span style='color:{TEXT_GRAY}; font-size:10px;'>{'  '.join(meta_info)}</span>"
        lbl.setText(safe_text + meta_html)
    else:
        lbl.setText(text_content)

    del_btn = QPushButton("×")
    del_btn.setFixedSize(QSize(24, 24))
    del_btn.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {TEXT_GRAY}; font-weight: bold; font-size: 14px; }} QPushButton:hover {{ color: {GOLD}; }}")

    hl.addWidget(chk)
    hl.addWidget(lbl, 1)
    hl.addWidget(del_btn)

    tid = task.get("id")
    chk.clicked.connect(lambda c: on_toggle(c, tid))
    del_btn.clicked.connect(lambda c: on_delete(c, tid))
    row.customContextMenuRequested.connect(lambda pos: on_context_menu(pos, tid))

    return row

# ============================================================================
# SECTION 5: TASK LIST WIDGETS (TODAY / WEEK / SOMEDAY / PROJECTS)
# ============================================================================


class TaskListWidget(QWidget):
    """
    Simple vertical task list for a given section (Today, This Week, Someday).

    Handles:
    - Quick add
    - Per-task actions (complete, delete, rename, move, mark important, assign project)
    - Section-wide actions (mark all done, clear completed, send completed to Someday)
    - Optional "What should I do next?" / focus suggestion for Today
    """

    def __init__(
        self,
        state: Dict[str, Any],
        section: str,
        save_callback,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.state = state
        self.section = section
        self._save_callback = save_callback

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
        self.tasks_list = QListWidget()
        self.tasks_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.tasks_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.tasks_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        layout.addWidget(self.tasks_list, 1)

    # ────────────────────────────────────────────────────────────────────
    # Refresh & rendering
    # ────────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Rebuild the list for the current section."""
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
                    "No tasks for Today.\n\nAdd one small thing to get started."
                )
            elif self.section == "This Week":
                self.empty_label.setText(
                    "No tasks for This Week.\n\nPlan ahead gently."
                )
            elif self.section == "Someday":
                self.empty_label.setText(
                    "No tasks for Someday.\n\nCapture ideas for later."
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

                row = create_task_row_widget(
                    t,
                    lambda _, tid: self._on_toggle_task(tid),
                    lambda _, tid: self._on_delete_task(tid),
                    lambda pos, tid: self._show_task_menu(tid, row.mapToGlobal(pos))
                )

                self.tasks_list.addItem(item)
                self.tasks_list.setItemWidget(item, row)

        self.tasks_list.setUpdatesEnabled(True)

    # ────────────────────────────────────────────────────────────────────
    # Handlers & actions
    # ────────────────────────────────────────────────────────────────────

    def _on_quick_add(self) -> None:
        text = self.quick_add_input.text().strip()
        if not text:
            return
            
        # Parse category from text (e.g., "Buy milk #Personal")
        category = None
        match = re.search(r"#(\w+)", text)
        if match:
            category = match.group(1)
            text = text.replace(match.group(0), "").strip()
            
        task = add_task(self.state, text=text, section=self.section, category=category)
        
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

        # Animate the new item
        for i in range(self.tasks_list.count()):
            item = self.tasks_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == task["id"]:
                self.tasks_list.scrollToItem(item)
                row = self.tasks_list.itemWidget(item)
                if row:
                    animate_widget_entry(row)
                break

    def _on_toggle_task(self, task_id: str) -> None:
        task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
        if not task:
            return

        is_completing = not task.get("completed", False)

        if is_completing:
            for i in range(self.tasks_list.count()):
                item = self.tasks_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == task_id:
                    row = self.tasks_list.itemWidget(item)
                    if row:
                        self._animate_and_finalize_toggle(row, task_id)
                    return
        else:
            toggle_task_completed(self.state, task_id)
            self._save_callback()
            self.refresh()

    def _animate_and_finalize_toggle(self, row: QWidget, task_id: str):
        effect = QGraphicsOpacityEffect(row)
        row.setGraphicsEffect(effect)
        group = QParallelAnimationGroup(self)
        anim_fade = QPropertyAnimation(effect, b"opacity")
        anim_fade.setDuration(ANIM_DURATION_MEDIUM)
        anim_fade.setStartValue(1.0)
        anim_fade.setEndValue(0.0)
        anim_fade.setEasingCurve(QEasingCurve.Type.InQuad)
        anim_size = QPropertyAnimation(row, b"maximumHeight")
        anim_size.setDuration(ANIM_DURATION_MEDIUM)
        anim_size.setStartValue(row.height())
        anim_size.setEndValue(0)
        anim_size.setEasingCurve(QEasingCurve.Type.InCubic)
        group.addAnimation(anim_fade)
        group.addAnimation(anim_size)
        group.finished.connect(row.hide)
        group.finished.connect(lambda: self._finalize_toggle(task_id))
        group.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _finalize_toggle(self, task_id: str):
        toggle_task_completed(self.state, task_id)
        self._save_callback()
        self.refresh()

    def _on_delete_task(self, task_id: str) -> None:
        delete_task(self.state, task_id)
        self._save_callback()
        self.refresh()

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
        elif action.parentWidget() is move_menu:
            new_section = action.text()
            self._move_task_section(task_id, new_section)
        elif action.parentWidget() is proj_menu:
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

        # Prefer important tasks, then lowest order
        candidates.sort(
            key=lambda t: (
                0 if t.get("important") else 1,
                t.get("order", 0),
            )
        )
        target = candidates[0]
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
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.state = state
        self._save_callback = save_callback
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

            row = create_task_row_widget(
                t,
                lambda _, tid: self._on_toggle_task(tid),
                lambda _, tid: self._on_delete_task(tid),
                lambda pos, tid: self._show_task_menu(tid, row.mapToGlobal(pos))
            )

            self.tasks_list.addItem(item)
            self.tasks_list.setItemWidget(item, row)

    def _set_enabled(self, enabled: bool) -> None:
        self.quick_add_input.setEnabled(enabled)
        self.btn_send_today.setEnabled(enabled)
        self.btn_mark_all.setEnabled(enabled)
        self.btn_clear_completed.setEnabled(enabled)
        self.tasks_list.setEnabled(enabled)

    # ────────────────────────────────────────────────────────────────────
    # Handlers
    # ────────────────────────────────────────────────────────────────────

    def _on_quick_add(self) -> None:
        text = self.quick_add_input.text().strip()
        if not text or not self._project_id:
            return
        task = add_task(
            self.state,
            text=text,
            section="Someday",
            project_id=self._project_id,
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
                    animate_widget_entry(row)
                break

    def _on_toggle_task(self, task_id: str) -> None:
        task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
        if not task:
            return

        is_completing = not task.get("completed", False)

        if is_completing:
            for i in range(self.tasks_list.count()):
                item = self.tasks_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == task_id:
                    row = self.tasks_list.itemWidget(item)
                    if row:
                        self._animate_and_finalize_toggle(row, task_id)
                    return
        else:
            toggle_task_completed(self.state, task_id)
            self._save_callback()
            self.refresh()

    def _animate_and_finalize_toggle(self, row: QWidget, task_id: str):
        """Animate a row out, then finalize the data change and refresh."""
        effect = QGraphicsOpacityEffect(row)
        row.setGraphicsEffect(effect)
        group = QParallelAnimationGroup(self)
        anim_fade = QPropertyAnimation(effect, b"opacity")
        anim_fade.setDuration(ANIM_DURATION_MEDIUM)
        anim_fade.setStartValue(1.0)
        anim_fade.setEndValue(0.0)
        anim_fade.setEasingCurve(QEasingCurve.Type.InQuad)
        anim_size = QPropertyAnimation(row, b"maximumHeight")
        anim_size.setDuration(ANIM_DURATION_MEDIUM)
        anim_size.setStartValue(row.height())
        anim_size.setEndValue(0)
        anim_size.setEasingCurve(QEasingCurve.Type.InCubic)
        group.addAnimation(anim_fade)
        group.addAnimation(anim_size)
        group.finished.connect(row.hide)
        group.finished.connect(lambda: self._finalize_toggle(task_id))
        group.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _finalize_toggle(self, task_id: str):
        """This is called after the completion animation finishes."""
        toggle_task_completed(self.state, task_id)
        self._save_callback()
        self.refresh()

    def _on_delete_task(self, task_id: str) -> None:
        delete_task(self.state, task_id)
        self._save_callback()
        self.refresh()

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
        elif action.parentWidget() is move_menu:
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


class JournalWidget(QWidget):
    """
    Simple daily journal with a date list and text editor.
    """
    def __init__(self, state: Dict[str, Any], save_callback, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state = state
        self._save_callback = save_callback
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
        l_left = QVBoxLayout(left_panel)
        l_left.addWidget(QLabel("Entries"))
        
        self.date_list = QListWidget()
        self.date_list.itemSelectionChanged.connect(self._on_date_selected)
        l_left.addWidget(self.date_list)
        layout.addWidget(left_panel)

        # Right: Editor
        right_panel = QFrame()
        right_panel.setObjectName("GlassCard")
        l_right = QVBoxLayout(right_panel)
        
        self.lbl_date_header = QLabel("")
        self.lbl_date_header.setStyleSheet(f"color: {GOLD}; font-size: 16px; font-weight: bold;")
        l_right.addWidget(self.lbl_date_header)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Write your thoughts here...")
        self.editor.textChanged.connect(self._on_text_changed)
        l_right.addWidget(self.editor)
        
        layout.addWidget(right_panel)

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
            self.editor.setPlainText(entry.get("text", "") if entry else "")
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
        text = self.editor.toPlainText()
        set_journal_entry(self.state, self._current_date, text)
        self._save_callback()

# ============================================================================
# SECTION 6: HUB WINDOW - LAYOUT, NAVIGATION & PAGES
# ============================================================================


class HubWindow(QMainWindow):
    data_changed = pyqtSignal()
    """Main TaskFlow Hub window: planning + mental health workspace."""

    def __init__(self, state: Dict[str, Any], paths: Dict[str, str]):
        super().__init__()
        self.state = state
        self.paths = paths

        # Geometry
        geom = self.state.get("uiGeometry")
        if geom and isinstance(geom, list) and len(geom) == 4:
            x, y, w, h = geom
            self.setGeometry(x, y, w, h)

        self.setWindowTitle(f"{APP_NAME} Hub v{APP_VERSION}")

        # Debounced save timer
        self._save_timer = QTimer(self)
        self._save_timer.setInterval(SAVE_DEBOUNCE_MS)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._do_save)

        # Focus session tracking (in-memory)
        self._session_completed_today = 0

        self._build_ui()
        self._refresh_home()

        # Apply shadows to all glass cards
        for widget in self.findChildren(QFrame, "GlassCard"):
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(0, 0, 0, 80))
            shadow.setOffset(0, 4)
            widget.setGraphicsEffect(shadow)

        # Background update check + daily planning
        self._check_updates_async()
        QTimer.singleShot(500, self._run_start_of_day_flow)
        
        # Listen for data changes to refresh UI (e.g. from Widget)
        self.data_changed.connect(self._on_data_changed)
        
        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+1"), self, activated=lambda: self._switch_page(self.page_home))
        QShortcut(QKeySequence("Ctrl+2"), self, activated=lambda: self._switch_page(self.page_today))
        QShortcut(QKeySequence("Ctrl+3"), self, activated=lambda: self._switch_page(self.page_week))
        QShortcut(QKeySequence("Ctrl+4"), self, activated=lambda: self._switch_page(self.page_someday))
        QShortcut(QKeySequence("Ctrl+5"), self, activated=lambda: self._switch_page(self.page_projects))
        QShortcut(QKeySequence("Ctrl+6"), self, activated=lambda: self._switch_page(self.page_stats))
        QShortcut(QKeySequence("Ctrl+T"), self, activated=lambda: self._switch_page(self.page_today))
        QShortcut(QKeySequence("Ctrl+P"), self, activated=lambda: self._switch_page(self.page_projects))
        QShortcut(QKeySequence("Ctrl+B"), self, activated=self._toggle_focus_mode)

    # ────────────────────────────────────────────────────────────────────
    # UI construction
    # ────────────────────────────────────────────────────────────────────

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
            
            /* Active Sidebar Button */
            QPushButton:checked {{
                background-color: {HOVER_BG};
                border-left: 2px solid {GOLD};
                color: {GOLD};
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

        self.btn_home = QPushButton("Home")
        self.btn_today = QPushButton("Today")
        self.btn_scheduled = QPushButton("Scheduled")
        self.btn_week = QPushButton("This Week")
        self.btn_projects = QPushButton("Projects")
        self.btn_journal = QPushButton("Journal")
        self.btn_stats = QPushButton("Stats")
        self.btn_someday = QPushButton("Someday")
        self.btn_profile = QPushButton("AI Coach")

        self.btn_focus = QPushButton("Focus Mode (Ctrl+B)")
        # New Settings Button
        self.btn_settings = QPushButton("Settings")
        self.btn_check_updates = QPushButton("Check updates")
        self.btn_quit = QPushButton("Exit Hub")

        for btn in (
            self.btn_home,
            self.btn_today,
            self.btn_scheduled,
            self.btn_week,
            self.btn_projects,
            self.btn_journal,
            self.btn_stats,
            self.btn_someday,
            self.btn_profile,
            self.btn_focus,
        ):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.setMinimumHeight(38)
            nav_layout.addWidget(btn)

        nav_layout.addStretch(1)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet(f"background-color: {GLASS_BORDER}; margin-top: 8px; margin-bottom: 8px;")
        sep.setFixedHeight(1)
        nav_layout.addWidget(sep)

        for btn in (self.btn_focus, self.btn_settings, self.btn_check_updates, self.btn_quit):
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
        self._build_settings_page()
        self.page_profile = ProfileWidget(self.state, self.schedule_save)

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
        self.stack.addWidget(self.page_profile)

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
            self.page_profile: self.btn_profile,
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
        self.btn_quit.clicked.connect(self.close)
        self.btn_check_updates.clicked.connect(self._check_updates_async)
        self.btn_focus.clicked.connect(self._toggle_focus_mode)

    # ────────────────────────────────────────────────────────────────────
    # Page builders
    # ────────────────────────────────────────────────────────────────────

    def _build_home_page(self) -> None:
        self.page_home = QWidget()
        layout = QVBoxLayout(self.page_home)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Card 1: Today at a glance
        card_glance = QFrame()
        card_glance.setObjectName("GlassCard")
        l_glance = QVBoxLayout(card_glance)
        l_glance.setContentsMargins(16, 16, 16, 16)
        l_glance.setSpacing(8)

        lbl_gl = QLabel("Today at a glance")
        lbl_gl.setStyleSheet(f"color: {GOLD}; font-weight: bold; font-size: 16px;")
        l_glance.addWidget(lbl_gl)

        lbl_expl = QLabel("Today is for now. This Week is flexible. Someday is for ideas.")
        lbl_expl.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 11px; margin-bottom: 4px;")
        l_glance.addWidget(lbl_expl)

        self.today_summary_line = QLabel("")
        self.today_summary_line.setWordWrap(True)
        l_glance.addWidget(self.today_summary_line)

        self.lbl_primary_goal = QLabel("")
        self.lbl_primary_goal.setWordWrap(True)
        self.lbl_primary_goal.setStyleSheet(f"color: {GOLD}; font-weight: bold; font-size: 14px; margin-top: 4px;")
        self.lbl_primary_goal.setVisible(False)
        l_glance.addWidget(self.lbl_primary_goal)

        self.home_glance_tasks = QLabel("")
        self.home_glance_tasks.setWordWrap(True)
        l_glance.addWidget(self.home_glance_tasks)

        self.suggestion_label = QLabel("")
        self.suggestion_label.setWordWrap(True)
        self.suggestion_label.setStyleSheet(
            f"color: {TEXT_GRAY}; font-style: italic; margin-top: 4px;"
        )
        l_glance.addWidget(self.suggestion_label)
        layout.addWidget(card_glance)

        # Card 2: Mood & habits snapshot
        card_snapshot = QFrame()
        card_snapshot.setObjectName("GlassCard")
        l_snapshot = QVBoxLayout(card_snapshot)
        l_snapshot.setContentsMargins(16, 16, 16, 16)
        l_snapshot.setSpacing(8)

        self.snapshot_summary = QLabel("")
        self.snapshot_summary.setWordWrap(True)
        l_snapshot.addWidget(self.snapshot_summary)

        self.snapshot_hint = QLabel("")
        self.snapshot_hint.setWordWrap(True)
        self.snapshot_hint.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 11px;")
        l_snapshot.addWidget(self.snapshot_hint)
        layout.addWidget(card_snapshot)

        # Card 3: Ideas & Notes
        card_ideas = QFrame()
        card_ideas.setObjectName("GlassCard")
        l_ideas = QVBoxLayout(card_ideas)
        l_ideas.setContentsMargins(16, 16, 16, 16)
        l_ideas.setSpacing(8)

        l_ideas.addWidget(QLabel("Ideas & Notes"))

        self.idea_input = QLineEdit()
        self.idea_input.setPlaceholderText("Capture a tiny idea...")
        self.idea_input.returnPressed.connect(self._on_add_idea)
        l_ideas.addWidget(self.idea_input)

        self.ideas_list = QListWidget()
        self.ideas_list.setStyleSheet("QListWidget { background: transparent; }")
        self.ideas_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ideas_list.customContextMenuRequested.connect(self._on_idea_menu)
        l_ideas.addWidget(self.ideas_list, 1)

        layout.addWidget(card_ideas)


        # Spacer + quote + quick links
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.quote_label = QLabel("")
        self.quote_label.setWordWrap(True)
        self.quote_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.quote_label.setStyleSheet(f"color: {TEXT_GRAY}; font-style: italic;")
        layout.addWidget(self.quote_label)

        quick_links_layout = QHBoxLayout()
        
        btn_brain_dump = QPushButton("🧠 Brain Dump")
        btn_brain_dump.setStyleSheet(f"background-color: {HOVER_BG}; color: {GOLD}; font-weight: bold;")
        btn_brain_dump.clicked.connect(self._on_brain_dump)
        
        btn_open_today = QPushButton("Open Today")
        btn_open_projects = QPushButton("Open Projects")
        btn_open_today.clicked.connect(lambda: self._switch_page(self.page_today))
        btn_open_projects.clicked.connect(lambda: self._switch_page(self.page_projects))
        
        quick_links_layout.addWidget(btn_brain_dump)
        quick_links_layout.addStretch(1)
        quick_links_layout.addWidget(btn_open_today)
        quick_links_layout.addWidget(btn_open_projects)
        quick_links_layout.addStretch(1)
        layout.addLayout(quick_links_layout)

    def _build_task_pages(self) -> None:
        self.page_today = TaskListWidget(self.state, "Today", self.schedule_save)
        self.page_week = TaskListWidget(self.state, "This Week", self.schedule_save)
        self.page_scheduled = TaskListWidget(self.state, "Scheduled", self.schedule_save)
        self.page_someday = TaskListWidget(self.state, "Someday", self.schedule_save)
        self.page_journal = JournalWidget(self.state, self.schedule_save)

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

        self.project_task_widget = ProjectTaskListWidget(self.state, self.schedule_save)
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

        l_card.addStretch(1)
        layout.addWidget(card)

    def _on_settings_changed(self):
        settings = self.state.setdefault("settings", {})
        settings["widgetEnabled"] = self.setting_widget_enabled.isChecked()
        settings["widgetTaskCount"] = int(self.setting_widget_task_count.currentText())
        settings["startWithHubMaximized"] = self.setting_hub_maximized.isChecked()
        self.schedule_save()

    def _refresh_settings(self):
        settings = self.state.get("settings", {})
        self.setting_widget_enabled.setChecked(settings.get("widgetEnabled", True))
        self.setting_widget_task_count.setCurrentText(str(settings.get("widgetTaskCount", 5)))
        self.setting_hub_maximized.setChecked(settings.get("startWithHubMaximized", True))

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
            "week": self.page_week,
            "scheduled": self.page_scheduled,
            "someday": self.page_someday,
            "projects": self.page_projects,
            "journal": self.page_journal,
            "stats": self.page_stats,
            "settings": self.page_settings,
        }
        target_page = page_map.get(page_key.lower())
        if target_page:
            self._switch_page(target_page)

    def _switch_page(self, page: QWidget) -> None:
        if self.stack.currentWidget() is page:
            return

        self.stack.setCurrentWidget(page)
        self._animate_page_in()

        # Update sidebar active state
        for btn in self.nav_map.values():
            btn.setChecked(False)
        if page in self.nav_map:
            self.nav_map[page].setChecked(True)

        if page is self.page_home:
            self._refresh_home()
        elif page is self.page_today:
            self.page_today.refresh()
        elif page is self.page_week:
            self.page_week.refresh()
        elif page is self.page_scheduled:
            self.page_scheduled.refresh()
        elif page is self.page_someday:
            self.page_someday.refresh()
        elif page is self.page_journal:
            self.page_journal.refresh()
        elif page is self.page_projects:
            self._refresh_projects()
        elif page is self.page_stats:
            self._refresh_stats_and_habits()
        elif page is self.page_settings:
            self._refresh_settings()
        elif page is self.page_profile:
            self.page_profile.refresh()

    def _toggle_focus_mode(self) -> None:
        """Toggle the visibility of the sidebar."""
        visible = self.nav_frame.isVisible()
        self.nav_frame.setVisible(not visible)
        self.btn_focus.setChecked(visible) # If it was visible, it's now hidden (checked state implies 'Focus Mode Active')
        
        if visible:
            # We just hid it
            self.statusBar().showMessage("Focus Mode Active. Press Ctrl+B to restore sidebar.", 3000)

    # ────────────────────────────────────────────────────────────────────
    # Home page logic
    # ────────────────────────────────────────────────────────────────────

    def _refresh_home(self) -> None:
        stats = self.state.get("stats", {})
        mood = get_today_mood(self.state)
        mood_value = mood.get("value") if mood else None

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
            self.lbl_primary_goal.setText(f"★ Focus: {today_log['primaryGoal']}")
            self.lbl_primary_goal.setVisible(True)
        else:
            self.lbl_primary_goal.setVisible(False)

        tasks = [t for t in tasks_in_section(self.state, "Today") if not t.get("completed")]
        if not tasks:
            glance_html = "No tasks for today. You can keep it light."
        else:
            lines = ["<ul>"]
            for t in tasks[:MAX_TODAY_SUGGESTION_TASKS]:
                txt = t.get("text", "")
                if t.get("important"):
                    lines.append(f"<li><b>{txt}</b></li>")
                else:
                    lines.append(f"<li>{txt}</li>")
            lines.append("</ul>")
            glance_html = "".join(lines)
        self.home_glance_tasks.setText(glance_html)

        # Use AI for the home suggestion to keep the persona consistent
        insights = taskflowai.generate_insights(self.state)
        suggestion = insights["advice"]
        self.suggestion_label.setText(f"<i>{suggestion}</i>")

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

        # Bottom area
        idx = hash(today_str()) % len(MOTIVATIONAL_QUOTES) if MOTIVATIONAL_QUOTES else 0
        quote = MOTIVATIONAL_QUOTES[idx] if MOTIVATIONAL_QUOTES else ""
        self.quote_label.setText(f'"{quote}"')

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
        current_widget_proj_id = self.state.get("widgetCurrentProjectId")

        for p in projects:
            name = p.get("name", "Untitled")
            if p.get("id") == current_widget_proj_id:
                name += " (Widget Focus)"
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, p.get("id"))
            self.project_list.addItem(item)

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
        self.schedule_save()

    # ────────────────────────────────────────────────────────────────────
    # Stats & habits logic
    # ────────────────────────────────────────────────────────────────────

    def _refresh_stats_and_habits(self) -> None:
        # Get intelligent insights
        insights = taskflowai.generate_insights(self.state)
        
        summary_html = (
            f"<p style='font-size:16px; margin-bottom:4px;'><b>Current Vibe:</b> <span style='color:{GOLD}'>{insights['mood_guess']}</span></p>"
            f"<p style='font-size:14px; margin-bottom:8px;'>{insights['advice']}</p>"
            f"<p style='font-size:12px; color:{TEXT_GRAY}; font-style:italic;'>💡 Suggestion: {insights['task_suggestion']}</p>"
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
        add_idea(self.state, text)
        self.schedule_save()
        self.idea_input.clear()
        self._refresh_home()  # To show the new idea in the list

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

    def _on_brain_dump(self) -> None:
        dlg = BrainDumpDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            text = dlg.get_text().strip()
            if not text: return
            
            count = 0
            if dlg.use_ai():
                # Use the new analytics function
                suggestions = taskflowai.analyze_brain_dump(text, self.state)
                for s in suggestions:
                    add_task(
                        self.state, 
                        text=s["text"], 
                        section=s.get("section", "Today"), 
                        category=s["category"], 
                        important=s["important"]
                    )
                    count += 1
            else:
                # Simple split by newline
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                for l in lines:
                    add_task(self.state, text=l, section="Today")
                    count += 1
            
            self.schedule_save()
            QMessageBox.information(self, "Brain Dump", f"Added {count} tasks to Today.")

    # ────────────────────────────────────────────────────────────────────
    # Updates, saving & close
    # ────────────────────────────────────────────────────────────────────

    def _check_updates_async(self) -> None:
        if requests is None:
            return

        def worker():
            latest_version, download_url, error = fetch_latest_release()
            QTimer.singleShot(
                0,
                lambda: self._on_update_check_result(latest_version, download_url, error),
            )

        threading.Thread(target=worker, daemon=True).start()

    def _on_update_check_result(
        self,
        latest_version: Optional[str],
        download_url: Optional[str],
        error: Optional[str],
    ) -> None:
        if error or not latest_version:
            return
        stats = self.state.setdefault("stats", {})
        if stats.get("lastIgnoredVersion") == latest_version:
            return
        if not is_newer_version(latest_version, APP_VERSION):
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
            self.page_scheduled.refresh()
        elif current is self.page_someday:
            self.page_someday.refresh()
        elif current is self.page_projects:
            self.project_task_widget.refresh()
        elif current is self.page_stats:
            self._refresh_stats_and_habits()
        elif current is self.page_home:
            self._refresh_home()

    def _run_start_of_day_flow(self) -> None:
        """Check if we need to show the Welcome Screen or Daily Planning."""
        today = today_str()
        stats = self.state.setdefault("stats", {})
        daily_logs = stats.setdefault("dailyLogs", {})

        # 1. Welcome Flow (Once per day)
        if today not in daily_logs:
            dlg = WelcomeDialog(self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                data = dlg.get_data()
                daily_logs[today] = data
                # Sync mood to existing mood system
                if data.get("mood"):
                    set_today_mood(self.state, data["mood"])
                self.schedule_save()
                self._refresh_home()

        # 2. Gentle Planning Check
        self._run_daily_planning()

    def _run_daily_planning(self) -> None:
        stats = self.state.setdefault("stats", {})
        last_planning_date = stats.get("lastPlanningDate")
        today = today_str()
        if last_planning_date == today:
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

    def closeEvent(self, event) -> None:
        # Optional: End-of-day reflection dialog could go here
        self._do_save()
        super().closeEvent(event)


# ============================================================================
# SECTION 7: ENTRY POINT
# ============================================================================

def debug_main() -> None:
    """For running the Hub in isolation for development."""
    app = QApplication(sys.argv)
    paths = get_data_paths()
    state = load_state(paths)
    rollover_tasks(state)
    save_state(paths, state)

    splash = SplashWindow()
    splash.show()

    def show_hub():
        window = HubWindow(state, paths)
        if state.get("settings", {}).get("startWithHubMaximized", True):
            window.showMaximized()
        else:
            window.show()

    QTimer.singleShot(SPLASH_DURATION_MS, show_hub)
    sys.exit(app.exec())


if __name__ == "__main__":
    debug_main()
