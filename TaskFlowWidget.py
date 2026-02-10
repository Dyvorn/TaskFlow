from __future__ import annotations

import sys
from typing import Any, Dict, Optional

from PyQt6.QtCore import (
    Qt,
    QTimer,
    QSize,
    QPoint,
    QPropertyAnimation,
    QEasingCurve,
)
from PyQt6.QtGui import QColor, QMouseEvent
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
    QStackedWidget,
    QTextEdit,
    QSizePolicy,
    QGraphicsOpacityEffect,
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
    get_data_paths,
    load_state,
    save_state,
    tasks_in_section,
    toggle_task_completed,
    get_today_mood,
    tasks_for_project,
    get_today_widget_note,
    set_today_widget_note,
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

    def __init__(self, state: Dict[str, Any], paths: Dict[str, str]) -> None:
        super().__init__(flags=Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.state = state
        self.paths = paths

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

        # If no mood yet today, show a tiny supportive hint
        if get_today_mood(self.state) is None:
            self.suggestion_label.setText(
                "How are you today? You can check in from the hub’s Stats page."
            )

        self._note_save_timer = QTimer(self)
        self._note_save_timer.setSingleShot(True)
        self._note_save_timer.setInterval(800)
        self._note_save_timer.timeout.connect(self._save_notes)

        self.notes_edit.textChanged.connect(self._on_notes_changed)

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

        self.suggestion_label = QLabel("")
        self.suggestion_label.setWordWrap(True)
        self.suggestion_label.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 11px;")
        header_row.addWidget(self.suggestion_label, 2)

        card_layout.addLayout(header_row)

        # Tabs: Tasks / Notes
        tabs_row = QHBoxLayout()
        tabs_row.setSpacing(4)

        self.btn_tab_tasks = QPushButton("Tasks")
        self.btn_tab_notes = QPushButton("Notes")
        self.btn_tab_tasks.setCheckable(True)
        self.btn_tab_notes.setCheckable(True)
        self.btn_tab_tasks.setChecked(True)

        self.btn_tab_tasks.clicked.connect(lambda: self._set_tab("tasks"))
        self.btn_tab_notes.clicked.connect(lambda: self._set_tab("notes"))

        tabs_row.addWidget(self.btn_tab_tasks)
        tabs_row.addWidget(self.btn_tab_notes)

        card_layout.addLayout(tabs_row)

        # stacked content
        self.stack = QStackedWidget()
        card_layout.addWidget(self.stack, 1)

        # Tasks page
        self.page_tasks = QWidget()
        pt_layout = QVBoxLayout(self.page_tasks)
        pt_layout.setContentsMargins(0, 4, 0, 0)
        pt_layout.setSpacing(4)

        self.tasks_list = QListWidget()
        self.tasks_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        pt_layout.addWidget(self.tasks_list, 1)

        self.show_more_button = QPushButton("Show more")
        self.show_more_button.clicked.connect(self._on_show_more)
        self.show_more_button.setVisible(False)
        pt_layout.addWidget(self.show_more_button)

        self.stack.addWidget(self.page_tasks)

        # Notes page
        self.page_notes = QWidget()
        pn_layout = QVBoxLayout(self.page_notes)
        pn_layout.setContentsMargins(0, 4, 0, 0)
        pn_layout.setSpacing(4)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            "Write a few words about what you’re doing or how it feels."
        )
        self.notes_edit.setPlainText(get_today_widget_note(self.state))
        pn_layout.addWidget(self.notes_edit, 1)

        self.stack.addWidget(self.page_notes)

        outer.addWidget(card)

    # ────────────────────────────────────────────────────────────────────
    # Tabs
    # ────────────────────────────────────────────────────────────────────

    def _set_tab(self, which: str) -> None:
        self._restart_idle_timers()
        if which == "tasks":
            self.btn_tab_tasks.setChecked(True)
            self.btn_tab_notes.setChecked(False)
            self.stack.setCurrentWidget(self.page_tasks)
        else:
            self.btn_tab_tasks.setChecked(False)
            self.btn_tab_notes.setChecked(True)
            self.stack.setCurrentWidget(self.page_notes)

    def _on_notes_changed(self) -> None:
        self._restart_idle_timers()
        self._note_save_timer.start()

    def _save_notes(self) -> None:
        text = self.notes_edit.toPlainText().strip()
        set_today_widget_note(self.state, text)
        save_state(self.paths, self.state)

    # ────────────────────────────────────────────────────────────────────
    # Tasks + suggestion
    # ────────────────────────────────────────────────────────────────────

    def _refresh_tasks(self) -> None:
        self.tasks_list.clear()

        # Today tasks
        today_tasks = tasks_in_section(self.state, "Today")

        # Current project tasks
        proj_id = self.state.get("widgetCurrentProjectId")
        project_tasks = tasks_for_project(self.state, proj_id) if proj_id else []

        # Combine lists with tags
        combined: list[dict[str, Any]] = []
        for t in today_tasks:
            combined.append({"task": t, "kind": "today"})
        for t in project_tasks:
            combined.append({"task": t, "kind": "project"})

        max_visible = 10  # e.g. 5+5; tune as you like
        visible = combined[:max_visible]
        has_more = len(combined) > max_visible

        for entry in visible:
            t = entry["task"]
            kind = entry["kind"]

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
            if kind == "project":
                text = f"[Proj] {text}"

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

        self.show_more_button.setVisible(has_more)

        # Suggestion line
        self._update_suggestion_line(today_tasks)

    def _on_show_more(self) -> None:
        self._restart_idle_timers()

        today_tasks = tasks_in_section(self.state, "Today")
        proj_id = self.state.get("widgetCurrentProjectId")
        project_tasks = tasks_for_project(self.state, proj_id) if proj_id else []

        combined: list[dict[str, Any]] = []
        for t in today_tasks:
            combined.append({"task": t, "kind": "today"})
        for t in project_tasks:
            combined.append({"task": t, "kind": "project"})

        self.tasks_list.clear()
        for entry in combined:
            t = entry["task"]
            kind = entry["kind"]

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
            if kind == "project":
                text = f"[Proj] {text}"

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

        self.show_more_button.setVisible(False)
        self._update_suggestion_line(today_tasks)

    def _on_toggle_task(self, task_id: str) -> None:
        toggle_task_completed(self.state, task_id)
        save_state(self.paths, self.state)
        self._refresh_tasks()
        self._restart_idle_timers()

    def _update_suggestion_line(self, tasks: list[Dict[str, Any]]) -> None:
        if not tasks:
            self.suggestion_label.setText(
                "No tasks for Today. You can keep it light or add one tiny thing in the hub."
            )
            return

        candidates = [t for t in tasks if not t.get("completed")]
        if not candidates:
            self.suggestion_label.setText(
                "Nothing urgent left for Today. Rest is allowed."
            )
            return

        candidates.sort(
            key=lambda t: (
                0 if t.get("important") else 1,
                t.get("order", 0),
            )
        )
        next_task = candidates[0]
        mood = get_today_mood(self.state)
        mood_value = (mood or {}).get("value", "Okay")

        if mood_value in ("Low energy", "Stressed"):
            prefix = "Gentle step: "
        elif mood_value in ("Motivated", "Great"):
            prefix = "You’re on a roll: "
        else:
            prefix = "Next good move: "

        self.suggestion_label.setText(f"{prefix}{next_task.get('text', '')}")

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
        if self._expanded == expanded:
            return
        self._expanded = expanded

        start_w = self.width()
        end_w = WIDGET_WIDTH if expanded else WIDGET_COLLAPSED_WIDTH

        anim = QPropertyAnimation(self, b"size")
        anim.setDuration(200)
        anim.setStartValue(QSize(start_w, self.height()))
        anim.setEndValue(QSize(end_w, self.height()))
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
            if not self._long_idle_mode and self._hover_expand_enabled:
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
        save_state(self.paths, self.state)
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    paths = get_data_paths()
    state = load_state(paths)

    widget = WidgetWindow(state, paths)
    widget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
