from __future__ import annotations
import math
import random
import html
from typing import Any, Dict, List, Optional, Callable

from PyQt6.QtCore import Qt, QSize, QPoint, QTimer, QPointF, pyqtSignal, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PyQt6.QtGui import QPainter, QColor, QCursor
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QGraphicsOpacityEffect

from core.model import (
    GOLD,
    DARK_BG,
    CARD_BG,
    HOVER_BG,
    TEXT_WHITE,
    TEXT_GRAY,
)

class AnimationManager:
    """
    Centralized manager for UI animations to ensure consistency and resource cleanup.
    Prevents painter conflicts by properly managing QGraphicsOpacityEffect.
    """
    
    @staticmethod
    def fade_in(widget: QWidget, duration: int = 250, delay: int = 0, on_finished: Optional[Callable] = None):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        
        anim = QPropertyAnimation(effect, b"opacity", widget)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        def cleanup():
            # It's possible the widget is destroyed before the animation finishes.
            # Check if the widget and its effect still exist.
            if widget and widget.graphicsEffect() is effect:
                widget.setGraphicsEffect(None)
            if on_finished:
                on_finished()
        
        anim.finished.connect(cleanup)
        
        if delay > 0:
            def safe_start():
                try:
                    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
                except RuntimeError:
                    pass
            QTimer.singleShot(delay, safe_start)
        else:
            anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        return anim

    @staticmethod
    def slide_and_fade_out(widget: QWidget, duration: int = 250, on_finished: Optional[Callable] = None):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        
        group = QParallelAnimationGroup(widget)
        
        anim_fade = QPropertyAnimation(effect, b"opacity")
        anim_fade.setDuration(duration)
        anim_fade.setStartValue(1.0)
        anim_fade.setEndValue(0.0)
        anim_fade.setEasingCurve(QEasingCurve.Type.InQuad)
        
        anim_size = QPropertyAnimation(widget, b"maximumHeight")
        anim_size.setDuration(duration)
        anim_size.setStartValue(widget.height())
        anim_size.setEndValue(0)
        anim_size.setEasingCurve(QEasingCurve.Type.InCubic)
        
        group.addAnimation(anim_fade)
        group.addAnimation(anim_size)
        
        def cleanup():
            widget.hide()
            widget.setMaximumHeight(16777215) # Restore max height
            widget.setGraphicsEffect(None)
            if on_finished:
                on_finished()

        group.finished.connect(cleanup)
        group.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        return group

class TaskRowWidget(QWidget):
    """A standardized task row widget that emits signals for interactions."""
    toggled = pyqtSignal(str)
    deleted = pyqtSignal(str)
    contextMenuRequested = pyqtSignal(QPoint, str)
    editRequested = pyqtSignal(str)
    focusRequested = pyqtSignal(str)

    def __init__(self, task: Dict[str, Any], show_delete_button: bool = True, show_focus_button: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.task = task
        self.task_id = task.get("id")
        self._build_ui(show_delete_button, show_focus_button)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._emit_context_menu)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.editRequested.emit(self.task_id)

    def _emit_context_menu(self, pos: QPoint):
        self.contextMenuRequested.emit(pos, self.task_id)

    def _build_ui(self, show_delete_button: bool, show_focus_button: bool):
        self.setObjectName("TaskRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        important_style = f"border-left: 3px solid {GOLD};" if self.task.get("important") else "border-left: 3px solid transparent;"
        self.setStyleSheet(f"""
            #TaskRow {{
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 0.02);
                {important_style}
            }}
            #TaskRow:hover {{ background-color: {HOVER_BG}; }}
        """)
        
        hl = QHBoxLayout(self)
        hl.setContentsMargins(6, 2, 6, 2)
        hl.setSpacing(6)

        chk = QPushButton("✔" if self.task.get("completed") else "")
        chk.setFixedSize(QSize(22, 22))
        chk.setCheckable(True)
        chk.setChecked(self.task.get("completed", False))
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

        text_content = self.task.get("text", "")
        meta_info = []
        if sched := self.task.get("schedule"):
            if isinstance(sched, dict) and sched.get("date"):
                date_str = sched['date']
                if sched.get("time"):
                    date_str += f" @ {sched['time']}"
                meta_info.append(f"📅 {date_str}")
        if rec := self.task.get("recurrence"):
            if isinstance(rec, dict) and rec.get("type"):
                meta_info.append(f"↻ {rec['type']}")
        if cat := self.task.get("category"):
            meta_info.append(f"🏷 {cat}")

        lbl = QLabel()
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {TEXT_GRAY if self.task.get('completed') else (GOLD if self.task.get('important') else TEXT_WHITE)};" + ("text-decoration: line-through;" if self.task.get('completed') else ""))
        lbl.setToolTip(text_content)
        
        lbl.setText(f"{html.escape(text_content)}<br><span style='color:{TEXT_GRAY}; font-size:10px;'>{'  '.join(meta_info)}</span>" if meta_info else html.escape(text_content))

        focus_btn = QPushButton("👁")
        focus_btn.setFixedSize(QSize(24, 24))
        focus_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        focus_btn.setToolTip("Focus on this task (Zen Mode)")
        focus_btn.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {TEXT_GRAY}; font-size: 14px; }} QPushButton:hover {{ color: {GOLD}; }}")
        focus_btn.setVisible(not self.task.get("completed") and show_focus_button)

        del_btn = QPushButton("×")
        del_btn.setFixedSize(QSize(24, 24))
        del_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        del_btn.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {TEXT_GRAY}; font-weight: bold; font-size: 14px; }} QPushButton:hover {{ color: {GOLD}; }}")
        del_btn.setVisible(show_delete_button)

        hl.addWidget(chk)
        hl.addWidget(lbl, 1)
        hl.addWidget(focus_btn)
        hl.addWidget(del_btn)

        chk.clicked.connect(lambda: self.toggled.emit(self.task_id))
        focus_btn.clicked.connect(lambda: self.focusRequested.emit(self.task_id))
        del_btn.clicked.connect(lambda: self.deleted.emit(self.task_id))

class ConfettiOverlay(QWidget):
    """
    A transparent overlay that renders a particle burst effect.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.particles = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update)

    def burst(self):
        self.particles.clear()
        cx = self.width() / 2
        cy = self.height() / 2
        for _ in range(60):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(5, 12)
            self.particles.append({
                "x": cx, "y": cy,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed - 4, # Upward bias
                "color": QColor.fromHsv(random.randint(0, 359), 200, 255),
                "size": random.randint(4, 8),
                "decay": random.uniform(0.92, 0.96)
            })
        self.timer.start(16)
        self.show()
        self.raise_()

    def _update(self):
        if not self.particles:
            self.timer.stop()
            self.hide()
            return
        
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.5 # Gravity
            p["vx"] *= p["decay"] # Air resistance
            
        self.particles = [p for p in self.particles if p["y"] < self.height() + 10]
        self.update()

    def paintEvent(self, event):
        if not self.particles: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for p in self.particles:
            painter.setBrush(p["color"])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(p["x"], p["y"]), p["size"]/2, p["size"]/2)