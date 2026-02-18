from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QInputDialog, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QCursor

# Theme constants (matching hub.py)
TEXT_WHITE = "#ffffff"
TEXT_GRAY = "#a0a0a0"
GOLD = "#ffd700"
HOVER_BG = "rgba(255, 255, 255, 0.1)"
GLASS_BORDER = "rgba(255, 255, 255, 0.15)"

class TrainingWorker(QThread):
    """Runs AI training in a separate thread to avoid freezing the UI."""
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, trainer):
        super().__init__()
        self.trainer = trainer

    def run(self):
        # In a real scenario, the engine itself would emit progress signals.
        # For now, we just run the blocking training call.
        self.trainer.train_model()
        self.finished.emit()


class SuggestionWidget(QFrame):
    """A custom widget to display an AI suggestion with action buttons."""
    action_taken = pyqtSignal(str, dict) # "accept" or "dismiss", suggestion data

    def __init__(self, suggestion: dict, parent=None):
        super().__init__(parent)
        self.suggestion = suggestion
        self.setObjectName("SuggestionCard")
        self.setStyleSheet(f"#SuggestionCard {{ background-color: {HOVER_BG}; border-radius: 8px; padding: 12px; }}")

        layout = QVBoxLayout(self)
        
        # Build text based on type
        if suggestion['type'] == 'SUGGEST_RECURRENCE':
            text = f"I noticed you often complete tasks like <b>'{suggestion['task_text']}'</b>. Would you like to make this a recurring <b>{suggestion['interval']}</b> task?"
        else:
            text = "I have a suggestion for you."
            
        lbl_text = QLabel(text)
        lbl_text.setWordWrap(True)
        lbl_text.setStyleSheet(f"color: {TEXT_WHITE}; background: transparent;")
        layout.addWidget(lbl_text)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_accept = QPushButton("✅ Create")
        btn_accept.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_accept.clicked.connect(lambda: self.action_taken.emit("accept", self.suggestion))
        
        btn_dismiss = QPushButton("❌ Dismiss")
        btn_dismiss.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dismiss.clicked.connect(lambda: self.action_taken.emit("dismiss", self.suggestion))
        
        btn_layout.addWidget(btn_accept)
        btn_layout.addWidget(btn_dismiss)
        layout.addLayout(btn_layout)


class CoachWidget(QWidget):
    """
    The AI Coach interface.
    Allows the user to:
    1. See the status of their Neural Network.
    2. Manually trigger training.
    3. Review and answer 'questions' (low-confidence predictions) to teach the AI.
    """
    def __init__(self, ai_engine, parent=None):
        super().__init__(parent)
        self.ai_engine = ai_engine
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        header = QLabel("AI Coach 🤖")
        header.setStyleSheet(f"color: {GOLD}; font-size: 24px; font-weight: bold;")
        layout.addWidget(header)

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

        layout.addWidget(stats_card)

        # --- Review Queue ---
        layout.addWidget(QLabel("Review Queue (Teach me!)"))
        
        self.review_list = QListWidget()
        self.review_list.setStyleSheet(f"background-color: rgba(0,0,0,0.2); border: 1px solid {GLASS_BORDER}; border-radius: 12px; color: {TEXT_WHITE};")
        layout.addWidget(self.review_list, 1)

        # Action buttons for review
        btn_row = QHBoxLayout()
        self.btn_confirm = QPushButton("✅ Confirm Prediction")
        self.btn_confirm.clicked.connect(self._confirm_prediction)
        self.btn_correct = QPushButton("✏️ Correct Category")
        self.btn_correct.clicked.connect(self._correct_prediction)
        
        for btn in (self.btn_confirm, self.btn_correct):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"background-color: {HOVER_BG}; color: {TEXT_WHITE}; border: 1px solid {GLASS_BORDER}; border-radius: 6px; padding: 10px;")
            btn_row.addWidget(btn)
            
        layout.addLayout(btn_row)
        
        # --- AI Recommendations ---
        layout.addSpacing(15)
        layout.addWidget(QLabel("AI Recommendations"))
        self.recommendations_list = QListWidget()
        layout.addWidget(self.recommendations_list, 1)

    def refresh(self):
        # Update Stats
        stats = self.ai_engine.get_stats()
        self.lbl_status.setText(f"Brain Status: {stats['status']}")
        self.lbl_vocab.setText(f"Vocabulary: {stats['vocab_size']} words")
        self.lbl_samples.setText(f"Training Samples: {stats['task_log_count']}")
        
        # Update Review Queue
        self.review_list.clear()
        queue = self.ai_engine.get_review_queue()
        
        if not queue:
            self.review_list.addItem("No pending questions. Good job!")
            self.btn_confirm.setEnabled(False)
            self.btn_correct.setEnabled(False)
        else:
            self.btn_confirm.setEnabled(True)
            self.btn_correct.setEnabled(True)
            for item in queue:
                text = f"Task: '{item['text']}'  →  AI Guessed: {item['predicted_category']} ({int(item['confidence']*100)}%)"
                list_item = QListWidgetItem(text)
                list_item.setData(Qt.ItemDataRole.UserRole, item)
                self.review_list.addItem(list_item)
                
        # Update Recommendations
        self.recommendations_list.clear()
        suggestions = self.ai_engine.get_proactive_suggestions()
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

    def _run_training(self):
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
        QMessageBox.information(self, "Training Complete", "The AI has learned from your latest data!")

    def _confirm_prediction(self):
        item = self.review_list.currentItem()
        if not item: return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data: return # Handle empty message
        
        self.ai_engine.learn_task(data['text'], data['predicted_category'], data.get('context'))
        self.refresh()

    def _correct_prediction(self):
        item = self.review_list.currentItem()
        if not item: return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data: return

        # Assumes AIEngine can provide a list of all known categories
        categories = self.ai_engine.get_all_categories()
        if not categories:
            QMessageBox.warning(self, "Correction", "No categories available to choose from.")
            return

        current_index = categories.index(data['predicted_category']) if data['predicted_category'] in categories else 0
        
        new_cat, ok = QInputDialog.getItem(self, "Correct Prediction", 
                                           f"What is the correct category for:\n'{data['text']}'?",
                                           categories, current_index, False)
        
        if ok and new_cat:
            self.ai_engine.learn_task(data['text'], new_cat, data.get('context'))
            self.refresh()

    def _handle_suggestion_action(self, action: str, suggestion: dict):
        if action == "accept":
            if suggestion['type'] == 'SUGGEST_RECURRENCE':
                # Access main window state via parent() chain
                hub = self.window()
                if hub:
                    from core.model import add_task
                    add_task(
                        hub.state,
                        text=suggestion['task_text'],
                        section="Today",
                        recurrence={'type': suggestion['interval']}
                    )
                    hub.schedule_save()
                    QMessageBox.information(self, "Success", f"Recurring task '{suggestion['task_text']}' created!")
        
        # Dismiss the suggestion in both cases
        self.ai_engine.dismiss_suggestion(suggestion['id'])
        self.window().schedule_save()
        self.refresh()