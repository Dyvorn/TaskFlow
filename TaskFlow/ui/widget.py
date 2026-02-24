from __future__ import annotations
import os
import math
import random
import sys
from typing import Any, Dict, Optional, Callable

from PyQt6.QtCore import (
    Qt,
    QTimer,
    QSize,
    QPoint,
    QPropertyAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
    QPointF,
)
from PyQt6.QtGui import QMouseEvent, QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel, QMenu,
    QPushButton,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QLineEdit,
    QGraphicsOpacityEffect,
)

try:
    import winsound
except ImportError:
    winsound = None

from core.model import (
    APP_NAME,
    DARK_BG,
    GLASS_BG,
    GLASS_BORDER,
    HOVER_BG,
    TEXT_WHITE,
    TEXT_GRAY,
    GOLD,
    ANIM_DURATION_MEDIUM,
    get_data_paths,
    load_state,
    save_state,
    count_today_tasks,
    tasks_in_section,
    toggle_task_completed,
    ConfettiOverlay,
    TaskRowWidget,
    add_task,
    delete_task,
    parse_task_input,
    AnimationManager,
)


WIDGET_WIDTH = 320
WIDGET_HEIGHT = 520
WIDGET_COLLAPSED_WIDTH = 32
SNAP_THRESHOLD = 24

AUTO_COLLAPSE_MS = 4000  # auto collapse after 4s idle when docked
LONG_IDLE_MS = 10 * 60 * 1000  # after 10 minutes, require click to open

class WidgetWindow(QWidget):
    """
    Always-on widget for Today tasks + active project tasks.
    Small glassy rectangle that docks to screen edges and collapses to a bump.
    """

    def __init__(
        self,
        state: Dict[str, Any],
        paths: Dict[str, str],
        save_callback: Callable[[], None],
        hub_instance: Optional[QWidget],
    ) -> None:
        super().__init__(flags=Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.state = state
        self.paths = paths
        self._save_callback = save_callback
        self._hub = hub_instance

        # collapse state
        settings = self.state.get("settings", {})
        self._docked = settings.get("widgetDocked", True)
        self._docked_side = settings.get("widgetDockSide", "right")
        self._expanded = not settings.get("widgetCollapsed", False)
        self._hover_expand_enabled = True
        self._auto_collapse_enabled = True
        self._require_click_after_idle = True
        self._long_idle_mode = False

        # tracking for dragging
        self._drag_active = False
        self._drag_pos = QPoint()
        
        self._pos_anim = None
        self._highlight_overlay = None
        self._highlight_effect = None

        # timers
        self._auto_collapse_timer = QTimer(self)
        self._auto_collapse_timer.setSingleShot(True)
        self._auto_collapse_timer.timeout.connect(self._on_auto_collapse_timeout)
        
        self._hover_open_timer = QTimer(self)
        self._hover_open_timer.setSingleShot(True)
        self._hover_open_timer.timeout.connect(self._on_hover_open_timeout)

        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self._on_long_idle_timeout)

        self._build_ui()
        self._apply_style()
        self._refresh_tasks()
        self._restore_position()
        self._restart_idle_timers()

        # Confetti Overlay
        self.confetti = ConfettiOverlay(self)
        self.confetti.resize(self.size())

    # ────────────────────────────────────────────────────────────────────
    # Geometry & Positioning Helpers
    # ────────────────────────────────────────────────────────────────────

    def _get_current_screen_geometry(self):
        screen = QApplication.screenAt(self.geometry().center())
        if not screen:
            screen = QApplication.primaryScreen()
        return screen.availableGeometry()

    def _clamp_y(self, y: int, geo) -> int:
        return max(geo.top(), min(y, geo.bottom() - WIDGET_HEIGHT + 1))

    def _expanded_anchor_x(self, side: str, geo) -> int:
        if side == "left":
            return geo.left()
        return geo.right() - WIDGET_WIDTH + 1

    def _collapsed_anchor_x(self, side: str, geo) -> int:
        if side == "left":
            return geo.left() - (WIDGET_WIDTH - WIDGET_COLLAPSED_WIDTH)
        return geo.right() - WIDGET_COLLAPSED_WIDTH + 1

    def _restore_position(self) -> None:
        settings = self.state.get("settings", {})
        pos = settings.get("widgetPos")
        
        geo = self._get_current_screen_geometry()
        
        # Default to right edge if no pos saved
        if pos and len(pos) == 2:
            x, y = int(pos[0]), int(pos[1])
        else:
            x = geo.right() - WIDGET_WIDTH + 1
            y = geo.top() + 100

        # Ensure Y is valid
        y = self._clamp_y(y, geo)

        # If docked, force X to the correct anchor based on state
        if self._docked:
            if self._expanded:
                x = self._expanded_anchor_x(self._docked_side, geo)
            else:
                x = self._collapsed_anchor_x(self._docked_side, geo)
        
        # Ensure size is correct (always full size, we slide off-screen to collapse)
        self.resize(WIDGET_WIDTH, WIDGET_HEIGHT)
        self.move(x, y)
        
        # Set initial visibility
        if self._expanded:
            self.content_wrap.show()
            self.bump.hide()
        else:
            self.content_wrap.hide()
            self.bump.show()

    # ────────────────────────────────────────────────────────────────────
    # UI
    # ────────────────────────────────────────────────────────────────────

    def _apply_style(self) -> None:
        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: transparent;
            }}
            QFrame#WidgetCard {{
                background-color: {GLASS_BG};
                border-radius: 16px;
                border: 1px solid {GLASS_BORDER};
            }}
            QLabel {{
                color: {TEXT_WHITE};
            }}
            QLabel#WidgetHeader {{
                color: {GOLD};
                font-weight: bold;
            }}
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.05);
                color: {TEXT_WHITE};
                border-radius: 8px;
                border: 1px solid {HOVER_BG};
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.15);
            }}
            QListWidget {{
                background-color: transparent;
                border: none;
                color: {TEXT_WHITE};
            }}
            """
        )

    def _build_ui(self) -> None:
        self.resize(WIDGET_WIDTH, WIDGET_HEIGHT)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.card = QFrame()
        self.card.setObjectName("WidgetCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(6)

        # Content Wrapper (for hiding real UI during collapse)
        self.content_wrap = QWidget()
        self.content_layout = QVBoxLayout(self.content_wrap)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(6)

        # Bump (visible only when collapsed)
        self.bump = QFrame()
        self.bump.setObjectName("Bump")
        self.bump.setStyleSheet(f"background-color: rgba(255, 255, 255, 0.1); border: 1px solid {GLASS_BORDER}; border-radius: 16px;")
        self.bump.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.bump.setToolTip("Click or hover to expand")
        self.bump.hide()
        
        # Add a visual handle to the bump
        bump_layout = QVBoxLayout(self.bump)
        bump_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bump_handle = QLabel("⋮")
        bump_handle.setStyleSheet(f"color: {GOLD}; font-size: 20px; font-weight: bold;")
        bump_layout.addWidget(bump_handle)

        # header row
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        self.header_label = QLabel(f"{APP_NAME} Today")
        self.header_label.setObjectName("WidgetHeader")
        header_row.addWidget(self.header_label, 1)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 11px;")
        header_row.addWidget(self.status_label, 2)

        # Collapse button
        self.btn_collapse = QPushButton("›")
        self.btn_collapse.setFixedSize(24, 24)
        self.btn_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_collapse.setToolTip("Collapse/Expand")
        self.btn_collapse.clicked.connect(lambda: self._set_expanded(False))
        header_row.addWidget(self.btn_collapse)

        self.content_layout.addLayout(header_row)

        # Task List
        self.tasks_list = QListWidget()
        self.tasks_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tasks_list.customContextMenuRequested.connect(self._on_context_menu)
        self.content_layout.addWidget(self.tasks_list, 1)

        # Quick Add Input (initially hidden)
        self.quick_add_input = QLineEdit()
        self.quick_add_input.setPlaceholderText("Add to Today & press Enter...")
        self.quick_add_input.returnPressed.connect(self._on_quick_add)
        self.quick_add_input.setVisible(False)
        self.content_layout.addWidget(self.quick_add_input)

        # Action buttons
        actions_row = QHBoxLayout()
        actions_row.setSpacing(6)

        btn_open_hub = QPushButton("Open Hub")
        btn_open_today = QPushButton("Open Today")
        btn_quick_add = QPushButton("+ Quick Add")

        btn_open_hub.clicked.connect(lambda: self._open_hub_page("home"))
        btn_open_today.clicked.connect(lambda: self._open_hub_page("today"))
        btn_quick_add.clicked.connect(self._toggle_quick_add)

        actions_row.addWidget(btn_open_hub)
        actions_row.addWidget(btn_open_today)
        actions_row.addWidget(btn_quick_add)
        self.content_layout.addLayout(actions_row)

        card_layout.addWidget(self.content_wrap)
        card_layout.addWidget(self.bump)

        # Highlight overlay for dopamine pulse (child of card, on top of card)
        self._highlight_overlay = QFrame(self.card)
        self._highlight_overlay.setStyleSheet(f"background-color: {GOLD}; border-radius: 16px;")
        self._highlight_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._highlight_overlay.hide()
        
        self._highlight_effect = QGraphicsOpacityEffect(self._highlight_overlay)
        self._highlight_effect.setOpacity(0.0)
        self._highlight_overlay.setGraphicsEffect(self._highlight_effect)

        outer.addWidget(self.card)

    # ────────────────────────────────────────────────────────────────────
    # Actions
    # ────────────────────────────────────────────────────────────────────

    def _open_hub_page(self, page_key: str):
        self._restart_idle_timers()
        if self._hub:
            self._hub.showNormal()
            self._hub.raise_()
            self._hub.activateWindow()
            self._hub.open_page(page_key)

    def _toggle_quick_add(self):
        self._restart_idle_timers()
        is_visible = self.quick_add_input.isVisible()
        self.quick_add_input.setVisible(not is_visible)
        if not is_visible:
            self.quick_add_input.setFocus()

    def _on_quick_add(self) -> None:
        text = self.quick_add_input.text().strip()
        if not text:
            return
            
        # Use shared parser
        meta = parse_task_input(text)
        
        add_task(
            self.state, 
            text=meta["text"], 
            section=meta["section"],
            category=meta["category"],
            important=meta["important"]
        )
        
        # Visual feedback: Flash input
        self.quick_add_input.setStyleSheet(f"background-color: rgba(255, 215, 0, 0.2); border: 1px solid {GOLD}; border-radius: 8px; color: {TEXT_WHITE};")
        QTimer.singleShot(200, lambda: self.quick_add_input.setStyleSheet(""))
        
        self._save_callback()
        
        # Delay hiding slightly to show the flash
        def finalize():
            self.quick_add_input.clear()
            self.quick_add_input.setVisible(False)
            self._refresh_tasks()
            if meta["section"] != "Today":
                self.status_label.setText(f"Added to {meta['section']}")
                
        QTimer.singleShot(250, finalize)
        self._refresh_tasks()

    # ────────────────────────────────────────────────────────────────────
    # Tasks
    # ────────────────────────────────────────────────────────────────────

    def _refresh_tasks(self) -> None:
        scroll_pos = self.tasks_list.verticalScrollBar().value()
        
        selected_id = None
        if self.tasks_list.currentItem():
            selected_id = self.tasks_list.currentItem().data(Qt.ItemDataRole.UserRole)
            
        self.tasks_list.clear()

        # Today tasks
        today_tasks = tasks_in_section(self.state, "Today")
        incomplete_tasks = [t for t in today_tasks if not t.get("completed")]

        # Sort: important first, then by order
        incomplete_tasks.sort(key=lambda t: (0 if t.get("important") else 1, t.get("order", 0)))

        max_visible = self.state.get("settings", {}).get("widgetTaskCount", 5)
        
        visible_tasks = []
        is_showing_scheduled = False

        if incomplete_tasks:
            visible_tasks = incomplete_tasks[:max_visible]
            self.header_label.setText(f"{APP_NAME} Today")
        else:
            # If Today is empty, look for Scheduled
            scheduled = tasks_in_section(self.state, "Scheduled")
            scheduled = [t for t in scheduled if not t.get("completed")]
            # Sort primarily by date
            scheduled.sort(key=lambda t: t.get("schedule", {}).get("date", "9999-99-99"))
            
            if scheduled:
                visible_tasks = scheduled[:max_visible]
                is_showing_scheduled = True
                self.header_label.setText(f"{APP_NAME} Upcoming")
            else:
                self.header_label.setText(f"{APP_NAME} Today")

        for t in visible_tasks:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, t.get("id"))

            row = TaskRowWidget(t, show_delete_button=False, show_focus_button=False)
            row.toggled.connect(self._on_widget_task_toggle)
            row.contextMenuRequested.connect(
                lambda pos, tid: self._on_context_menu(row.mapToGlobal(pos), tid)
            )
            
            self.tasks_list.addItem(item)
            self.tasks_list.setItemWidget(item, row)

    def _on_widget_task_toggle(self, task_id: str):
        for i in range(self.tasks_list.count()):
            item = self.tasks_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == task_id:
                row = self.tasks_list.itemWidget(item)
                if row:
                    AnimationManager.slide_and_fade_out(row, on_finished=lambda: self._finalize_toggle(task_id))
                break

    def _finalize_toggle(self, task_id: str):
        self._refresh_tasks()

    def _on_context_menu(self, pos, task_id=None):
        # If task_id is not provided (e.g. background click), try to find item at pos
        if not task_id:
            # Map global pos back to list widget coordinates for itemAt
            local_pos = self.tasks_list.mapFromGlobal(pos)
            item = self.tasks_list.itemAt(local_pos)
            if item:
                task_id = item.data(Qt.ItemDataRole.UserRole)
        
        menu = QMenu(self)
        menu.setStyleSheet(f"QMenu {{ background-color: {GLASS_BG}; color: {TEXT_WHITE}; border: 1px solid {GLASS_BORDER}; }} QMenu::item:selected {{ background-color: {HOVER_BG}; }}")
        
        if task_id:
            task = next((t for t in self.state["tasks"] if t["id"] == task_id), None)
            if not task: return

            act_imp = menu.addAction("Unmark Important" if task.get("important") else "Mark Important")
            act_del = menu.addAction("Delete")
            
            action = menu.exec(pos)
            
            if action == act_imp:
                task["important"] = not task.get("important")
                self._save_callback()
                self._refresh_tasks()
            elif action == act_del:
                delete_task(self.state, task_id)
                self._save_callback()
                self._refresh_tasks()
        else:
            # Background context menu
            act_add = menu.addAction("Quick Add")
            act_hub = menu.addAction("Open Hub")
            
            action = menu.exec(pos)
            
            if action == act_add:
                self._toggle_quick_add()
            elif action == act_hub:
                self._open_hub_page("home")

    # ────────────────────────────────────────────────────────────────────

    def _restart_idle_timers(self) -> None:
        if self._auto_collapse_enabled and self._docked and self._expanded:
            self._auto_collapse_timer.start(AUTO_COLLAPSE_MS)
        else:
            self._auto_collapse_timer.stop()

        if self._require_click_after_idle:
            self._idle_timer.start(LONG_IDLE_MS)
        else:
            self._idle_timer.stop()

    def _on_auto_collapse_timeout(self) -> None:
        # Don't collapse if user is typing
        if self.quick_add_input.isVisible() and self.quick_add_input.hasFocus():
            self._restart_idle_timers()
            return
            
        if self._docked and self._expanded:
            self._set_expanded(False, is_auto=True)

    def _on_long_idle_timeout(self) -> None:
        self._long_idle_mode = True

    def _on_hover_open_timeout(self) -> None:
        if self._docked and not self._expanded:
            self._set_expanded(True)

    def _set_expanded(self, expanded: bool, is_auto: bool = False) -> None:
        if self._expanded == expanded or not self._docked:
            return
        
        # Stop running animation
        if self._pos_anim and self._pos_anim.state() == QPropertyAnimation.State.Running:
            self._pos_anim.stop()

        self._expanded = expanded
        geo = self._get_current_screen_geometry()

        start_pos = self.pos()
        
        # Update collapse button direction
        self.btn_collapse.setText("›" if self._docked_side == "right" else "‹")
        
        # Calculate target X based on side and expansion state
        if expanded:
            target_x = self._expanded_anchor_x(self._docked_side, geo)
            easing = QEasingCurve.Type.OutCubic
            duration = ANIM_DURATION_MEDIUM
            # Expand: show content immediately (slide in)
            self.bump.hide()
            self.content_wrap.show()
        else:
            target_x = self._collapsed_anchor_x(self._docked_side, geo)
            easing = QEasingCurve.Type.InCubic # Accelerate into ramp
            duration = ANIM_DURATION_MEDIUM + 80
            # Collapse: hide content immediately, show bump (slide out)
            self.content_wrap.hide()
            self.bump.show()

        # Clamp Y to ensure it stays on screen
        target_y = self._clamp_y(self.y(), geo)
        end_pos = QPoint(target_x, target_y)

        # Update state immediately
        settings = self.state.setdefault("settings", {})
        settings["widgetCollapsed"] = not expanded
        # We don't update widgetPos here because widgetPos tracks the *expanded* position
        self._save_callback()

        self.resize(WIDGET_WIDTH, WIDGET_HEIGHT)

        self._pos_anim = QPropertyAnimation(self, b"pos")
        self._pos_anim.setDuration(duration)
        self._pos_anim.setStartValue(start_pos)
        self._pos_anim.setEndValue(end_pos)
        self._pos_anim.setEasingCurve(easing)
        
        if not expanded:
            self._pos_anim.finished.connect(self._pulse_ramp_highlight)
            
        self._pos_anim.start()

    def _pulse_ramp_highlight(self) -> None:
        if not self._highlight_overlay or self._expanded:
            return
        self._highlight_overlay.show()
        
        anim = QPropertyAnimation(self._highlight_effect, b"opacity", self)
        anim.setDuration(220)
        anim.setKeyValueAt(0.0, 0.0)
        anim.setKeyValueAt(0.5, 0.3) # Peak intensity
        anim.setKeyValueAt(1.0, 0.0)
        anim.finished.connect(self._highlight_overlay.hide)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # If collapsed and docked, a single click should expand it
            if self._docked and not self._expanded:
                self._long_idle_mode = False # Reset idle mode
                self._set_expanded(True)
                self._restart_idle_timers()
                event.accept()
                return

            self._drag_active = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_active:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            
            # If dragging, we are effectively expanded (or should be)
            if not self._expanded:
                self._set_expanded(True)
                if self._pos_anim:
                    self._pos_anim.stop()
            
            self.move(new_pos)
            
            # Update widgetPos while dragging if expanded, so we remember where we left it
            # even if we don't dock.
            if self._expanded:
                self.state["settings"]["widgetPos"] = [new_pos.x(), new_pos.y()]
            
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drag_active:
            self._drag_active = False
            
            geo = self._get_current_screen_geometry()
            x = self.x()
            y = self.y()
            
            # Check docking thresholds
            dist_left = abs(x - geo.left())
            dist_right = abs((x + WIDGET_WIDTH - 1) - geo.right())
            
            docked = False
            side = self._docked_side
            
            if dist_left <= SNAP_THRESHOLD:
                docked = True
                side = "left"
                x = self._expanded_anchor_x("left", geo)
            elif dist_right <= SNAP_THRESHOLD:
                docked = True
                side = "right"
                x = self._expanded_anchor_x("right", geo)
            
            # Always clamp Y
            y = self._clamp_y(y, geo)
            
            self._docked = docked
            self._docked_side = side
            self._expanded = True # Always expand on drop
            
            self.move(int(x), int(y))
            
            # Persist
            s = self.state.setdefault("settings", {})
            s["widgetDocked"] = self._docked
            s["widgetDockSide"] = self._docked_side
            s["widgetPos"] = [x, y]
            s["widgetCollapsed"] = False
            self._save_callback()
            
            self._restart_idle_timers()
            event.accept()
        super().mouseReleaseEvent(event)

    def enterEvent(self, event) -> None:
        if self._docked and not self._expanded:
            if self._hover_expand_enabled and not self._long_idle_mode:
                self._hover_open_timer.start(300) # Faster response (was 1500)
        self._restart_idle_timers()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover_open_timer.stop()
        self._restart_idle_timers()
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._docked:
            self._long_idle_mode = False
            self._set_expanded(True)
            self._restart_idle_timers()
        super().mouseDoubleClickEvent(event)

    def resizeEvent(self, event) -> None:
        if self._highlight_overlay and hasattr(self, "card"):
            self._highlight_overlay.resize(self.card.size())
        if hasattr(self, "confetti"):
            self.confetti.resize(self.size())
        super().resizeEvent(event)

    # ────────────────────────────────────────────────────────────────────
    # Close → save
    # ────────────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self._save_callback()
        super().closeEvent(event)


def debug_main() -> None:
    app = QApplication(sys.argv)
    paths = get_data_paths()
    state = load_state(paths)

    # For debugging, provide dummy callbacks
    widget = WidgetWindow(state, paths, lambda: save_state(paths, state), None)
    widget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    debug_main()
