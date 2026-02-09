# ============================================================================
# TASKFLOW HUB V6.0 - Planning & Mental Health Workspace
# ============================================================================

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1: IMPORTS & SETUP
# ═══════════════════════════════════════════════════════════════════════════


import sys
import os
import json
import random
import threading
import webbrowser
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional
from PyQt6.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve, QRectF, QPoint
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QShortcut, QKeySequence, QIcon, QPixmap
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
    QMenu, QSpinBox ,QLineEdit, QGraphicsDropShadowEffect

)

try:
    import requests
except ImportError:
    requests = None

from taskflow_model import (
    APP_NAME, APP_VERSION, DATA_DIR_NAME, DARK_BG, CARD_BG, HOVER_BG, GLASS_BG, GLASS_BORDER,
    TEXT_WHITE, TEXT_GRAY, GOLD, PRESSED_BG, SECTIONS, MOTIVATIONAL_QUOTES,
    MOOD_OPTIONS, today_str, now_iso, get_data_paths, atomic_write_json,
    default_state, validate_and_migrate_state, load_state, save_state,
    get_today_mood, set_today_mood, count_today_tasks, add_task,
    tasks_in_section, toggle_task_completed, delete_task, get_project_by_id,
    add_project, tasks_for_project, get_today_habit_checks,
    set_habit_checked, rollover_tasks
)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: CONSTANTS & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Colors – dark, gold, cozy

GITHUB_OWNER = "Dyvorn"
GITHUB_REPO = "TaskFlow"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"


def parse_version_tuple(v: str) -> tuple:
    """Convert version string like '6.0' or 'v6.0.1' to tuple of ints."""
    v = v.strip()
    if v.lower().startswith("v"):
        v = v[1:]
    parts = v.split(".")
    nums = []
    for p in parts:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    # Ensure at least 2 components
    while len(nums) < 2:
        nums.append(0)
    return tuple(nums)

def is_newer_version(latest: str, current: str) -> bool:
    return parse_version_tuple(latest) > parse_version_tuple(current)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4: GRAPH & DIALOG WIDGETS
# ═══════════════════════════════════════════════════════════════════════════

class DailyPlanningDialog(QDialog):
    def __init__(self, incomplete_today_count, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Daily Planning")
        layout = QVBoxLayout(self)
        
        info_text = f"You have {incomplete_today_count} incomplete tasks from yesterday." if incomplete_today_count > 0 else "Ready for a fresh start!"
        layout.addWidget(QLabel(info_text))
        
        layout.addWidget(QLabel("How many tasks do you realistically want to focus on today?"))
        self.spin_box = QSpinBox()
        self.spin_box.setRange(0, 10)
        self.spin_box.setValue(3)
        layout.addWidget(self.spin_box)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

class MoodGraphWidget(QWidget):
    def __init__(self, state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = state
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"background-color: {GLASS_BG}; border-radius: 16px;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        moods = self.state.get("moods", [])
        mood_map = {m["date"]: m["value"] for m in moods}
        
        val_map = {"Low energy": 1, "Stressed": 1, "Okay": 2, "Motivated": 3, "Great": 4}
        
        today = date.today()
        days = 14
        bar_width = rect.width() / days
        max_h = rect.height() - 10
        
        painter.setPen(Qt.PenStyle.NoPen)
        
        for i in range(days):
            d = today - timedelta(days=(days - 1 - i))
            d_str = str(d)
            val_str = mood_map.get(d_str)
            score = val_map.get(val_str, 0)
            
            if score > 0:
                h = (score / 4) * max_h
                x = i * bar_width + 2
                y = rect.height() - h
                w = bar_width - 4
                
                color = QColor(GOLD)
                if score <= 1: color = QColor("#ff6b6b") # Red
                elif score == 2: color = QColor("#feca57") # Orange
                
                painter.setBrush(QBrush(color))
                painter.drawRoundedRect(QRectF(x, y, w, h), 4, 4)
            
            # Draw faint baseline
            painter.setBrush(QBrush(QColor(HOVER_BG)))
            painter.drawRect(QRectF(i * bar_width + 2, rect.height() - 2, bar_width - 4, 2))

class HabitGraphWidget(QWidget):
    def __init__(self, state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = state
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"background-color: {GLASS_BG}; border-radius: 16px;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        checks = self.state.get("habitChecks", {})
        habits = self.state.get("habits", [])
        active_count = len([h for h in habits if h.get("active", True)])
        if active_count == 0: active_count = 1

        today = date.today()
        days = 14
        bar_width = rect.width() / days
        max_h = rect.height() - 10
        
        painter.setPen(Qt.PenStyle.NoPen)

        for i in range(days):
            d = today - timedelta(days=(days - 1 - i))
            d_str = str(d)
            day_checks = checks.get(d_str, {})
            completed = sum(1 for v in day_checks.values() if v)
            
            ratio = completed / active_count
            h = ratio * max_h
            x = i * bar_width + 2
            y = rect.height() - h
            w = bar_width - 4
            
            painter.setBrush(QBrush(QColor(GOLD) if ratio == 1.0 else QColor(TEXT_GRAY)))
            if h > 0:
                painter.drawRoundedRect(QRectF(x, y, w, h), 4, 4)
            
            painter.setBrush(QBrush(QColor(HOVER_BG)))
            painter.drawRect(QRectF(i * bar_width + 2, rect.height() - 2, bar_width - 4, 2))

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5: LIST WIDGETS
# ═══════════════════════════════════════════════════════════════════════════

class TaskListWidget(QWidget):
    """Simple vertical task list for a given section."""

    def __init__(self, state: Dict[str, Any], section: str, save_callback, parent=None):
        super().__init__(parent)
        self.state = state
        self.section = section
        self._save_callback = save_callback
        self._focus_skip_count = 0
        self._highlight_timer = QTimer(self)
        
        # Session hint label (Today only)
        self.session_hint_label = QLabel("")
        self.session_hint_label.setStyleSheet(f"color: {GOLD}; font-style: italic; margin-top: 4px;")
        self.session_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.session_hint_label.hide()

        # Main layout for the widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        
        # Glass Card Frame
        self.card = QFrame()
        self.card.setObjectName("GlassCard")
        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        
        main_layout.addWidget(self.card)

        # Header row
        header = QHBoxLayout()
        lbl = QLabel(section)
        lbl.setObjectName("PageHeader")
        header.addWidget(lbl, 1)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 12px; background-color: {HOVER_BG}; border-radius: 10px; padding: 2px 8px;")
        header.addWidget(self.progress_label)

        # -- Today-specific controls --
        if section == "Today":
            self.mode_label = QLabel("")
            self.mode_label.setStyleSheet(f"color: {GOLD}; font-size: 11px; font-weight: bold; margin-left: 8px;")
            header.addWidget(self.mode_label)

            # Focus Mode Toggle
            self.focus_toggle = QPushButton("Focus")
            self.focus_toggle.setCheckable(True)
            self.focus_toggle.setFixedSize(50, 26)
            self.focus_toggle.setStyleSheet(f"background-color: {HOVER_BG}; color: {TEXT_WHITE}; border-radius: 8px; font-size: 11px;")
            self.focus_toggle.toggled.connect(self._toggle_focus_mode)
            header.addWidget(self.focus_toggle)

            self.btn_next = QPushButton("What next?")
            self.btn_next.setFixedSize(80, 26)
            self.btn_next.setStyleSheet(f"background-color: {HOVER_BG}; color: {GOLD}; font-weight: bold; border-radius: 8px; font-size: 11px;")
            self.btn_next.clicked.connect(self._suggest_next_task)
            header.addWidget(self.btn_next)
        else:
            self.btn_send_today = QPushButton("Move all to Today")
            self.btn_send_today.setFixedSize(110, 26)
            self.btn_send_today.setStyleSheet(f"background-color: {HOVER_BG}; color: {TEXT_WHITE}; border-radius: 8px; font-size: 11px;")
            self.btn_send_today.clicked.connect(self._move_all_to_today)
            header.addWidget(self.btn_send_today)

        self.menu_btn = QPushButton("...")
        self.menu_btn.setFixedSize(26, 26)
        self.menu_btn.clicked.connect(self._show_section_menu)
        header.addWidget(self.menu_btn)
        
        layout.addLayout(header)
        
        if section == "Today":
            
            # Overload Warning
            self.overload_frame = QFrame()
            self.overload_frame.setStyleSheet(f"background-color: rgba(200, 50, 50, 0.15); border-radius: 8px; border: 1px solid rgba(200, 50, 50, 0.3);")
            self.overload_frame.setVisible(False)
            ol_layout = QHBoxLayout(self.overload_frame)
            ol_layout.setContentsMargins(8, 4, 8, 4)
            self.ol_label = QLabel("That’s quite a lot for today.")
            self.ol_label.setStyleSheet("color: #ffaaaa; font-size: 12px;")
            self.ol_btn = QPushButton("Move 3 to This Week")
            self.ol_btn.setStyleSheet(f"background-color: rgba(200, 50, 50, 0.3); color: {TEXT_WHITE}; border: none; border-radius: 4px; padding: 4px;")
            self.ol_btn.clicked.connect(self._move_overload_tasks)
            ol_layout.addWidget(self.ol_label, 1)
            ol_layout.addWidget(self.ol_btn)
            layout.addWidget(self.overload_frame)

            # Focus Card (Hidden by default)
            self.focus_card = QFrame()
            self.focus_card.setVisible(False)
            self.focus_card.setStyleSheet(f"background-color: rgba(0,0,0,0.2); border: 1px solid {GOLD}; border-radius: 12px;")
            fc_layout = QVBoxLayout(self.focus_card)
            self.fc_label = QLabel("Focus Task")
            self.fc_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {TEXT_WHITE}; margin: 10px;")
            self.fc_label.setWordWrap(True)
            self.fc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fc_layout.addWidget(self.fc_label)
            
            fc_btns = QHBoxLayout()
            self.fc_done = QPushButton("Done")
            self.fc_done.setStyleSheet(f"background-color: {GOLD}; color: {DARK_BG}; font-weight: bold;")
            self.fc_done.clicked.connect(self._focus_done)
            self.fc_skip = QPushButton("Skip")
            self.fc_skip.clicked.connect(self._focus_skip)
            fc_btns.addWidget(self.fc_done)
            fc_btns.addWidget(self.fc_skip)
            fc_layout.addLayout(fc_btns)
            layout.addWidget(self.focus_card)
            
            layout.addWidget(self.session_hint_label)

        # Quick Add Row
        qa_layout = QHBoxLayout()
        self.quick_add_input = QLineEdit()
        self.quick_add_input.setPlaceholderText("Quick add...")
        self.quick_add_input.setStyleSheet(f"background-color: rgba(0,0,0,0.3); border: 1px solid {HOVER_BG}; border-radius: 6px; padding: 4px; color: {TEXT_WHITE};")
        self.quick_add_input.returnPressed.connect(self._on_quick_add)
        qa_layout.addWidget(self.quick_add_input, 1)

        if section == "Today":
            self.project_combo = QComboBox()
            self.project_combo.addItem("No Project", None)
            self.project_combo.setFixedWidth(100)
            self.project_combo.setStyleSheet(f"background-color: rgba(0,0,0,0.3); color: {TEXT_GRAY}; border: 1px solid {HOVER_BG}; border-radius: 6px;")
            qa_layout.addWidget(self.project_combo)

        layout.addLayout(qa_layout)

        self.tasks_list = QListWidget()
        self.tasks_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.tasks_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.tasks_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.tasks_list.setStyleSheet(f"""
            QListWidget {{ background-color: transparent; border: none; }}
            QListWidget::item {{ min-height: 36px; border-bottom: 1px solid rgba(255,255,255,0.05); }}
            QListWidget::item:hover {{ background-color: rgba(255,255,255,0.05); }}
        """)
        layout.addWidget(self.tasks_list, 1)
        
        # Empty State Label
        self.empty_label = QLabel("")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {TEXT_GRAY}; font-style: italic; margin-top: 20px;")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)
        
        # Transient label for feedback
        self.transient_label = QLabel("")
        self.transient_label.setStyleSheet(f"color: {GOLD}; font-style: italic; margin-top: 4px;")
        self.transient_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.transient_label.hide()
        layout.addWidget(self.transient_label)

        self.tasks_list.model().rowsMoved.connect(self._on_internal_reorder)
        self.refresh()

    def refresh(self) -> None:
        self.tasks_list.clear()
        # tasks_in_section already sorts by (completed, important, order)
        tasks = tasks_in_section(self.state, self.section)
        
        total = len(tasks)
        completed = len([t for t in tasks if t.get("completed")])
        self.progress_label.setText(f"{completed} / {total} done")

        # Update Mode Label in Header (Today only)
        if self.section == "Today" and self.window():
            mode = getattr(self.window(), "_current_mode", "")
            self.mode_label.setText(f"[{mode}]" if mode else "")

        # Refresh Project Combo if Today
        if self.section == "Today":
            current_data = self.project_combo.currentData()
            self.project_combo.blockSignals(True)
            self.project_combo.clear()
            self.project_combo.addItem("No Project", None)
            for p in self.state.get("projects", []):
                self.project_combo.addItem(p["name"], p["id"])
            if current_data:
                idx = self.project_combo.findData(current_data)
                if idx >= 0: self.project_combo.setCurrentIndex(idx)
            self.project_combo.blockSignals(False)
            
            # Overload Check
            mood = get_today_mood(self.state)
            val = mood.get("value", "") if mood else ""
            is_low = val in ("Low energy", "Stressed")
            open_tasks = total - completed
            
            if is_low and open_tasks > 7:
                self.overload_frame.setVisible(True)
            else:
                self.overload_frame.setVisible(False)

            # Update Focus Card if active
            if self.focus_toggle.isChecked():
                self._update_focus_card()
        
        # Empty State Logic
        if total == 0:
            self.tasks_list.setVisible(False)
            self.empty_label.setVisible(True)
            if self.section == "Today":
                self.empty_label.setText("No tasks in Today. Add one thing you’d like Future You to be grateful for.")
            elif self.section == "This Week":
                self.empty_label.setText("No tasks in This Week. Add things you’d like to get to sometime this week.")
            elif self.section == "Someday":
                self.empty_label.setText("No tasks in Someday. Capture long‑term ideas here without pressure.")
            else:
                self.empty_label.setText(f"Ready? Type above to add a task for {self.section}.")
        else:
            self.tasks_list.setVisible(True)
            self.empty_label.setVisible(False)

        for t in tasks:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, t.get("id"))

            row = QWidget()
            row.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            hl = QHBoxLayout(row)
            hl.setContentsMargins(6, 2, 6, 2)
            hl.setSpacing(6)

            chk = QPushButton("✔" if t.get("completed") else "")
            chk.setFixedSize(QSize(22, 22))
            chk.setCheckable(True)
            chk.setChecked(t.get("completed"))
            chk.setStyleSheet(f"""
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
            """)

            lbl = QLabel(t.get("text", ""))
            lbl.setWordWrap(True)
            if t.get("completed"):
                lbl.setStyleSheet(f"color: {TEXT_GRAY}; text-decoration: line-through;")
            elif t.get("important"):
                lbl.setStyleSheet(f"color: {GOLD}; font-weight: bold;")
            else:
                lbl.setStyleSheet(f"color: {TEXT_WHITE};")

            del_btn = QPushButton("×")
            del_btn.setFixedSize(QSize(24, 24))
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    color: {TEXT_GRAY};
                    font-weight: bold;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    color: {GOLD};
                }}
            """)

            hl.addWidget(chk)
            hl.addWidget(lbl, 1)
            hl.addWidget(del_btn)

            self.tasks_list.addItem(item)
            self.tasks_list.setItemWidget(item, row)

            chk.clicked.connect(lambda checked, tid=t.get("id"): self._on_toggle_task(tid))
            del_btn.clicked.connect(lambda checked=False, tid=t.get("id"): self._on_delete_task(tid))
            row.customContextMenuRequested.connect(
                lambda pos, tid=t.get("id"): self._show_task_menu(tid, row.mapToGlobal(pos))
            )

    def _on_quick_add(self) -> None:
        text = self.quick_add_input.text().strip()
        if not text: return
        
        pid = None
        if self.section == "Today":
            pid = self.project_combo.currentData()
            
        add_task(self.state, text=text, section=self.section, project_id=pid)
        self._save_callback()
        self.refresh()
        self.quick_add_input.clear()
        self.quick_add_input.setFocus()

    def _on_toggle_task(self, task_id: str) -> None:
        t = toggle_task_completed(self.state, task_id)
        # If completed, notify window to track session
        if t and t.get("completed") and self.window() and hasattr(self.window(), "record_task_completion"):
            self.window().record_task_completion()
        self._save_callback()
        self.refresh()

    def _on_delete_task(self, task_id: str) -> None:
        # Delegate to window for Undo capability
        if self.window() and hasattr(self.window(), "request_delete_task"):
            self.window().request_delete_task(task_id)
        else:
            delete_task(self.state, task_id)
            self._save_callback()
            self.refresh()

    def _on_internal_reorder(self, parent, start, end, dest, row):
        QTimer.singleShot(0, self._update_order_from_widget)

    def _update_order_from_widget(self):
        tasks_in_this_section = {t['id']: t for t in self.state['tasks'] if t['section'] == self.section}
        for i in range(self.tasks_list.count()):
            item = self.tasks_list.item(i)
            task_id = item.data(Qt.ItemDataRole.UserRole)
            if task_id in tasks_in_this_section:
                task = tasks_in_this_section[task_id]
                task['order'] = i
        self._save_callback()
    
    def _show_section_menu(self):
        menu = QMenu(self)
        mark_all_done = menu.addAction("Mark all done")
        clear_completed = menu.addAction("Clear completed tasks")
        
        send_completed_someday = None
        if self.section != "Someday":
            send_completed_someday = menu.addAction("Send completed to Someday")
            
        if self.section == "Someday":
            menu.addAction("Archive Someday tasks older than 30 days")
        action = menu.exec(self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft()))

        if action == mark_all_done:
            for task in tasks_in_section(self.state, self.section):
                if not task['completed']:
                    task['completed'] = True
                    task['updatedAt'] = now_iso()
            self._save_callback()
            self.refresh()
        elif action == clear_completed:
            self.state['tasks'] = [t for t in self.state['tasks'] if t.get('section') != self.section or not t.get('completed')]
            self._save_callback()
            self.refresh()
        elif send_completed_someday and action == send_completed_someday:
            for task in tasks_in_section(self.state, self.section):
                if task['completed']:
                    task['section'] = "Someday"
                    task['updatedAt'] = now_iso()
            self._save_callback()
            self.refresh()
        elif action and action.text() == "Archive Someday tasks older than 30 days":
            cutoff = datetime.now() - timedelta(days=30)
            for task in tasks_in_section(self.state, self.section):
                created = datetime.fromisoformat(task.get("createdAt", now_iso()))
                if created < cutoff and not task.get("completed"):
                    task["section"] = "Archived"
                    task['updatedAt'] = now_iso()
            self._save_callback()
            self.refresh()
    
    def _move_all_to_today(self):
        tasks = tasks_in_section(self.state, self.section)
        count = 0
        for t in tasks:
            if not t.get("completed"):
                t["section"] = "Today"
                t["updatedAt"] = now_iso()
                count += 1
        if count > 0:
            self._save_callback()
            self.refresh()
            self._show_transient_message(f"Moved {count} tasks to Today")

    def _move_overload_tasks(self):
        # Move 3 lowest priority tasks to This Week
        tasks = tasks_in_section(self.state, "Today")
        incomplete = [t for t in tasks if not t.get("completed")]
        # Sort: Not important first, then highest order (bottom of list)
        incomplete.sort(key=lambda t: (t.get("important", False), -t.get("order", 0)))
        
        moved = 0
        for t in incomplete[:3]:
            t["section"] = "This Week"
            t["updatedAt"] = now_iso()
            moved += 1
            
        if moved > 0:
            self._save_callback()
            self.refresh()
            self._show_transient_message(f"Moved {moved} tasks to This Week. Breathe.")

    def _toggle_focus_mode(self, checked):
        effect = QGraphicsOpacityEffect(self.tasks_list)
        effect.setOpacity(0.3 if checked else 1.0)
        self.tasks_list.setGraphicsEffect(effect)
        self.focus_card.setVisible(checked)
        if checked:
            self._update_focus_card()

    def _update_focus_card(self):
        tasks = tasks_in_section(self.state, "Today")
        incomplete = [t for t in tasks if not t.get("completed")]
        # Sort by priority
        incomplete.sort(key=lambda t: (not t.get("important", False), t.get("order", 0)))
        
        # Apply skip offset
        idx = self._focus_skip_count % len(incomplete) if incomplete else 0
        
        if incomplete:
            task = incomplete[idx]
            self.fc_label.setText(task["text"])
            self.fc_label.setProperty("taskId", task["id"])
        else:
            self.fc_label.setText("All done! 🎉")
            self.fc_label.setProperty("taskId", None)

    def _focus_done(self):
        tid = self.fc_label.property("taskId")
        if tid:
            self._on_toggle_task(tid) # This refreshes UI

    def _focus_skip(self):
        self._focus_skip_count += 1
        self._update_focus_card()

    def show_session_hint(self):
        self.session_hint_label.setText("Nice little focus streak. Maybe take a short break.")
        self.session_hint_label.show()
        QTimer.singleShot(5000, self.session_hint_label.hide)

    def _suggest_next_task(self):
        tasks = tasks_in_section(self.state, self.section)
        # Filter incomplete
        incomplete = [t for t in tasks if not t.get("completed")]
        if not incomplete:
            self._show_transient_message("Nothing urgent left for Today. You can rest or check Projects.")
            return
            
        # tasks_in_section already sorts by (completed, important, order).
        # So the first item in 'incomplete' is the highest priority.
        top = incomplete[0]
        
        self.scroll_to_task(top['id'])
        # No popup, just scroll and highlight
        # self._show_transient_message(f"A gentle next step: {top['text']}")

    def _show_transient_message(self, text):
        self.transient_label.setText(text)
        self.transient_label.show()
        QTimer.singleShot(3000, self.transient_label.hide)

    def scroll_to_task(self, task_id):
        for i in range(self.tasks_list.count()):
            item = self.tasks_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == task_id:
                self.tasks_list.scrollToItem(item)
                self.tasks_list.setCurrentItem(item)
                widget = self.tasks_list.itemWidget(item)
                if widget:
                    # Flash effect
                    widget.setStyleSheet(f"background-color: {HOVER_BG}; border: 1px solid {GOLD}; border-radius: 8px;")
                    QTimer.singleShot(500, lambda w=widget: w.setStyleSheet(f"background-color: transparent;"))
                break

    def _show_task_menu(self, task_id: str, global_pos) -> None:
        menu = QMenu(self)
        task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
        if not task: return

        is_important = task.get("important", False)
        act_rename = menu.addAction("Rename")
        act_important = menu.addAction("Unmark important" if is_important else "Mark as important")

        move_menu = menu.addMenu("Move to")
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
        if not action: return

        if action is act_rename:
            self._rename_task(task_id)
        elif action is act_important:
            self._set_task_important(task_id, not is_important)
        elif action.parent() is move_menu:
            self._move_task_section(task_id, action.text())
        elif action.parent() is proj_menu:
            self._assign_task_project(task_id, action.data())

    def _rename_task(self, task_id: str) -> None:
        task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
        if not task: return
        current_text = task.get("text", "")
        new_text, ok = QInputDialog.getText(self, "Rename task", "New name:", text=current_text)
        if ok and new_text.strip():
            task["text"] = new_text.strip()
            task["updatedAt"] = now_iso()
            self._save_callback()
            self.refresh()

    def _set_task_important(self, task_id: str, important: bool) -> None:
        task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
        if not task: return
        task["important"] = important
        task["updatedAt"] = now_iso()
        self._save_callback()
        self.refresh()

    def _move_task_section(self, task_id: str, new_section: str) -> None:
        task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
        if not task or new_section not in SECTIONS: return
        task["section"] = new_section
        task["updatedAt"] = now_iso()
        self._save_callback()
        self.refresh()

    def _assign_task_project(self, task_id: str, project_id: Optional[str]) -> None:
        task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
        if not task: return
        task["projectId"] = project_id
        task["updatedAt"] = now_iso()
        self._save_callback()
        self.refresh()

    def dropEvent(self, event) -> None:
        super().dropEvent(event)
        tasks_in_this_section = {t['id']: t for t in self.state['tasks'] if t['section'] == self.section}
        for i in range(self.tasks_list.count()):
            item = self.tasks_list.item(i)
            task_id = item.data(Qt.ItemDataRole.UserRole)
            if task_id in tasks_in_this_section:
                task = tasks_in_this_section[task_id]
                if task.get("order") != i:
                    task['order'] = i
                    task['updatedAt'] = now_iso()
        self._save_callback()

class ProjectTaskListWidget(QWidget):
    """Task list widget specifically for projects with bulk actions."""

    def __init__(self, state: Dict[str, Any], save_callback, parent=None):
        super().__init__(parent)
        self.state = state
        self._save_callback = save_callback
        self.project_id = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Actions row
        actions_layout = QHBoxLayout()
        self.btn_send_today = QPushButton("Send selected to Today")
        self.btn_send_one = QPushButton("Send one to Today")
        self.btn_mark_all = QPushButton("Mark all done")
        actions_layout.addWidget(self.btn_send_today)
        actions_layout.addWidget(self.btn_send_one)
        actions_layout.addWidget(self.btn_mark_all)
        actions_layout.addStretch(1)
        layout.addLayout(actions_layout)

        # Quick add
        self.quick_add_input = QLineEdit()
        self.quick_add_input.setPlaceholderText("Add task to project...")
        self.quick_add_input.setStyleSheet(f"background-color: rgba(0,0,0,0.3); border: 1px solid {HOVER_BG}; border-radius: 6px; padding: 4px; color: {TEXT_WHITE};")
        self.quick_add_input.returnPressed.connect(self._on_quick_add)
        layout.addWidget(self.quick_add_input)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 12px; margin-bottom: 4px;")
        layout.addWidget(self.info_label)

        # List
        self.tasks_list = QListWidget()
        self.tasks_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.tasks_list.setStyleSheet(f"background-color: transparent; border: none;")
        layout.addWidget(self.tasks_list, 1)
        self.tasks_list.itemSelectionChanged.connect(self._on_selection_changed)
        
        self.empty_label = QLabel("No tasks in this project.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {TEXT_GRAY}; font-style: italic;")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        self.btn_send_one.clicked.connect(self._on_send_one_today)
        self.btn_send_today.clicked.connect(self._on_send_selected_today)
        self.btn_mark_all.clicked.connect(self._on_mark_all_done)

    def set_project(self, project_id: Optional[str]):
        self.project_id = project_id
        self.refresh()

    def _on_selection_changed(self):
        self.btn_send_today.setEnabled(bool(self.tasks_list.selectedItems()))

    def refresh(self):
        self.tasks_list.clear()
        if not self.project_id:
            self.quick_add_input.setEnabled(False)
            self.btn_send_today.setEnabled(False)
            self.btn_send_one.setEnabled(False)
            self.btn_mark_all.setEnabled(False)
            self.info_label.setText("")
            self.tasks_list.setVisible(False)
            self.empty_label.setVisible(False)
            return

        self.quick_add_input.setEnabled(True)
        self.btn_send_one.setEnabled(True)
        self.btn_mark_all.setEnabled(True)

        tasks = tasks_for_project(self.state, self.project_id)
        # Sort by completed (bottom), then order
        tasks.sort(key=lambda t: (t.get("completed", False), t.get("order", 0)))
        
        open_count = len([t for t in tasks if not t.get("completed")])
        done_count = len(tasks) - open_count 
        today_count = len([t for t in tasks if t.get("section") == "Today" and not t.get("completed")])
        
        self.info_label.setText(f"{open_count} open · {done_count} done · {today_count} in Today")
        
        if not tasks:
            self.tasks_list.setVisible(False)
            self.empty_label.setVisible(True)
            self.empty_label.setText("No tasks here yet. Add one above to get started.")
            self.btn_send_today.setEnabled(False)
            self.btn_send_one.setEnabled(False)
            self.btn_mark_all.setEnabled(False)
        else:
            self.tasks_list.setVisible(True)
            self.empty_label.setVisible(False)
            self.btn_send_one.setEnabled(True)
            self.btn_mark_all.setEnabled(True)
            self._on_selection_changed()

        for t in tasks:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, t.get("id"))

            row = QWidget()
            hl = QHBoxLayout(row)
            hl.setContentsMargins(6, 2, 6, 2)
            hl.setSpacing(6)

            chk = QPushButton("✔" if t.get("completed") else "")
            chk.setFixedSize(QSize(22, 22))
            chk.setCheckable(True)
            chk.setChecked(t.get("completed"))
            chk.setStyleSheet(f"""
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
            """)

            lbl = QLabel(t.get("text", ""))
            lbl.setWordWrap(True)
            if t.get("completed"):
                lbl.setStyleSheet(f"color: {TEXT_GRAY}; text-decoration: line-through;")
            else:
                lbl.setStyleSheet(f"color: {TEXT_WHITE};")

            del_btn = QPushButton("×")
            del_btn.setFixedSize(QSize(24, 24))
            del_btn.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {TEXT_GRAY}; font-weight: bold; font-size: 14px; }} QPushButton:hover {{ color: {GOLD}; }}")

            hl.addWidget(chk)
            hl.addWidget(lbl, 1)
            hl.addWidget(del_btn)

            self.tasks_list.addItem(item)
            self.tasks_list.setItemWidget(item, row)
            
            chk.clicked.connect(lambda checked, tid=t.get("id"): self._on_toggle_task(tid))
            del_btn.clicked.connect(lambda checked=False, tid=t.get("id"): self._on_delete_task(tid))

    def _on_quick_add(self):
        text = self.quick_add_input.text().strip()
        if not text or not self.project_id: return
        add_task(self.state, text=text, section="Someday", project_id=self.project_id)
        self._save_callback()
        self.refresh()
        self.quick_add_input.clear()

    def _on_toggle_task(self, task_id):
        t = toggle_task_completed(self.state, task_id)
        if t and t.get("completed") and self.window() and hasattr(self.window(), "record_task_completion"):
            self.window().record_task_completion()
        self._save_callback()
        self.refresh()

    def _on_delete_task(self, task_id):
        if self.window() and hasattr(self.window(), "request_delete_task"):
            self.window().request_delete_task(task_id)
        else:
            delete_task(self.state, task_id)
            self._save_callback()
            self.refresh()

    def _on_send_selected_today(self):
        for item in self.tasks_list.selectedItems():
            tid = item.data(Qt.ItemDataRole.UserRole)
            for t in self.state["tasks"]:
                if t["id"] == tid:
                    t["section"] = "Today"
                    t["updatedAt"] = now_iso()
        self._save_callback()
        self.refresh()

    def _on_send_one_today(self):
        tasks = tasks_for_project(self.state, self.project_id)
        candidates = [t for t in tasks if not t.get("completed") and t.get("section") != "Today"]
        if candidates:
            # Pick highest priority/order
            candidates.sort(key=lambda t: (t.get("order", 0)))
            t = candidates[0]
            t["section"] = "Today"
            t["updatedAt"] = now_iso()
            self._save_callback()
        self.refresh()

    def _on_mark_all_done(self):
        reply = QMessageBox.question(self, "Mark all done", "Mark all tasks in this project as completed?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        tasks = tasks_for_project(self.state, self.project_id)
        for t in tasks:
            if not t["completed"]:
                t["completed"] = True
                t["updatedAt"] = now_iso()
        self._save_callback()
        self.refresh()

    def _show_task_menu(self, task_id: str, global_pos) -> None:
        menu = QMenu(self)
        task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
        if not task: return

        is_important = task.get("important", False)
        act_rename = menu.addAction("Rename")
        act_important = menu.addAction("Unmark important" if is_important else "Mark as important")

        move_menu = menu.addMenu("Move to")
        for sec in ["Today", "Tomorrow", "This Week", "Someday"]:
            move_menu.addAction(sec)

        action = menu.exec(global_pos)
        if not action: return

        if action is act_rename:
            self._rename_task(task_id)
        elif action is act_important:
            self._set_task_important(task_id, not is_important)
        elif action.parent() is move_menu:
            self._move_task_section(task_id, action.text())

    def _rename_task(self, task_id: str) -> None:
        task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
        if not task: return
        current_text = task.get("text", "")
        new_text, ok = QInputDialog.getText(self, "Rename task", "New name:", text=current_text)
        if ok and new_text.strip():
            task["text"] = new_text.strip()
            task["updatedAt"] = now_iso()
            self._save_callback()
            self.refresh()

    def _set_task_important(self, task_id: str, important: bool) -> None:
        task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
        if not task: return
        task["important"] = important
        task["updatedAt"] = now_iso()
        self._save_callback()
        self.refresh()

    def _move_task_section(self, task_id: str, new_section: str) -> None:
        task = next((t for t in self.state.get("tasks", []) if t.get("id") == task_id), None)
        if not task or new_section not in SECTIONS: return
        task["section"] = new_section
        task["updatedAt"] = now_iso()
        self._save_callback()
        self.refresh()

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6: HUB WINDOW
# ═══════════════════════════════════════════════════════════════════════════

class HubWindow(QMainWindow):
    """Main planning & mental health hub."""

    def __init__(self, state: Dict[str, Any], paths: Dict[str, str]):
        super().__init__()
        self.state = state
        self.paths = paths
        self._last_deleted_task = None
        self._current_mode = "Standard"
        self._consecutive_completions = 0
        self._last_completion_time = 0.0

        geom = self.state.get("ui_geometry")
        if geom:
            self.setGeometry(*geom)

        self.setWindowTitle(f"{APP_NAME} Hub v{APP_VERSION}")
        self._save_timer = QTimer(self)
        self._save_timer.setInterval(800)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._do_save)

        self._build_ui()
        
        # Apply shadows to cards after UI build
        for widget in self.findChildren(QFrame, "GlassCard"):
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(0, 0, 0, 60))
            shadow.setOffset(0, 4)
            widget.setGraphicsEffect(shadow)

        self._refresh_home()

        # Check for updates silently in the background
        self._check_updates_async()
        self._run_daily_planning()
        
        # Initial soft fade-in
        self._animate_page_in()

        # Keyboard Shortcuts
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self._switch_page(self.page_home))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self._switch_page(self.page_today))
        QShortcut(QKeySequence("Ctrl+3"), self, lambda: self._switch_page(self.page_week))
        QShortcut(QKeySequence("Ctrl+4"), self, lambda: self._switch_page(self.page_someday))
        QShortcut(QKeySequence("Ctrl+5"), self, lambda: self._switch_page(self.page_projects))
        QShortcut(QKeySequence("Ctrl+6"), self, lambda: self._switch_page(self.page_stats))
        QShortcut(QKeySequence("Ctrl+T"), self, lambda: self._switch_page(self.page_today))
        QShortcut(QKeySequence("Ctrl+P"), self, lambda: self._switch_page(self.page_projects))


    # ────────────────────────────────────────────────────────────────────
    # UI construction
    # ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {DARK_BG};
            }}
            QLabel#TitleLabel {{
                color: {GOLD};
                font-size: 20px;
                font-weight: bold;
            }}
            QLabel {{
                color: {TEXT_WHITE};
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
            QLabel#PageHeader {{
                font-size: 24px;
                font-weight: bold;
                color: {GOLD};
                background: transparent;
            }}
            QLabel#SectionHeader {{
                font-size: 16px;
                font-weight: bold;
                color: {TEXT_WHITE};
                margin-top: 8px;
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
        """)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # Left navigation
        nav_frame = QFrame()
        nav_frame.setObjectName("NavBar")
        nav_frame.setFixedWidth(180)
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(10, 20, 10, 20)
        nav_layout.setSpacing(8)

        title = QLabel(f"{APP_NAME} Hub")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(title)

        nav_layout.addSpacing(6)

        self.btn_home = QPushButton("🏠 Home")
        self.btn_today = QPushButton("📅 Today")
        self.btn_week = QPushButton("🗓 This Week")
        self.btn_someday = QPushButton("🌙 Someday")
        self.btn_projects = QPushButton("📁 Projects")
        self.btn_stats = QPushButton("📊 Stats")

        for btn in [
            self.btn_home,
            self.btn_today,
            self.btn_week,
            self.btn_someday,
            self.btn_projects,
            self.btn_stats,
        ]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(32)
            nav_layout.addWidget(btn)

        self.btn_check_updates = QPushButton("🔄 Check updates")
        self.btn_check_updates.setCursor(Qt.CursorShape.PointingHandCursor)
        nav_layout.addWidget(self.btn_check_updates)

        nav_layout.addStretch(1)

        self.btn_quit = QPushButton("Exit Hub")
        self.btn_quit.setCursor(Qt.CursorShape.PointingHandCursor)
        nav_layout.addWidget(self.btn_quit)

        root.addWidget(nav_frame)

        # Right stacked pages
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        # Home page
        self.page_home = QWidget()
        home_layout = QVBoxLayout(self.page_home)
        home_layout.setContentsMargins(12, 12, 12, 12)
        home_layout.setSpacing(16)

        # -- Card 1: Check-in --
        card_checkin = QFrame()
        card_checkin.setObjectName("GlassCard")
        l_checkin = QVBoxLayout(card_checkin)
        
        lbl_ci = QLabel("Today Check‑In")
        lbl_ci.setObjectName("PageHeader")
        l_checkin.addWidget(lbl_ci)

        mood_row = QHBoxLayout()
        self.mood_combo = QComboBox()
        self.mood_combo.addItems(MOOD_OPTIONS)
        self.mood_save_btn = QPushButton("Save mood")
        mood_row.addWidget(self.mood_combo, 1)
        mood_row.addWidget(self.mood_save_btn)
        l_checkin.addLayout(mood_row)

        self.mood_note = QTextEdit()
        self.mood_note.setPlaceholderText("Optional: write a few words about your day.")
        self.mood_note.setFixedHeight(60)
        l_checkin.addWidget(self.mood_note)

        self.mood_message = QLabel("")
        self.mood_message.setWordWrap(True)
        self.mood_message.setStyleSheet(f"color: {TEXT_GRAY};")
        l_checkin.addWidget(self.mood_message)
        
        home_layout.addWidget(card_checkin)

        # -- Onboarding Card (Conditional) --
        self.card_onboarding = QFrame()
        self.card_onboarding.setObjectName("GlassCard")
        self.card_onboarding.setVisible(False)
        l_onboard = QVBoxLayout(self.card_onboarding)
        l_onboard.addWidget(QLabel("Start here:"))
        self.lbl_ob_mood = QLabel("○ Log how you feel")
        self.lbl_ob_task = QLabel("○ Add one task for Today")
        l_onboard.addWidget(self.lbl_ob_mood)
        l_onboard.addWidget(self.lbl_ob_task)
        home_layout.addWidget(self.card_onboarding)

        # -- Weekly Reset Card --
        self.card_weekly = QFrame()
        self.card_weekly.setObjectName("GlassCard")
        self.card_weekly.setVisible(False)
        l_weekly = QVBoxLayout(self.card_weekly)
        l_weekly.addWidget(QLabel("Weekly Reset: Pick up to 3 priorities"))
        
        self.weekly_inputs = []
        for i in range(3):
            inp = QLineEdit()
            inp.setPlaceholderText(f"Priority {i+1}")
            inp.setStyleSheet(f"background-color: rgba(0,0,0,0.3); border: 1px solid {HOVER_BG}; border-radius: 6px; padding: 4px; color: {TEXT_WHITE};")
            l_weekly.addWidget(inp)
            self.weekly_inputs.append(inp)
            
        btn_save_weekly = QPushButton("Set Focus")
        btn_save_weekly.clicked.connect(self._save_weekly_focus)
        l_weekly.addWidget(btn_save_weekly)
        home_layout.addWidget(self.card_weekly)

        # -- Someday Suggestion Card --
        self.card_someday_suggestion = QFrame()
        self.card_someday_suggestion.setObjectName("GlassCard")
        self.card_someday_suggestion.setVisible(False)
        l_someday = QVBoxLayout(self.card_someday_suggestion)
        self.lbl_someday_text = QLabel("")
        self.lbl_someday_text.setWordWrap(True)
        l_someday.addWidget(self.lbl_someday_text)
        h_someday = QHBoxLayout()
        btn_sd_move = QPushButton("Move to Today")
        btn_sd_move.clicked.connect(self._move_someday_suggestion)
        btn_sd_skip = QPushButton("Skip")
        btn_sd_skip.clicked.connect(lambda: self.card_someday_suggestion.hide())
        h_someday.addWidget(btn_sd_move)
        h_someday.addWidget(btn_sd_skip)
        l_someday.addLayout(h_someday)
        home_layout.addWidget(self.card_someday_suggestion)

        # -- Card 2: At a glance --
        card_glance = QFrame()
        card_glance.setObjectName("GlassCard")
        l_glance = QVBoxLayout(card_glance)
        
        lbl_gl = QLabel("Today at a glance")
        lbl_gl.setObjectName("PageHeader")
        l_glance.addWidget(lbl_gl)

        # Today counts text
        self.home_counts_label = QLabel("")
        self.home_counts_label.setStyleSheet(f"color: {TEXT_WHITE}; font-weight: bold;")
        l_glance.addWidget(self.home_counts_label)

        # Mode label
        self.home_mode_label = QLabel("")
        self.home_mode_label.setStyleSheet(f"color: {GOLD}; font-size: 12px;")
        l_glance.addWidget(self.home_mode_label)

        self.home_glance_list = QListWidget()
        self.home_glance_list.setFixedHeight(100)
        self.home_glance_list.setStyleSheet(f"""
            QListWidget {{ background-color: transparent; border: none; }}
            QListWidget::item {{ border-bottom: 1px solid rgba(255,255,255,0.05); padding: 4px; }}
            QListWidget::item:hover {{ background-color: rgba(255,255,255,0.05); }}
        """)
        self.home_glance_list.itemClicked.connect(self._on_glance_clicked)
        l_glance.addWidget(self.home_glance_list)
        
        # Suggestion Label
        self.suggestion_label = QLabel("")
        self.suggestion_label.setWordWrap(True)
        self.suggestion_label.setStyleSheet(f"color: {TEXT_GRAY}; font-style: italic; margin-top: 8px;")
        l_glance.addWidget(self.suggestion_label)
        
        self.home_stats_label = QLabel("")
        self.home_stats_label.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 12px; margin-top: 4px;")
        l_glance.addWidget(self.home_stats_label)
        
        # Weekly Strip
        self.weekly_strip = QHBoxLayout()
        l_glance.addLayout(self.weekly_strip)

        home_layout.addWidget(card_glance)

        # -- Bottom: Quote & Links --
        spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        home_layout.addItem(spacer)

        self.quote_label = QLabel("")
        self.quote_label.setWordWrap(True)
        self.quote_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.quote_label.setStyleSheet(f"color: {TEXT_GRAY}; font-style: italic;")
        home_layout.addWidget(self.quote_label)
        
        # Quick Links
        quick_links_layout = QHBoxLayout()
        btn_open_today = QPushButton("Open Today List")
        btn_open_projects = QPushButton("Open Projects")
        btn_open_today.clicked.connect(lambda: self._switch_page(self.page_today))
        btn_open_projects.clicked.connect(lambda: self._switch_page(self.page_projects))
        quick_links_layout.addStretch(1)
        quick_links_layout.addWidget(btn_open_today)
        quick_links_layout.addWidget(btn_open_projects)
        quick_links_layout.addStretch(1)
        home_layout.addLayout(quick_links_layout)

        # Today page
        self.page_today = TaskListWidget(self.state, "Today", self._schedule_save)

        # This Week page
        self.page_week = TaskListWidget(self.state, "This Week", self._schedule_save)

        # Someday page
        self.page_someday = TaskListWidget(self.state, "Someday", self._schedule_save)

        # Projects page
        self.page_projects = QWidget()
        proj_layout = QVBoxLayout(self.page_projects)
        proj_layout.setContentsMargins(12, 12, 12, 12)
        proj_layout.setSpacing(10)

        # Split Layout
        content_proj = QHBoxLayout()
        proj_layout.addLayout(content_proj, 1)

        # Left Card: List
        card_plist = QFrame()
        card_plist.setObjectName("GlassCard")
        card_plist.setFixedWidth(280)
        l_plist = QVBoxLayout(card_plist)
        
        l_plist.addWidget(QLabel("Projects"))
        
        self.project_list = QListWidget()
        self.project_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        l_plist.addWidget(self.project_list, 1)
        
        self.empty_projects_label = QLabel("You can create your first project with the 'New' button.")
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
        
        content_proj.addWidget(card_plist)

        # Right Card: Tasks
        self.project_detail = QFrame()
        self.project_detail.setObjectName("GlassCard")
        project_detail_layout = QVBoxLayout(self.project_detail)
        
        self.project_detail_title = QLabel("Select a project")
        self.project_detail_title.setObjectName("PageHeader")
        project_detail_layout.addWidget(self.project_detail_title)
        
        self.project_task_widget = ProjectTaskListWidget(self.state, self._schedule_save)
        project_detail_layout.addWidget(self.project_task_widget)

        content_proj.addWidget(self.project_detail, 1)

        # Stats & Habits page
        self.page_stats = QWidget()
        stats_layout = QVBoxLayout(self.page_stats)
        stats_layout.setContentsMargins(12, 12, 12, 12)
        stats_layout.setSpacing(10)

        # Top Card: Summary
        card_stats_top = QFrame()
        card_stats_top.setObjectName("GlassCard")
        l_stop = QVBoxLayout(card_stats_top)
        
        lbl_stats = QLabel("Stats & Habits")
        lbl_stats.setObjectName("PageHeader")
        l_stop.addWidget(lbl_stats)
        self.stats_summary_label = QLabel("")
        self.stats_summary_label.setWordWrap(True)
        l_stop.addWidget(self.stats_summary_label)
        stats_layout.addWidget(card_stats_top)

        # Middle: Graphs
        graphs_layout = QHBoxLayout()
        
        card_mood = QFrame()
        card_mood.setObjectName("GlassCard")
        l_mood = QVBoxLayout(card_mood)
        lbl_mood = QLabel("Mood History")
        lbl_mood.setObjectName("SectionHeader")
        l_mood.addWidget(lbl_mood)
        self.mood_graph = MoodGraphWidget(self.state)
        l_mood.addWidget(self.mood_graph)
        graphs_layout.addWidget(card_mood)
        
        card_habit = QFrame()
        card_habit.setObjectName("GlassCard")
        l_habit = QVBoxLayout(card_habit)
        lbl_habit = QLabel("Habit Consistency")
        lbl_habit.setObjectName("SectionHeader")
        l_habit.addWidget(lbl_habit)
        self.habit_graph = HabitGraphWidget(self.state)
        l_habit.addWidget(self.habit_graph)
        graphs_layout.addWidget(card_habit)
        
        stats_layout.addLayout(graphs_layout)

        # Bottom: Habits List
        card_habits = QFrame()
        card_habits.setObjectName("GlassCard")
        l_habits = QVBoxLayout(card_habits)
        
        habits_title = QLabel("Today’s habits")
        habits_title.setObjectName("SectionHeader")
        l_habits.addWidget(habits_title)
        
        self.habit_counter_label = QLabel("")
        self.habit_counter_label.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 12px; margin-bottom: 4px;")
        l_habits.addWidget(self.habit_counter_label)

        self.habits_list = QListWidget()
        l_habits.addWidget(self.habits_list, 1)

        self.habit_message = QLabel("")
        self.habit_message.setWordWrap(True)
        self.habit_message.setStyleSheet(f"color: {TEXT_GRAY}; font-style: italic;")
        l_habits.addWidget(self.habit_message)
        
        stats_layout.addWidget(card_habits, 1)

        # Add all pages to stacked widget
        self.stack.addWidget(self.page_home)
        self.stack.addWidget(self.page_today)
        self.stack.addWidget(self.page_week)
        self.stack.addWidget(self.page_someday)
        self.stack.addWidget(self.page_projects)
        self.stack.addWidget(self.page_stats)

        # -- Undo Toast (Overlay) --
        self.toast_frame = QFrame(self)
        self.toast_frame.setStyleSheet(f"background-color: {CARD_BG}; border: 1px solid {GOLD}; border-radius: 8px;")
        self.toast_frame.setVisible(False)
        # Position it at bottom center
        self.toast_layout = QHBoxLayout(self.toast_frame)
        self.toast_layout.setContentsMargins(12, 8, 12, 8)
        self.lbl_toast = QLabel("Task deleted")
        self.btn_undo = QPushButton("Undo")
        self.btn_undo.setStyleSheet(f"background-color: {HOVER_BG}; color: {GOLD}; border: none; font-weight: bold;")
        self.btn_undo.clicked.connect(self._undo_delete)
        self.toast_layout.addWidget(self.lbl_toast)
        self.toast_layout.addWidget(self.btn_undo)
        

        # Connect navigation
        self.btn_home.clicked.connect(lambda: self._switch_page(self.page_home))
        self.btn_today.clicked.connect(lambda: self._switch_page(self.page_today))
        self.btn_week.clicked.connect(lambda: self._switch_page(self.page_week))
        self.btn_someday.clicked.connect(lambda: self._switch_page(self.page_someday))
        self.btn_projects.clicked.connect(lambda: self._switch_page(self.page_projects))
        self.btn_stats.clicked.connect(lambda: self._switch_page(self.page_stats))
        self.btn_quit.clicked.connect(self.close)

        self.mood_save_btn.clicked.connect(self._on_save_mood)

        # Projects signals
        self.btn_add_project.clicked.connect(self._on_add_project)
        self.project_list.itemSelectionChanged.connect(self._on_project_selected)
        self.btn_rename_project.clicked.connect(self._on_rename_project)
        self.btn_delete_project.clicked.connect(self._on_delete_project)
        self.btn_check_updates.clicked.connect(self._check_updates_async)

    def resizeEvent(self, event):
        # Reposition toast
        if hasattr(self, "toast_frame"):
            w = self.width()
            h = self.height()
            self.toast_frame.setGeometry(w // 2 - 100, h - 60, 200, 40)
        super().resizeEvent(event)

    def _make_placeholder_page(self, text: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        layout.addStretch(1)
        return page

    # ────────────────────────────────────────────────────────────────────
    # Navigation & updates
    # ────────────────────────────────────────────────────────────────────
    
    def _animate_page_in(self):
        effect = QGraphicsOpacityEffect(self.stack)
        self.stack.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: self.stack.setGraphicsEffect(None))
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _switch_page(self, page: QWidget) -> None:
        if self.stack.currentWidget() == page:
            return

        self.stack.setCurrentWidget(page)
        self._animate_page_in()

        if page is self.page_home:
            self._refresh_home()
        elif isinstance(page, TaskListWidget):
            # Today, Week, Someday are TaskListWidgets
            page.refresh()
            # If it's Today, maybe check if we should suggest something?
            # if page is self.page_today:
            #     pass
        elif page is self.page_projects:
            self._refresh_projects()
        elif page is self.page_stats:
            self._refresh_stats_and_habits()

    def _determine_mode(self) -> str:
        mood = get_today_mood(self.state)
        val = mood.get("value", "") if mood else ""
        counts = count_today_tasks(self.state)
        done = counts["completed"]
        total = counts["total"]
        now = datetime.now()

        # Recovery
        if val in ("Low energy", "Stressed"):
            return "Recovery"
        if not mood and done == 0 and now.hour >= 14:
            return "Recovery" # Late start, be gentle

        # Wrap-up
        if now.hour >= 18:
             if total > 0 and (done / total > 0.8):
                 return "Wrap-up"
             if total == 0:
                 return "Wrap-up"

        # Focus
        if val in ("Motivated", "Great") and total > 3:
            return "Focus"
        
        return "Standard"

    def _refresh_home(self) -> None:
        # Mood
        mood = get_today_mood(self.state)
        mood_val = "Not set"
        if mood:
            value = mood.get("value", "Okay")
            note = mood.get("note", "")
            idx = self.mood_combo.findText(value)
            if idx >= 0:
                self.mood_combo.setCurrentIndex(idx)
            else:
                self.mood_combo.setCurrentIndex(0)
        self.mood_note.setPlainText(note)
        self.mood_message.setText(self._mood_message_for_value(value))
        mood_val = value
        else:
            self.mood_combo.setCurrentIndex(0)
            self.mood_note.setPlainText("")
            self.mood_message.setText("There are good days and bad days. Logging how you feel is a good start.")
        
        # Mode
        mode = self._determine_mode()
        self._current_mode = mode
        
        mode_desc = "Standard – steady progress."
        if mode == "Recovery": mode_desc = "Recovery – go gently, one tiny task is enough."
        elif mode == "Focus": mode_desc = "Focus – you have energy, pick one priority."
        elif mode == "Wrap-up": mode_desc = "Wrap-up – close your loops and rest."
        
        self.home_mode_label.setText(f"Today mode: {mode_desc}")

        # Today at a glance
        self.home_glance_list.clear()
        top_today_tasks = tasks_in_section(self.state, "Today")[:3]
        if not top_today_tasks:
            item = QListWidgetItem("No tasks for today. You can keep it light.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.home_glance_list.addItem(item)
        else:
            for task in top_today_tasks:
                icon = "🔥" if task.get("important") else "●"
                text = f"{icon} {task['text']}"
                item = QListWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, task['id'])
                if task.get("important"):
                    item.setForeground(QColor(GOLD))
                self.home_glance_list.addItem(item)

        # Today summary
        counts = count_today_tasks(self.state)
        total = counts["total"]
        done = counts["completed"]
        self.home_counts_label.setText(f"Today: {total} planned · {done} done · Mood: {mood_val}")
        
        stats = self.state.get("stats", {})
        planned = stats.get("plannedTasksToday", 0)
        streak = stats.get("currentStreak", 0)
        self.home_stats_label.setText(f"Streak: {streak} days · Planned tasks: {planned}")

        # Quote (simple deterministic choice)
        idx = hash(today_str()) % len(MOTIVATIONAL_QUOTES)
        self.quote_label.setText(MOTIVATIONAL_QUOTES[idx])

        # Suggestion Logic
        suggestion = "Suggestion: "
        if mode == "Recovery":
            suggestion += "Pick the easiest task and just do that."
        elif mode == "Focus":
            suggestion += "Tackle your most important task now."
        elif mode == "Wrap-up":
            suggestion += "Review what you did and plan for tomorrow."
        else:
            if total == 0:
                suggestion += "Add one small task to get started."
            elif done == 0:
                suggestion += "Start with the first item on your list."
            else:
                suggestion += "Keep going, or take a break if needed."
            
        # Easter egg chance
        if random.random() < 0.12: # ~1 in 8
            eggs = ["Hydration side quest: drink water before your next task.", "Micro‑stretch break: 20 seconds, then come back."]
            suggestion = random.choice(eggs)
            
        self.suggestion_label.setText(f"Suggestion: {suggestion}")

        # Time of day copy refinement
        # (Removed summary_label, so removing tooltips)

        # Onboarding Logic
        has_tasks = len(self.state.get("tasks", [])) > 0
        has_mood = len(self.state.get("moods", [])) > 0
        
        if not has_tasks or not has_mood:
            self.card_onboarding.setVisible(True)
            self.lbl_ob_mood.setText("✔ Log how you feel" if has_mood else "○ Log how you feel")
            self.lbl_ob_mood.setStyleSheet(f"color: {GOLD if has_mood else TEXT_WHITE}")
            self.lbl_ob_task.setText("✔ Add one task" if has_tasks else "○ Add one task")
            self.lbl_ob_task.setStyleSheet(f"color: {GOLD if has_tasks else TEXT_WHITE}")
        else:
            self.card_onboarding.setVisible(False)

        # Weekly Reset Logic
        stats = self.state.get("stats", {})
        last_reset = stats.get("lastWeeklyReset")
        today = date.today()
        is_monday = today.weekday() == 0
        
        show_weekly = False
        if is_monday and last_reset != str(today):
            show_weekly = True
        elif not stats.get("weeklyFocus"):
            show_weekly = True # Prompt if empty
            
        self.card_weekly.setVisible(show_weekly)
        if show_weekly:
            # Pre-fill if existing
            current_focus = stats.get("weeklyFocus", [])
            for i, inp in enumerate(self.weekly_inputs):
                if i < len(current_focus): inp.setText(current_focus[i])

        # Someday Suggestion Logic
        # Show only if not showing weekly reset to avoid clutter
        if not show_weekly and random.random() < 0.3: # 30% chance on refresh
            someday_tasks = tasks_in_section(self.state, "Someday")
            if someday_tasks:
                # Pick oldest
                someday_tasks.sort(key=lambda t: t.get("createdAt", now_iso()))
                task = someday_tasks[0]
                self.lbl_someday_text.setText(f"Optional idea from Someday:\n'{task['text']}'")
                self.lbl_someday_text.setProperty("taskId", task["id"])
                self.card_someday_suggestion.setVisible(True)
            else:
                self.card_someday_suggestion.setVisible(False)
        else:
            self.card_someday_suggestion.setVisible(False)

        # Weekly Strip
        # Clear old
        while self.weekly_strip.count():
            child = self.weekly_strip.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        today = date.today()
        moods = {m["date"]: m["value"] for m in self.state.get("moods", [])}
        
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            d_str = str(d)
            
            lbl = QLabel()
            lbl.setFixedSize(24, 24)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            m_val = moods.get(d_str)
            color = GOLD if m_val in ("Motivated", "Great") else (TEXT_GRAY if not m_val else "#ff6b6b")
            lbl.setStyleSheet(f"background-color: {color}; border-radius: 12px; font-size: 10px; color: {DARK_BG}; font-weight: bold;")
            lbl.setText(d.strftime("%a")[0])
            self.weekly_strip.addWidget(lbl)
        self.weekly_strip.addStretch()

        # Welcome back message
        last_opened = self.state.get("lastOpened", today_str())
        if last_opened < today_str():
            diff = (today - date.fromisoformat(last_opened)).days
            if diff > 1:
                self.mood_message.setText(f"Welcome back. You’ve been away for {diff} days; we’ll keep it gentle.")

    def _save_weekly_focus(self):
        focus = [inp.text().strip() for inp in self.weekly_inputs if inp.text().strip()]
        self.state["stats"]["weeklyFocus"] = focus
        self.state["stats"]["lastWeeklyReset"] = today_str()
        self._schedule_save()
        self.card_weekly.setVisible(False)
        self._refresh_stats_and_habits()

    def _move_someday_suggestion(self):
        tid = self.lbl_someday_text.property("taskId")
        if tid:
            self._move_task_section(tid, "Today") # Helper exists or logic similar
            self.card_someday_suggestion.setVisible(False)

    def _on_glance_clicked(self, item):
        tid = item.data(Qt.ItemDataRole.UserRole)
        self._switch_page(self.page_today)
        self.page_today.scroll_to_task(tid)

    def _mood_message_for_value(self, value: str) -> str:
        if value == "Low energy":
            return "Low days happen. You’re still allowed to go slow and do tiny steps."
        if value == "Stressed":
            return "Stress is heavy. You don’t have to win the whole day, just make it softer."
        if value == "Okay":
            return "An okay day is still a real day. One or two gentle wins are enough."
        if value == "Motivated":
            return "Nice, you’re motivated. Let’s use that energy without burning you out."
        if value == "Great":
            return "Enjoy the good days. You don’t need to be perfect to deserve them."
        return "There are good days and bad days. You still deserve kindness on all of them."

    def request_delete_task(self, task_id: str):
        # Find task
        task = next((t for t in self.state["tasks"] if t["id"] == task_id), None)
        if not task: return
        
        self._last_deleted_task = task.copy()
        delete_task(self.state, task_id)
        self._schedule_save()
        
        # Refresh all lists
        self.page_today.refresh()
        self.page_week.refresh()
        self.page_someday.refresh()
        self.project_task_widget.refresh()
        self._refresh_home()
        
        # Show toast
        self.toast_frame.setVisible(True)
        self.toast_frame.raise_()
        QTimer.singleShot(5000, lambda: self.toast_frame.setVisible(False))

    def _undo_delete(self):
        if self._last_deleted_task:
            self.state["tasks"].append(self._last_deleted_task)
            self._last_deleted_task = None
            self._schedule_save()
            self.page_today.refresh()
            self.page_week.refresh()
            self.page_someday.refresh()
            self.project_task_widget.refresh()
            self.toast_frame.setVisible(False)

    def record_task_completion(self):
        now = datetime.now().timestamp()
        # Reset session if gap > 20 mins (1200 seconds)
        if self._last_completion_time and (now - self._last_completion_time > 1200):
            self._consecutive_completions = 0
        
        self._consecutive_completions += 1
        self._last_completion_time = now
        
        if self._consecutive_completions >= 3:
            # Log session
            today = today_str()
            sessions = self.state["stats"].setdefault("focusSessions", {})
            sessions[today] = sessions.get(today, 0) + 1
            self._consecutive_completions = 0
            self._schedule_save()
            
            # Show hint if on Today page
            if self.stack.currentWidget() == self.page_today:
                self.page_today.show_session_hint()
            
            # Refresh stats if visible
            if self.stack.currentWidget() == self.page_stats:
                self._refresh_stats_and_habits()

    def _run_daily_planning(self):
        stats = self.state.setdefault("stats", {})
        if stats.get("lastPlanningDate") == today_str():
            return

        incomplete_today = len([t for t in tasks_in_section(self.state, "Today") if not t.get("completed")])
        
        dlg = DailyPlanningDialog(incomplete_today, self)
        if dlg.exec():
            num = dlg.spin_box.value()
            mood = get_today_mood(self.state)
            mood_value = mood.get("value", "Okay") if mood else "Okay"
            
            # Hard day protection logic in planning
            if mood_value in ("Low energy", "Stressed") and num > 3:
                QMessageBox.information(self, "Gentle Reminder", "It's a tough day. Maybe aim for just 1-3 essential tasks?")
            
            stats["plannedTasksToday"] = num
            stats["targetTasksToday"] = num
            stats["moodAtStart"] = mood_value
            stats["lastPlanningDate"] = today_str()
            self._schedule_save()
            self._refresh_stats_and_habits()

    # ────────────────────────────────────────────────────────────────────
    # Projects page
    # ────────────────────────────────────────────────────────────────────

    def _refresh_projects(self) -> None:
        self.project_list.clear()
        for p in self.state.get("projects", []):
            item = QListWidgetItem(p.get("name", "Untitled"))
            item.setData(Qt.ItemDataRole.UserRole, p.get("id"))
            
            # Color indicator
            pix = QPixmap(10, 10)
            pix.fill(QColor(p.get("color", GOLD)))
            item.setIcon(QIcon(pix))
            self.project_list.addItem(item)
        self.project_detail_title.setText("Select a project")
        self.project_task_widget.set_project(None)
        
        self.empty_projects_label.setVisible(self.project_list.count() == 0)
        
        has_sel = bool(self.project_list.selectedItems())
        self.btn_rename_project.setEnabled(has_sel)
        self.btn_delete_project.setEnabled(has_sel)
        
        # Center empty state if no selection
        if not self.project_list.selectedItems():
            self.project_detail_title.setText("Select a project")
            self.project_task_widget.setVisible(False)
            # We can rely on project_detail_title being centered or add a specific label
            # For now, just hiding the task widget makes the title centered in the layout flow
        else:
            self.project_task_widget.setVisible(True)

    def _on_add_project(self) -> None:
        name, ok = QInputDialog.getText(self, "New Project", "Project Name:")
        if ok and name:
            proj = add_project(self.state, name)
            self._schedule_save()
            self._refresh_projects()
            # Auto-select
            for i in range(self.project_list.count()):
                item = self.project_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == proj['id']:
                    self.project_list.setCurrentItem(item)
                    self._on_project_selected()
                    break
            self.project_task_widget.quick_add_input.setFocus()

    def _on_rename_project(self) -> None:
        current_item = self.project_list.currentItem()
        if not current_item: return
        pid = current_item.data(Qt.ItemDataRole.UserRole)
        proj = get_project_by_id(self.state, pid)
        if not proj: return

        new_name, ok = QInputDialog.getText(self, "Rename Project", "New Name:", text=proj['name'])
        if ok and new_name:
            proj['name'] = new_name
            self._schedule_save()
            self._refresh_projects()
            # Reselect to keep focus
            for i in range(self.project_list.count()):
                item = self.project_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == pid:
                    self.project_list.setCurrentItem(item)
                    break

    def _on_delete_project(self) -> None:
        current_item = self.project_list.currentItem()
        if not current_item: return
        pid = current_item.data(Qt.ItemDataRole.UserRole)
        proj = get_project_by_id(self.state, pid)
        if not proj: return

        reply = QMessageBox.question(self, "Delete Project", f"Are you sure you want to delete '{proj['name']}'? This will also unassign all its tasks.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            row = self.project_list.row(current_item)
            self.state['projects'] = [p for p in self.state['projects'] if p['id'] != pid]
            for task in self.state['tasks']:
                if task.get('projectId') == pid:
                    task['projectId'] = None
            self._schedule_save()
            self._refresh_projects()
            
            # Select next or previous
            count = self.project_list.count()
            if count > 0:
                new_row = min(row, count - 1)
                self.project_list.setCurrentRow(new_row)
            else:
                self._on_project_selected() # Trigger empty state

    def _on_project_selected(self) -> None:
        items = self.project_list.selectedItems()
        has_sel = bool(items)
        self.btn_rename_project.setEnabled(has_sel)
        self.btn_delete_project.setEnabled(has_sel)

        if not items:
            self.project_detail_title.setText("Select a project")
            self.project_task_widget.set_project(None)
            return
        item = items[0]
        pid = item.data(Qt.ItemDataRole.UserRole)
        proj = get_project_by_id(self.state, pid)
        if not proj:
            self.project_detail_title.setText("Project not found")
            self.project_task_widget.set_project(None)
            return

        self.project_detail_title.setText(proj.get("name", "Untitled"))
        c = proj.get("color", GOLD)
        self.project_detail_title.setStyleSheet(f"color: {c}; font-weight: bold; font-size: 24px; background: transparent;")
        self.project_task_widget.setVisible(True)
        self.project_task_widget.set_project(pid)

    # ────────────────────────────────────────────────────────────────────
    # Stats & habits page
    # ────────────────────────────────────────────────────────────────────

    def _refresh_stats_and_habits(self) -> None:
        stats = self.state.get("stats", {})
        streak = stats.get("currentStreak", 0)
        done_today = stats.get("tasksCompletedToday", 0)
        planned = stats.get("plannedTasksToday", 0)
        mood_start = stats.get("moodAtStart")
        weekly_focus = stats.get("weeklyFocus", [])
        focus_sessions = stats.get("focusSessions", {}).get(today_str(), 0)

        mood = get_today_mood(self.state)
        encouragement = ""
        if mood:
            val = mood.get("value", "")
            if val in ("Low energy", "Stressed"):
                encouragement = "Be gentle with yourself today."
                if done_today > 0:
                    encouragement = "You showed up on a hard day. That counts."
                else:
                    encouragement = "On heavy days, just existing is enough work."
            elif val in ("Motivated", "Great"):
                encouragement = "Nice energy today. Use it gently, not to exhaust yourself."
        else:
            encouragement = "However you feel today is valid. You’re allowed to go at your pace."

        if mood_start:
            encouragement += f"\nMood at start today: {mood_start}."
            
        lines = []
        lines.append(f"<b>Streak:</b> {streak} days")
        lines.append(f"<b>Today:</b> {done_today} completed / {planned} planned")
        lines.append(f"<b>Mood:</b> {val if mood else 'Not logged'} — {encouragement}")
        
        if focus_sessions > 0:
             lines.append(f"<b>Focus:</b> {focus_sessions} sessions today")
        
        if weekly_focus:
            focus_str = ", ".join(weekly_focus)
            lines.append(f"<br><b>This week's focus:</b> {focus_str}")

        self.stats_summary_label.setText("<br>".join(lines))
        self.mood_graph.update()
        self.habit_graph.update()

        # Habits list
        self.habits_list.clear()
        checks = get_today_habit_checks(self.state)
        habits = [h for h in self.state.get("habits", []) if h.get("active", True)]
        done_habits = sum(1 for h in habits if checks.get(h["id"]))
        self.habit_counter_label.setText(f"Completed {done_habits} of {len(habits)} active habits today.")
        
        for h in self.state.get("habits", []):
            if not h.get("active", True):
                continue
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, h.get("id"))

            row = QWidget()
            row.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            hl = QHBoxLayout(row)
            hl.setContentsMargins(6, 2, 6, 2)
            hl.setSpacing(6)

            btn = QPushButton("✔" if checks.get(h["id"], False) else "")
            btn.setCheckable(True)
            btn.setChecked(checks.get(h["id"], False))
            btn.setFixedSize(QSize(22, 22))
            btn.setStyleSheet(f"""
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
            """)

            lbl = QLabel(h.get("name", "Habit"))
            lbl.setStyleSheet(f"color: {TEXT_WHITE};")

            hl.addWidget(btn)
            hl.addWidget(lbl, 1)

            self.habits_list.addItem(item)
            self.habits_list.setItemWidget(item, row)

            btn.clicked.connect(
                lambda checked, hid=h["id"]: self._on_toggle_habit(hid, checked)
            )

    def _on_toggle_habit(self, habit_id: str, checked: bool) -> None:
        set_habit_checked(self.state, habit_id, checked)
        if checked:
            self.habit_message.setText("Nice, that’s one small win for today.")
        else:
            self.habit_message.setText("You can always come back to this habit. Nothing is ruined.")
        self._schedule_save()

    # ────────────────────────────────────────────────────────────────────
    # Updates
    # ────────────────────────────────────────────────────────────────────

    def _check_updates_async(self) -> None:
        """Run on a background thread; fetch latest GitHub release."""
        if requests is None:
            return  # no HTTP support available

        def worker():
            latest_version = None
            download_url = None
            error = None
            try:
                headers = {"Accept": "application/vnd.github+json"}
                resp = requests.get(GITHUB_API_LATEST, headers=headers, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                tag = data.get("tag_name") or ""
                latest_version = tag

                # Find setup.exe asset
                assets = data.get("assets", [])
                for asset in assets:
                    name = asset.get("name", "").lower()
                    if "setup" in name and name.endswith(".exe"):
                        download_url = asset.get("browser_download_url")
                        break
            except Exception as e:
                error = str(e)

            # Back to main thread
            QTimer.singleShot(0, lambda: self._on_update_check_result(latest_version, download_url, error))

        threading.Thread(target=worker, daemon=True).start()

    def _on_update_check_result(self, latest_version: Optional[str], download_url: Optional[str], error: Optional[str]) -> None:
        """Handle update check result on UI thread."""
        if error or not latest_version:
            return
        
        if self.state.get("stats", {}).get("lastIgnoredVersion") == latest_version:
            return

        if not is_newer_version(latest_version, APP_VERSION):
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Update available")
        msg.setText(f"A newer version of TaskFlow Hub is available: {latest_version}.\n\nYour version: {APP_VERSION}.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        msg.setCheckBox(QCheckBox("Don't remind me about this version again"))
        if download_url:
            msg.setInformativeText("Do you want to open the download page in your browser?")
            ret = msg.exec()
            if ret == QMessageBox.StandardButton.Ok:
                self._open_update_url(download_url)

        if msg.checkBox().isChecked():
            self.state.setdefault("stats", {})["lastIgnoredVersion"] = latest_version
            self._schedule_save()

    def _open_update_url(self, url: str) -> None:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    # ────────────────────────────────────────────────────────────────────
    # Events & saving
    # ────────────────────────────────────────────────────────────────────

    def _on_save_mood(self) -> None:
        value = self.mood_combo.currentText()
        note = self.mood_note.toPlainText().strip()
        set_today_mood(self.state, value, note)
        self.mood_message.setText(self._mood_message_for_value(value))
        self._schedule_save()

    def _schedule_save(self) -> None:
        self._save_timer.start()

    def _do_save(self) -> None:
        self.state["ui_geometry"] = self.geometry().getRect()
        save_state(self.paths, self.state)

    def closeEvent(self, event) -> None:
        now = datetime.now()
        today = today_str()
        if now.hour >= 20 and self.state.get("stats", {}).get("lastReviewDate") != today:
            reply, ok = QInputDialog.getItem(self, "End of Day Review", "How did today feel overall?", ["Productive", "Average", "Tough"], 0, False)
            if ok and reply:
                self.state.setdefault("dayQuality", {})[today] = reply
            self.state.setdefault("stats", {})["lastReviewDate"] = today

        self._do_save()
        super().closeEvent(event)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6: ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    app = QApplication(sys.argv)
    paths = get_data_paths()
    state = load_state(paths)
    rollover_tasks(state)
    save_state(paths, state)
    window = HubWindow(state, paths)
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
