from __future__ import annotations

import sys
from typing import Any, Dict, Optional, Callable

from PyQt6.QtCore import (
    Qt,
    QTimer,
    QSize,
    QPoint,
    QPropertyAnimation,
    QEasingCurve,
)
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QLineEdit,
)

from taskflowmodel import (
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
    add_task,
)


WIDGET_WIDTH = 320
WIDGET_HEIGHT = 520
WIDGET_COLLAPSED_WIDTH = 32

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
        self._docked_side: Optional[str] = None  # "left" or "right"
        self._expanded = True
        self._hover_expand_enabled = True
        self._auto_collapse_enabled = True
        self._require_click_after_idle = True
        self._long_idle_mode = False

        # tracking for dragging
        self._drag_active = False
        self._drag_pos = QPoint()

        # timers
        self._auto_collapse_timer = QTimer(self)
        self._auto_collapse_timer.setSingleShot(True)
        self._auto_collapse_timer.timeout.connect(self._on_auto_collapse_timeout)

        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self._on_long_idle_timeout)

        self._build_ui()
        self._apply_style()
        self._refresh_tasks()
        self._restart_idle_timers()

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

        card = QFrame()
        card.setObjectName("WidgetCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(6)

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

        card_layout.addLayout(header_row)

        # Task List
        self.tasks_list = QListWidget()
        card_layout.addWidget(self.tasks_list, 1)

        # Quick Add Input (initially hidden)
        self.quick_add_input = QLineEdit()
        self.quick_add_input.setPlaceholderText("Add to Today & press Enter...")
        self.quick_add_input.returnPressed.connect(self._on_quick_add)
        self.quick_add_input.setVisible(False)
        card_layout.addWidget(self.quick_add_input)

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
        card_layout.addLayout(actions_row)

        outer.addWidget(card)

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
        add_task(self.state, text=text, section="Today")
        self._save_callback()
        self.quick_add_input.clear()
        self.quick_add_input.setVisible(False)
        self._refresh_tasks()

    # ────────────────────────────────────────────────────────────────────
    # Tasks + suggestion
    # ────────────────────────────────────────────────────────────────────

    def _refresh_tasks(self) -> None:
        self.tasks_list.clear()

        # Today tasks
        today_tasks = tasks_in_section(self.state, "Today")
        incomplete_tasks = [t for t in today_tasks if not t.get("completed")]

        # Sort: important first, then by order
        incomplete_tasks.sort(key=lambda t: (0 if t.get("important") else 1, t.get("order", 0)))

        max_visible = self.state.get("settings", {}).get("widgetTaskCount", 5)
        visible_tasks = incomplete_tasks[:max_visible]

        for t in visible_tasks:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, t.get("id"))

            row = QWidget()
            hl = QHBoxLayout(row)
            hl.setContentsMargins(2, 0, 2, 0)
            hl.setSpacing(4)

            chk = QPushButton("✔" if t.get("completed") else "")
            chk.setCheckable(True)
            chk.setChecked(t.get("completed"))
            chk.setFixedSize(QSize(20, 20))

            text = t.get("text", "")
            lbl = QLabel(text)
            lbl.setWordWrap(True)
            if t.get("completed"):
                lbl.setStyleSheet(
                    f"color: {TEXT_GRAY}; text-decoration: line-through;"
                )
            elif t.get("important"):
                lbl.setStyleSheet(f"color: {GOLD}; font-weight: bold;")

            hl.addWidget(chk)
            hl.addWidget(lbl, 1)

            self.tasks_list.addItem(item)
            self.tasks_list.setItemWidget(item, row)

            chk.clicked.connect(
                lambda checked, tid=t.get("id"): self._on_toggle_task(tid)
            )

        # Update status line
        counts = count_today_tasks(self.state)
        if counts["total"] == 0:
            self.status_label.setText("All clear for Today.")
        else:
            self.status_label.setText(f"{counts['completed']} of {counts['total']} done.")

    def _on_toggle_task(self, task_id: str) -> None:
        toggle_task_completed(self.state, task_id)
        self._save_callback()
        self._refresh_tasks()
        self._restart_idle_timers()

    # ────────────────────────────────────────────────────────────────────
    # Collapse / dock / drag
    # ────────────────────────────────────────────────────────────────────

    def _restart_idle_timers(self) -> None:
        if self._auto_collapse_enabled and self._docked_side and self._expanded:
            self._auto_collapse_timer.start(AUTO_COLLAPSE_MS)
        else:
            self._auto_collapse_timer.stop()

        if self._require_click_after_idle:
            self._idle_timer.start(LONG_IDLE_MS)
        else:
            self._idle_timer.stop()

    def _on_auto_collapse_timeout(self) -> None:
        if self._docked_side and self._expanded:
            self._set_expanded(False)

    def _on_long_idle_timeout(self) -> None:
        self._long_idle_mode = True

    def _set_expanded(self, expanded: bool) -> None:
        if self._expanded == expanded or not self._docked_side:
            return
        self._expanded = expanded

        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()

        # The size should always be the full widget width now.
        self.setFixedSize(WIDGET_WIDTH, WIDGET_HEIGHT)

        start_pos = self.pos()
        end_pos = None

        if self._docked_side == "right":
            end_x = geo.right() - (WIDGET_WIDTH if expanded else WIDGET_COLLAPSED_WIDTH)
            end_pos = QPoint(end_x, self.y())
        elif self._docked_side == "left":
            end_x = geo.left() - (0 if expanded else WIDGET_WIDTH - WIDGET_COLLAPSED_WIDTH)
            end_pos = QPoint(end_x, self.y())

        if end_pos and start_pos != end_pos:
            anim = QPropertyAnimation(self, b"pos")
            anim.setDuration(ANIM_DURATION_MEDIUM)
            anim.setStartValue(start_pos)
            anim.setEndValue(end_pos)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_active:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drag_active:
            self._drag_active = False
            self._dock_to_nearest_edge()
            self._restart_idle_timers()
            event.accept()
        super().mouseReleaseEvent(event)

    def enterEvent(self, event) -> None:
        if self._docked_side and not self._expanded:
            if self._hover_expand_enabled:
                self._set_expanded(True)
        self._restart_idle_timers()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._restart_idle_timers()
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        # When long idle mode is active, double-click (or click) can expand even if hover is disabled.
        if event.button() == Qt.MouseButton.LeftButton and self._docked_side:
            self._long_idle_mode = False
            self._set_expanded(True)
            self._restart_idle_timers()
        super().mouseDoubleClickEvent(event)

    def _dock_to_nearest_edge(self) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        center_x = self.frameGeometry().center().x()

        # choose left or right
        if center_x < geo.center().x():
            # dock left
            self._docked_side = "left"
            self.move(geo.left(), self.y())
        else:
            # dock right
            self._docked_side = "right"
            self.move(geo.right() - self.width(), self.y())

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
