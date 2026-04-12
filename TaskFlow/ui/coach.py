import random
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QInputDialog, QSizePolicy, QLineEdit, QComboBox,
    QSpacerItem
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import QCursor, QPainter, QColor, QPen,  QFont

# Theme constants (matching hub.py)
TEXT_WHITE = "#ffffff"
TEXT_GRAY = "#a0a0a0"
GOLD = "#ffd700"
HOVER_BG = "rgba(255, 255, 255, 0.1)"
GLASS_BORDER = "rgba(255, 255, 255, 0.15)"
DARK_BG = "#121212"

class ReviewItemWidget(QWidget):
    """Custom card for items in the AI review queue."""
    action_taken = pyqtSignal(str, dict) # 'confirm' or 'correct', and the item data

    def __init__(self, item_data: dict, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Task Text
        lbl_task = QLabel(f"“{item_data['text']}”")
        lbl_task.setStyleSheet(f"color: {TEXT_WHITE}; font-weight: bold; font-size: 13px;")
        layout.addWidget(lbl_task)

        # Prediction Info
        info_layout = QHBoxLayout()
        conf = int(item_data['confidence'] * 100)
        conf_color = "#1dd1a1" if conf > 70 else ("#feca57" if conf > 40 else "#ff6b6b")
        
        lbl_guess = QLabel(f"Guess: {item_data['predicted_category']}")
        lbl_guess.setStyleSheet(f"color: {TEXT_GRAY}; font-size: 11px;")
        
        lbl_conf = QLabel(f"{conf}% match")
        lbl_conf.setStyleSheet(f"color: {conf_color}; font-size: 11px; font-weight: bold;")
        
        # Visual meter
        meter = QProgressBar()
        meter.setFixedHeight(3)
        meter.setRange(0, 100)
        meter.setValue(conf)
        meter.setTextVisible(False)
        meter.setStyleSheet(f"QProgressBar {{ background: rgba(255,255,255,0.05); border: none; }} QProgressBar::chunk {{ background: {conf_color}; }}")
        
        info_layout.addWidget(lbl_guess)
        info_layout.addStretch()
        info_layout.addWidget(lbl_conf)
        layout.addLayout(info_layout)
        layout.addWidget(meter)

        # --- Action Buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 4, 0, 0)
        btn_layout.addStretch()

        btn_confirm = QPushButton("✅ Confirm")
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_confirm.setStyleSheet(f"color: #1dd1a1; background: transparent; border: none; font-weight: bold;")
        btn_confirm.clicked.connect(lambda: self.action_taken.emit('confirm', item_data))
        btn_layout.addWidget(btn_confirm)

        btn_correct = QPushButton("✏️ Correct")
        btn_correct.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_correct.setStyleSheet(f"color: #feca57; background: transparent; border: none; font-weight: bold;")
        btn_correct.clicked.connect(lambda: self.action_taken.emit('correct', item_data))
        btn_layout.addWidget(btn_correct)

        layout.addLayout(btn_layout)

class SuggestionWidget(QFrame):
    """A custom widget to display an AI suggestion with action buttons."""
    action_taken = pyqtSignal(str, dict) # "accept" or "dismiss", suggestion data

    def __init__(self, suggestion: dict, parent=None):
        super().__init__(parent)
        self.suggestion = suggestion
        self.setObjectName("SuggestionCard")
        
        # Distinct accent colors based on suggestion type
        accent_map = {
            'WELLBEING_CHECK': "#ff6b6b",
            'SUGGEST_RESCHEDULE': "#4facfe",
            'SUGGEST_BREAKDOWN_STUCK_TASK': GOLD,
            'SUGGEST_RECURRENCE': "#1dd1a1",
            'FORCED_BREAK': "#9b59b6" # Purple for rest
        }
        accent_color = accent_map.get(suggestion['type'], GLASS_BORDER)
        
        self.setStyleSheet(f"""
            #SuggestionCard {{ 
                background-color: rgba(255, 255, 255, 0.05); 
                border-radius: 12px; 
                padding: 14px; 
                border-left: 4px solid {accent_color};
            }}
        """)

        layout = QVBoxLayout(self)
        
        # Build text based on type
        s_type = suggestion['type']
        icon_map = {
            'SUGGEST_RECURRENCE': "🔄",
            'WELLBEING_CHECK': "🌿",
            'REVIEW_STALE_TASKS': "🧹",
            'SUGGEST_BREAKDOWN_STUCK_TASK': "💎",
            'SUGGEST_RESCHEDULE': "📅",
            'FORCED_BREAK': "🧘"
        }
        icon = icon_map.get(s_type, "💡")

        if s_type == 'SUGGEST_RECURRENCE':
            text = f"I noticed you often complete <b>'{suggestion['task_text']}'</b>. Make it recurring?"
            accept_text = "Create"
        elif s_type == 'WELLBEING_CHECK':
            text = suggestion.get('text', "How are you feeling?")
            accept_text = "Check-in"
        elif s_type == 'REVIEW_STALE_TASKS':
            text = suggestion.get('text', "Review some old items?")
            accept_text = "Review"
        elif s_type == 'SUGGEST_BREAKDOWN_STUCK_TASK':
            text = suggestion.get('text', "Break down this complex task?")
            accept_text = "Analyze"
        elif s_type == 'SUGGEST_RESCHEDULE':
            text = suggestion.get('text', "Move some tasks to tomorrow?")
            accept_text = "Reschedule"
        elif s_type == 'FORCED_BREAK':
            text = suggestion.get('text', "Take a forced break?")
            accept_text = "Rest Now"
        else:
            text = suggestion.get('text', "I have a suggestion.")
            accept_text = "Accept"
            
        lbl_text = QLabel(f"{icon}  {text}")
        lbl_text.setWordWrap(True)
        lbl_text.setStyleSheet(f"color: {TEXT_WHITE}; background: transparent;")
        layout.addWidget(lbl_text)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_accept = QPushButton(accept_text)
        btn_accept.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_accept.setStyleSheet(f"background-color: {accent_color}; color: {DARK_BG}; font-weight: bold; border: none; padding: 6px 12px; border-radius: 8px;")
        btn_accept.clicked.connect(lambda: self.action_taken.emit("accept", self.suggestion))
        
        btn_dismiss = QPushButton("Dismiss")
        btn_dismiss.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dismiss.setStyleSheet(f"color: {TEXT_GRAY}; background: transparent; border: none;")
        btn_dismiss.clicked.connect(lambda: self.action_taken.emit("dismiss", self.suggestion))
        
        btn_layout.addWidget(btn_accept)
        btn_layout.addWidget(btn_dismiss)
        layout.addLayout(btn_layout)

class BrainVisualizer(QWidget):
    """
    A structural visualization of the TaskBrain architecture.
    Shows input features, hidden layers, and multi-head outputs.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.layers = [] # List of lists of nodes
        self._is_thinking = False
        self._pulse_offset = 0.0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_nodes)
        self.timer.start(30) # ~33 FPS

    def set_thinking(self, thinking: bool):
        self._is_thinking = thinking

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.init_nodes()

    def init_nodes(self):
        self.layers = []
        w, h = self.width(), self.height()
        if w < 100 or h < 100: return

        # Define Layer Structure: [Input, Hidden, Output]
        # Input: 1 Text, 3 Context features
        # Hidden: 10 neurons
        # Output: 3 heads (Cat, Comp, Dur)
        layer_counts = [4, 10, 3]
        layer_labels = [
            ["Text", "Time", "Day", "Mood"],
            ["" for _ in range(10)],
            ["Category", "Complexity", "Duration"]
        ]
        
        margin = 40
        layer_x_dist = (w - (2 * margin)) / (len(layer_counts) - 1)

        for i, count in enumerate(layer_counts):
            layer_nodes = []
            x = margin + (i * layer_x_dist)
            
            # Vertical spacing
            v_space = (h - (2 * margin)) / (count + 1)
            for j in range(count):
                y = margin + ((j + 1) * v_space)
                layer_nodes.append({
                    'pos': QPointF(x, y),
                    'size': 6 if i != 1 else 4,
                    'label': layer_labels[i][j]
                })
            self.layers.append(layer_nodes)

    def update_nodes(self):
        if self._is_thinking:
            self._pulse_offset += 0.08
            if self._pulse_offset > 1.0:
                self._pulse_offset = 0.0
        else:
            self._pulse_offset = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if not self.layers: return

        # 1. Draw Synapses (Connections)
        for i in range(len(self.layers) - 1):
            curr_layer = self.layers[i]
            next_layer = self.layers[i + 1]
            
            for n1 in curr_layer:
                for n2 in next_layer:
                    # Base line
                    color = QColor(GOLD if not self._is_thinking else "#00f2fe")
                    alpha = 40 if not self._is_thinking else 70
                    color.setAlpha(alpha)
                    painter.setPen(QPen(color, 1))
                    painter.drawLine(n1['pos'], n2['pos'])

                    # Signal Pulse (when thinking)
                    if self._is_thinking:
                        p1 = n1['pos']
                        p2 = n2['pos']
                        # Interpolate position
                        pulse_pos = p1 + (p2 - p1) * self._pulse_offset
                        painter.setPen(QPen(QColor("#00f2fe"), 2))
                        painter.drawPoint(pulse_pos)

        # 2. Draw Neurons (Nodes)
        font = QFont("Segoe UI", 8)
        painter.setFont(font)

        for i, layer in enumerate(self.layers):
            for node in layer:
                color = QColor(GOLD if not self._is_thinking else "#00f2fe")
                painter.setBrush(color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(node['pos'], node['size'], node['size'])
                
                # Label for Input/Output layers
                if node['label']:
                    painter.setPen(QColor(TEXT_GRAY))
                    label_rect = QRectF(node['pos'].x() - 40, node['pos'].y() + 8, 80, 20)
                    painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, node['label'])

        # Layer Descriptors
        painter.setPen(QColor(TEXT_GRAY))
        painter.setOpacity(0.5)
        painter.drawText(int(self.layers[0][0]['pos'].x() - 20), 25, "INPUT")
        painter.drawText(int(self.layers[1][0]['pos'].x() - 20), 25, "HIDDEN")
        painter.drawText(int(self.layers[2][0]['pos'].x() - 20), 25, "OUTPUT")


class CoachWidget(QWidget):
    """
    The AI Coach interface.
    Allows the user to:
    1. See the status of their Neural Network.
    2. Manually trigger training.
    3. Review and answer 'questions' (low-confidence predictions) to teach the AI.
    """
    message_requested = pyqtSignal(str)

    def __init__(self, ai_engine, parent=None):
        super().__init__(parent)
        self.ai_engine = ai_engine
        self._build_ui()
        self.refresh()
        if self.ai_engine:
            self.ai_engine.status_changed.connect(self._on_ai_status_changed)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        header = QLabel("AI Coach 🤖")
        header.setStyleSheet(f"color: {GOLD}; font-size: 24px; font-weight: bold;")
        layout.addWidget(header)

        # Neural Visualizer
        self.visualizer = BrainVisualizer()
        layout.addWidget(self.visualizer)

        # --- Stats Card ---
        stats_card = QFrame()
        stats_card.setObjectName("GlassCard")
        stats_card.setStyleSheet(f"#GlassCard {{ background-color: rgba(0,0,0,0.2); border: 1px solid {GLASS_BORDER}; border-radius: 16px; }}")
        s_layout = QVBoxLayout(stats_card)
        s_layout.setContentsMargins(20, 20, 20, 20)
        
        self.lbl_status = QLabel("Brain Status: Unknown")
        self.lbl_status.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 16px;")
        s_layout.addWidget(self.lbl_status)
        
        self.lbl_vocab = QLabel("Vocabulary: 0 words")
        self.lbl_vocab.setStyleSheet(f"color: {TEXT_GRAY};")
        s_layout.addWidget(self.lbl_vocab)

        self.lbl_samples = QLabel("Training Samples: 0")
        self.lbl_samples.setStyleSheet(f"color: {TEXT_GRAY};")
        s_layout.addWidget(self.lbl_samples)

        self.lbl_agreement = QLabel("Agreement: N/A")
        self.lbl_agreement.setStyleSheet(f"color: {TEXT_GRAY};")
        s_layout.addWidget(self.lbl_agreement)

        s_layout.addSpacing(10)
        s_layout.addWidget(QLabel("Neural Maturity:"))
        self.maturity_bar = QProgressBar()
        self.maturity_bar.setFixedHeight(6)
        self.maturity_bar.setStyleSheet(f"QProgressBar {{ background: rgba(255,255,255,0.05); border: none; border-radius: 3px; }} QProgressBar::chunk {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4facfe, stop:1 #00f2fe); border-radius: 3px; }}")
        s_layout.addWidget(self.maturity_bar)

        s_layout.addSpacing(10)
        
        self.train_progress = QProgressBar()
        self.train_progress.setTextVisible(False)
        self.train_progress.setFixedHeight(8)
        self.train_progress.setStyleSheet(f"QProgressBar {{ border: none; background-color: {HOVER_BG}; border-radius: 4px; }} QProgressBar::chunk {{ background-color: {GOLD}; border-radius: 4px; }}")
        self.train_progress.hide()
        s_layout.addWidget(self.train_progress)
        
        self.btn_train = QPushButton("Train Brain Now")
        self.btn_train.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_train.setStyleSheet(f"background-color: {HOVER_BG}; color: {TEXT_WHITE}; border: 1px solid {GLASS_BORDER}; border-radius: 6px; padding: 8px;")
        self.btn_train.clicked.connect(self._run_training)
        s_layout.addWidget(self.btn_train)

        self.btn_reset_brain = QPushButton("Reset Brain")
        self.btn_reset_brain.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset_brain.setStyleSheet(f"background-color: transparent; color: #ff6b6b; border: 1px solid #ff6b6b; border-radius: 6px; padding: 8px;")
        self.btn_reset_brain.clicked.connect(self._reset_brain)
        s_layout.addWidget(self.btn_reset_brain)

        layout.addWidget(stats_card)

        # --- Manual Teach Card ---
        teach_card = QFrame()
        teach_card.setObjectName("GlassCard")
        teach_card.setStyleSheet(f"#GlassCard {{ background-color: rgba(0,0,0,0.2); border: 1px solid {GLASS_BORDER}; border-radius: 16px; }}")
        t_layout = QVBoxLayout(teach_card)
        t_layout.setContentsMargins(20, 20, 20, 20)
        t_layout.setSpacing(12)
        
        lbl_teach_title = QLabel("Proactive Training (Manual Teach)")
        lbl_teach_title.setStyleSheet(f"color: {TEXT_WHITE}; font-size: 16px; font-weight: bold;")
        t_layout.addWidget(lbl_teach_title)
        
        self.teach_input = QLineEdit()
        self.teach_input.setPlaceholderText("Enter a task example (e.g. 'Fix server bug')")
        self.teach_input.setStyleSheet(f"background-color: rgba(0,0,0,0.3); color: {TEXT_WHITE}; border: 1px solid {GLASS_BORDER}; border-radius: 8px; padding: 10px;")
        t_layout.addWidget(self.teach_input)
        
        teach_row = QHBoxLayout()
        self.teach_cat_combo = QComboBox()
        self.teach_cat_combo.setStyleSheet(f"background-color: rgba(0,0,0,0.3); color: {TEXT_WHITE}; border: 1px solid {GLASS_BORDER}; border-radius: 8px; padding: 6px;")
        
        self.teach_diff_combo = QComboBox()
        self.teach_diff_combo.addItems(["1 (Easy)", "2", "3 (Medium)", "4", "5 (Epic)"])
        self.teach_diff_combo.setStyleSheet(f"background-color: rgba(0,0,0,0.3); color: {TEXT_WHITE}; border: 1px solid {GLASS_BORDER}; border-radius: 8px; padding: 6px;")
        
        teach_row.addWidget(QLabel("Category:"), 0)
        teach_row.addWidget(self.teach_cat_combo, 1)
        teach_row.addWidget(QLabel("Difficulty:"), 0)
        teach_row.addWidget(self.teach_diff_combo, 1)
        t_layout.addLayout(teach_row)
        
        btn_teach_submit = QPushButton("Teach Neural Brain")
        btn_teach_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_teach_submit.setStyleSheet(f"background-color: {GOLD}; color: {DARK_BG}; font-weight: bold; border-radius: 8px; padding: 10px;")
        btn_teach_submit.clicked.connect(self._on_manual_teach)
        t_layout.addWidget(btn_teach_submit)
        
        layout.addWidget(teach_card)

        # --- Review Queue ---
        layout.addWidget(QLabel("Review Queue (Teach me!)"))
        
        self.review_list = QListWidget()
        self.review_list.setStyleSheet(f"background-color: rgba(0,0,0,0.2); border: 1px solid {GLASS_BORDER}; border-radius: 12px; color: {TEXT_WHITE};")
        layout.addWidget(self.review_list, 1)
        
        # --- AI Recommendations ---
        layout.addSpacing(15)
        layout.addWidget(QLabel("AI Recommendations"))
        self.recommendations_list = QListWidget()
        layout.addWidget(self.recommendations_list, 1)

    def _on_ai_status_changed(self, status: str):
        is_busy = status != "Ready"
        self.visualizer.set_thinking(is_busy)

    def refresh(self, state: dict = None):
        if not self.ai_engine:
            self.lbl_status.setText("Brain Status: Offline (Debug)")
            self.lbl_vocab.setText("Vocabulary: -")
            self.lbl_samples.setText("Training Samples: -")
            self.review_list.clear()
            self.review_list.addItem("AI Engine not connected.")
            self.recommendations_list.clear()
            self.recommendations_list.addItem("No recommendations.")
            self.btn_train.setEnabled(False)
            return

        # Update Stats
        stats = self.ai_engine.get_stats()
        self.lbl_status.setText(f"Brain Status: {stats['status']}")
        self.lbl_vocab.setText(f"Vocabulary: {stats['vocab_size']} words")
        self.lbl_samples.setText(f"Training Samples: {stats['task_log_count']}")
        self.lbl_agreement.setText(f"Agreement Rate: {stats.get('agreement_rate', 0):.1f}%")
        
        # Update Maturity Meter
        samples = stats.get('task_log_count', 0)
        vocab = stats.get('vocab_size', 0)
        maturity = min(100, (vocab / 200 * 50) + (samples / 50 * 50))
        self.maturity_bar.setValue(int(maturity))

        # Update Manual Teach Categories
        self.teach_cat_combo.clear()
        cats = self.ai_engine.get_all_categories()
        if cats:
            self.teach_cat_combo.addItems(cats)

        # Update Review Queue
        self.review_list.clear()
        queue = self.ai_engine.get_review_queue()
        
        if not queue:
            self.review_list.addItem("No pending questions. Good job!")
        else:
            for item in queue:
                list_item = QListWidgetItem()
                widget = ReviewItemWidget(item)
                widget.action_taken.connect(self._handle_review_action)
                list_item.setData(Qt.ItemDataRole.UserRole, item)
                list_item.setSizeHint(widget.sizeHint())
                self.review_list.addItem(list_item)
                self.review_list.setItemWidget(list_item, widget)
                
        # Update Recommendations
        self.recommendations_list.clear()
        suggestions = []
        if state:
            suggestions = self.ai_engine.get_proactive_suggestions(state)

        if not suggestions:
            item = QListWidgetItem("No recommendations right now. Keep using the app!")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.recommendations_list.addItem(item)
        else:
            for suggestion in suggestions:
                widget = SuggestionWidget(suggestion)
                widget.action_taken.connect(self._handle_suggestion_action)
                item = QListWidgetItem()
                item.setSizeHint(widget.sizeHint())
                self.recommendations_list.addItem(item)
                self.recommendations_list.setItemWidget(item, widget)

    def _on_manual_teach(self):
        text = self.teach_input.text().strip()
        cat = self.teach_cat_combo.currentText()
        diff_text = self.teach_diff_combo.currentText()
        
        if not text or not cat:
            return
            
        try:
            difficulty = int(diff_text.split()[0])
        except:
            difficulty = 1
        
        if self.ai_engine:
            self.ai_engine.learn_task(text, cat, difficulty=difficulty)
            self.teach_input.clear()
            self.refresh()
            self.message_requested.emit(f"Neural Brain updated with example: '{text}'")

    def _run_training(self):
        if not self.ai_engine:
            return
        self.btn_train.setText("Training... (Please wait)")
        self.btn_train.setEnabled(False)
        self.train_progress.setValue(0)
        self.train_progress.show()
        
        # Use a worker thread to prevent UI freezing
        # The AIEngine will handle the actual worker creation and management
        self.ai_engine.train_model(background=True, on_finish_callback=self._on_training_finished)

    def _on_training_finished(self):
        self.refresh()
        self.btn_train.setText("Train Brain Now")
        self.btn_train.setEnabled(True)
        self.train_progress.hide()
        self.message_requested.emit("Training Complete! The AI has learned.")

    def _handle_review_action(self, action: str, data: dict):
        if not self.ai_engine:
            return
        
        if action == 'confirm':
            self.ai_engine.confirm_prediction(data['text'], data['predicted_category'], data.get('context'))
            self.refresh()
        elif action == 'correct':
            categories = self.ai_engine.get_all_categories()
            if not categories:
                QMessageBox.warning(self, "Correction", "No categories available to choose from.")
                return

            current_index = categories.index(data['predicted_category']) if data['predicted_category'] in categories else 0
            
            new_cat, ok = QInputDialog.getItem(self, "Correct Prediction", 
                                               f"What is the correct category for:\n'{data['text']}'?",
                                               categories, current_index, False)
            
            if ok and new_cat:
                self.ai_engine.correct_prediction(data['text'], new_cat, data.get('context'))
                self.refresh()

    def _reset_brain(self):
        if not self.ai_engine:
            return
        
        reply = QMessageBox.question(
            self, 
            "Reset AI Brain",
            "Are you sure you want to reset the AI? This will delete its memory and all learned data. The app will use the default brain.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.ai_engine.reset_brain()
            self.refresh()
            self.message_requested.emit("AI Brain has been reset.")

    def _handle_suggestion_action(self, action: str, suggestion: dict):
        s_type = suggestion['type']
        hub = self.window()
        if not hub:
            return
            
        if action == "accept":
            if s_type == 'SUGGEST_RECURRENCE':
                from core.model import add_task
                add_task(
                    hub.state,
                    text=suggestion['task_text'],
                    section="Today",
                    recurrence={'type': suggestion['interval']}
                )
                hub.schedule_save()
                self.message_requested.emit(f"Recurring task '{suggestion['task_text']}' created!")
            elif s_type == 'WELLBEING_CHECK':
                hub.open_page("journal")
                self.message_requested.emit("Taking time for yourself is a great idea.")
            elif s_type == 'REVIEW_STALE_TASKS':
                hub.open_page("someday")
                self.message_requested.emit("Let's clear out some old ideas.")
            elif s_type == 'SUGGEST_BREAKDOWN_STUCK_TASK':
                task_id = suggestion.get('task_id')
                if task_id and hasattr(hub, 'break_down_task_by_id'):
                    hub.break_down_task_by_id(task_id)
                    self.message_requested.emit("Let's break that down into smaller pieces.")
            elif s_type == 'SUGGEST_RESCHEDULE':
                if hasattr(hub, 'reschedule_overloaded_tasks'):
                    moved_count = hub.reschedule_overloaded_tasks()
                    if moved_count > 0:
                        self.message_requested.emit(f"Moved {moved_count} tasks to give you some breathing room.")
            elif s_type == 'FORCED_BREAK':
                if hasattr(hub, '_start_manual_timer'):
                    # Start a 15-minute break session
                    hub._start_manual_timer(15, "break")
                    # Navigate to Zen page to show the timer
                    if hasattr(hub, 'page_zen'):
                        hub._switch_page(hub.page_zen)
                    self.message_requested.emit("Break started. Enjoy your rest!")
        
        # Dismiss the suggestion in both cases
        self.ai_engine.dismiss_suggestion(suggestion['id'])
        hub.schedule_save()
        self.refresh()

# ═══════════════════════════════════════════════════════════════════════════
# TODO / IDEAS LIST
# ═══════════════════════════════════════════════════════════════════════════
# [ ] Add 'Explain' button for AI categories (LIME/SHAP style text highlights).
# [ ] Visualize the Neural Network weights as a heat-map background.
# [ ] Add 'Personality' selector for the AI Coach (Encouraging, Stoic, Direct).
# [ ] Implement 'Batch Review' for long queues.
# [ ] Allow user to 'Ignore' certain words from being learned.
# [x] AI Brain Visualization: A 3D or 2D nodes-and-lines graph representing the Neural Network's current state.
# [ ] Progress Timeline: Visualize how the AI's accuracy has improved over weeks of training.
