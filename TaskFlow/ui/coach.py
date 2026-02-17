from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QInputDialog
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
    finished = pyqtSignal(str)

    def __init__(self, ai_engine):
        super().__init__()
        self.ai_engine = ai_engine

    def run(self):
        # In a real scenario, the engine itself would emit progress signals.
        # For now, we just run the blocking training call.
        self.ai_engine.train_model()
        self.finished.emit("Training complete!")


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

    def _run_training(self):
        self.btn_train.setText("Training... (Please wait)")
        self.btn_train.setEnabled(False)
        self.train_progress.setValue(0)
        self.train_progress.show()
        
        # Use a worker thread to prevent UI freezing
        self.worker = TrainingWorker(self.ai_engine)
        # self.worker.progress.connect(self.train_progress.setValue) # Progress signal not implemented in engine
        self.worker.finished.connect(self._on_training_finished)
        self.worker.start()

    def _on_training_finished(self, message: str):
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
        
        self.ai_engine.learn_task(data['text'], data['predicted_category'])
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
            self.ai_engine.learn_task(data['text'], new_cat)
            self.refresh()