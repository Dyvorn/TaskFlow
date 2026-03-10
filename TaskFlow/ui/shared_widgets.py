from __future__ import annotations
import math
import random
import html
from typing import Any, Dict, List, Optional, Callable

from PyQt6.QtCore import Qt, QSize, QPoint, QTimer, QPointF, pyqtSignal, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QVariantAnimation, QRectF
from PyQt6.QtGui import QPainter, QColor, QCursor, QPen, QBrush
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QGraphicsOpacityEffect, QFrame

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

class AnimatedCheckbox(QPushButton):
    """A custom checkbox with a smooth fill animation."""
    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        super().setChecked(checked)
        self.setFixedSize(24, 24)
        self.setText("")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Animation state (0.0 = empty, 1.0 = filled)
        self._anim_value = 1.0 if checked else 0.0
        
        self._anim = QVariantAnimation()
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._anim.valueChanged.connect(self._update_anim)

    def setChecked(self, checked: bool):
        if checked != self.isChecked():
            self._anim.stop()
            self._anim.setStartValue(self._anim_value)
            self._anim.setEndValue(1.0 if checked else 0.0)
            self._anim.start()
        super().setChecked(checked)

    def nextCheckState(self):
        super().nextCheckState()
        self.setChecked(self.isChecked())

    def _update_anim(self, val):
        self._anim_value = val
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not painter.isActive():
            return
            
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        center = QPointF(rect.center())
        radius = (min(rect.width(), rect.height()) / 2) - 2
        
        # Draw ring
        painter.setPen(QPen(QColor(GOLD), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius, radius)
        
        # Draw fill
        if self._anim_value > 0.05:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(GOLD))
            r = radius * self._anim_value
            painter.drawEllipse(center, r, r)
            
            # Draw checkmark
            if self._anim_value > 0.6:
                painter.setPen(QPen(QColor(DARK_BG), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                # Simple checkmark coordinates
                p1 = QPointF(center.x() - 3, center.y())
                p2 = QPointF(center.x() - 1, center.y() + 3)
                p3 = QPointF(center.x() + 4, center.y() - 3)
                painter.drawLine(p1, p2)
                painter.drawLine(p2, p3)
        painter.end()

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

        chk = AnimatedCheckbox(checked=self.task.get("completed", False))
        # No stylesheet needed for AnimatedCheckbox as it paints itself

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

        self._apply_decorations()

    def _apply_decorations(self):
        """Adds visual indicators (difficulty, duration) to the task row."""
        # Difficulty
        difficulty = self.task.get("difficulty", 1)
        if difficulty > 2:
            self.difficulty_indicator = QFrame(self)
            self.difficulty_indicator.setFixedSize(4, 18)
            
            color = GOLD
            tooltip = "Difficulty: Medium"
            if difficulty == 4:
                color = "#f39c12" # Orange
                tooltip = "Difficulty: Hard"
            elif difficulty >= 5:
                color = "#e74c3c" # Red
                tooltip = "Difficulty: Epic"
            
            self.difficulty_indicator.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
            self.difficulty_indicator.setToolTip(tooltip)
            self.difficulty_indicator.show()
        else:
            self.difficulty_indicator = None

        # Duration
        duration = self.task.get("estimatedDuration", 0)
        if duration > 0:
            layout = self.layout()
            if layout:
                lbl = QLabel(f"⏱ {duration}m")
                lbl.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 11px; margin-right: 8px; background: transparent;")
                layout.insertWidget(2, lbl)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'difficulty_indicator') and self.difficulty_indicator:
             self.difficulty_indicator.move(6, (self.height() - 18) // 2)

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
        if not painter.isActive():
            return
            
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for p in self.particles:
            painter.setBrush(p["color"])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(p["x"], p["y"]), p["size"]/2, p["size"]/2)
        painter.end()