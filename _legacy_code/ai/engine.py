import json
import re
import torch  # type: ignore
import shutil
import random
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal  # type: ignore

# Conditional import for LLM libraries
try:
    from transformers import pipeline  # type: ignore
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("Warning: 'transformers' library not found. LLM features will be disabled.")
from core.model import today_str, current_time_of_day, get_today_mood, tasks_in_section
from core.user_manager import UserManager
from .architect import TaskBrain
from .pipeline import TaskPipeline
from .trainer import UserTrainer, TrainingWorker
import ai.analytics as analytics

class TaskInsights:
    """
    A collection of heuristic-based methods for analyzing and generating task-related data.
    This is separated from the main AIEngine to group non-ML AI features.
    """
    def calculate_xp_for_task(self, task: Dict[str, Any]) -> int:
        """Calculates XP based on difficulty and importance."""
        base = task.get("xpReward", 10)
        difficulty = task.get("difficulty", 1)
        
        # Multiplier for difficulty
        multiplier = 1.0 + (0.5 * (difficulty - 1))
        
        return int(base * multiplier)

class AIEngine(QObject):
    """
    Orchestrates all AI operations, including prediction, learning, and training.
    """
    status_changed = pyqtSignal(str) # Emits what the AI is "thinking"

    def __init__(self, user_id: str, state: Dict):
        super().__init__()
        self.user_id = user_id
        self.state = state
        self.user_manager = UserManager()
        self.insights = TaskInsights()
        self.user_path = self.user_manager.ensure_user_directory(user_id)
        self._tips = [
            "Use #hashtags in task input to auto-categorize them (e.g., 'Call mom #Personal').",
            "Double-click any task to quickly rename it.",
            "Right-click a task for more options like scheduling or moving it.",
            "Use the Brain Dump feature on the Home page to quickly unload your mind.",
            "Check the AI Coach page to teach the AI and see its recommendations.",
            "You can drag and drop tasks to reorder them.",
            "Press Ctrl+B to toggle Focus Mode and hide the sidebar.",
            "The 'Zen Mode' helps you focus on just one task at a time.",
            "Review your 'Someday' list occasionally to keep it fresh."
        ]
        
        self._bootstrap_base_model()
        
        self.pipeline = TaskPipeline(self.user_path)
        self.model: Optional[TaskBrain] = None
        self.review_queue: List[Dict] = []
        self.dynamic_threshold = 0.85  # Cache for the confidence threshold

        self._new_samples_counter = 0
        self._training_threshold = 10  # Auto-train after 10 new learned tasks
        self._training_worker: Optional[TrainingWorker] = None

        self.llm_pipeline = None
        self._load_llm_if_enabled()

        self.load_pipeline_and_model()
        self.status_changed.emit("Ready")

    def _load_llm_if_enabled(self):
        """Loads the Phi-2 model if enabled in settings."""
        if self.state.get("settings", {}).get("llmEnabled", False) and LLM_AVAILABLE:
            self.status_changed.emit("Waking up Phi-2...")
            print("Loading local LLM (Phi-2) for task reasoning...")
            try:
                # Using Phi-2 for complex task reasoning
                self.llm_pipeline = pipeline(
                    "text-generation", 
                    model="microsoft/phi-2", 
                    device="cpu", 
                    trust_remote_code=True
                )
                print("Local LLM loaded successfully.")
                self.status_changed.emit("Phi-2 Ready")
            except Exception as e:
                print(f"Failed to load LLM: {e}")
                self.llm_pipeline = None
                self.status_changed.emit("LLM Error")

    def get_tip_of_the_day(self) -> str:
        """Returns a random tip to display on startup."""
        return random.choice(self._tips)

    def _bootstrap_base_model(self):
        """Copies pre-trained assets to user directory if fresh."""
        # Locate assets folder (assuming it's in the project root, two levels up)
        base_path = Path(__file__).parent.parent / "assets"
        base_brain = base_path / "base_brain.pth"
        base_vocab = base_path / "base_vocab.json"
        
        user_brain = self.user_path / "brain.pth"
        user_vocab = self.user_path / "vocab.json"
        
        if base_brain.exists() and not user_brain.exists():
            try:
                shutil.copy2(base_brain, user_brain)
                print(f"Bootstrapped user brain from {base_brain}")
                # Force copy vocab if brain was copied, to ensure sync
                if base_vocab.exists():
                    shutil.copy2(base_vocab, user_vocab)
                    print(f"Bootstrapped user vocab from {base_vocab} (synced with brain)")
            except Exception as e:
                print(f"Failed to bootstrap brain: {e}")
                
        elif base_vocab.exists() and not user_vocab.exists():
            try:
                shutil.copy2(base_vocab, user_vocab)
                print(f"Bootstrapped user vocab from {base_vocab}")
            except Exception as e:
                print(f"Failed to bootstrap vocab: {e}")

    def load_pipeline_and_model(self):
        """Loads the pipeline and model from disk."""
        self.pipeline.load()
        
        if not self.pipeline.categories:
            # If no categories exist, use the default ones from the main state
            self.pipeline.categories = self.state.get("categories", [])
            self.pipeline.cat_to_idx = {cat: i for i, cat in enumerate(self.pipeline.categories)}

        model_path = self.user_path / "brain.pth"
        if not model_path.exists() and not self.pipeline.vocab:
            # True first run: no model, no vocab. Build a fresh vocab from user's history.
            self.pipeline.build_or_update_from_log(self.state.get("tasks", []))

        # The dimensions for each context feature (e.g., 4 times of day, 7 days of week)
        context_dims = [len(values) for values in self.pipeline.context_features.values()]

        self.model = TaskBrain(
            vocab_size=len(self.pipeline.vocab),
            hidden_size=128,
            num_classes=len(self.pipeline.categories),
            context_dims=context_dims,
            context_embedding_dim=12
        )
        
        if model_path.exists():
            try:
                # Check for corruption (empty file)
                if model_path.stat().st_size == 0:
                    raise ValueError("Model file is empty")
                
                # Load with strict=False to handle architectural changes gracefully.
                incompatible_keys = self.model.load_state_dict(torch.load(model_path), strict=False)
                
                if not incompatible_keys.missing_keys and not incompatible_keys.unexpected_keys:
                    print("AI brain loaded successfully.")
                else:
                    print("AI brain loaded with mismatched layers. This is normal after an update.")

            except Exception as e:
                # This block now only runs for true file corruption or other critical errors,
                # not for simple key mismatches.
                print(f"Could not load AI brain (file corrupt or other error). Re-initializing. Error: {e}")
                # Rename corrupt file for safety/debugging
                try:
                    model_path.rename(model_path.with_suffix(".corrupt"))
                except OSError:
                    pass
                
                # Attempt to restore base model immediately
                self._bootstrap_base_model()
                
                # Reload pipeline and re-init model to match new vocab
                self.pipeline.load()
                self.model = TaskBrain(
                    vocab_size=len(self.pipeline.vocab),
                    hidden_size=128,
                    num_classes=len(self.pipeline.categories),
                    context_dims=context_dims,
                    context_embedding_dim=12
                )

                # Try loading again if bootstrap succeeded
                if model_path.exists():
                    try:
                        # Use strict=False here as well, as the base model might be old
                        incompatible_keys = self.model.load_state_dict(torch.load(model_path), strict=False)
                        if not incompatible_keys.missing_keys and not incompatible_keys.unexpected_keys:
                            print("Successfully loaded bootstrapped model.")
                        else:
                            print("Bootstrapped model is from an older architecture. Some layers re-initialized.")
                    except Exception as e2:
                        print(f"Failed to load bootstrapped model: {e2}")
                        # If bootstrapped model is also bad, delete it to prevent loop
                        try:
                            model_path.unlink()
                        except: pass
                        print("Starting with random weights. Please run 'train_brain_model.py' to update the base model.")
        self.model.eval()
        self._update_dynamic_threshold()

    def _update_dynamic_threshold(self):
        """
        Adjusts the confidence threshold based on user agreement rate.
        Higher agreement -> lower threshold (more trust).
        """
        stats = self.state.get("stats", {})
        total = stats.get("ai_total_reviewed", 0)
        confirmed = stats.get("ai_total_confirmed", 0)
        
        if total < 10:
            self.dynamic_threshold = 0.85
            return

        rate = confirmed / total
        self.dynamic_threshold = max(0.65, min(0.90, 1.0 - (rate * 0.35)))

    def neural_inference(self, text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Core neural reasoning method. Returns predicted category, complexity, and duration."""
        # Automatically enrich context with user state if not provided
        if context is None:
            mood_data = get_today_mood(self.state)
            context = {
                "time_of_day": current_time_of_day(),
                "day_of_week": datetime.now().strftime("%A"),
                "mood": mood_data.get("value", "Okay") if mood_data else "Okay"
            }

        self.status_changed.emit(f"Reasoning: {text[:20]}...")
        if not self.model or not text or len(text.strip()) < 2:
            self.status_changed.emit("Ready")
            return {"category": None, "complexity": 1, "duration": 15}

        if len(self.pipeline.vocab) <= 1:
            self.status_changed.emit("Ready")
            return {"category": None, "complexity": 1, "duration": 15}

        text_indices, offsets, context_indices = self.pipeline.process_input(text, context or {})
        with torch.no_grad():
            cat_logits, comp_logits, dur_pred = self.model(text_indices, offsets, context_indices)
            
            # Category
            cat_probs = torch.softmax(cat_logits, dim=1)
            cat_conf, cat_idx = torch.max(cat_probs, 1)
            
            # Complexity
            comp_idx = torch.argmax(comp_logits, dim=1).item() + 1
            
            # Duration (clamped to realistic bounds)
            duration = max(5, min(480, int(dur_pred.item())))
            
            category = self.pipeline.get_category_name(cat_idx.item())
            
            # Handle low-confidence categories for review
            if cat_conf.item() < self.dynamic_threshold:
                if not any(q['text'] == text for q in self.review_queue) and len(self.review_queue) < 25:
                    self.review_queue.append({
                        "text": text, "predicted_category": category, 
                        "confidence": cat_conf.item(), "context": context or {}
                    })
                category = None

            self.status_changed.emit("Ready")
            return {
                "category": category,
                "complexity": comp_idx,
                "duration": duration,
                "confidence": cat_conf.item()
            }

    def predict_category(self, text: str, context: Optional[Dict] = None) -> Optional[str]:
        return self.neural_inference(text, context)["category"]

    def confirm_prediction(self, text: str, category: str, context: Optional[Dict]):

        """Learns a task from a confirmed prediction and updates stats."""
        stats = self.state.setdefault("stats", {})
        stats["ai_total_reviewed"] = stats.get("ai_total_reviewed", 0) + 1
        stats["ai_total_confirmed"] = stats.get("ai_total_confirmed", 0) + 1
        self.learn_task(text, category, context)

    def correct_prediction(self, text: str, new_category: str, context: Optional[Dict]):
        """Learns a task from a corrected prediction and updates stats."""
        stats = self.state.setdefault("stats", {})
        stats["ai_total_reviewed"] = stats.get("ai_total_reviewed", 0) + 1
        self.learn_task(text, new_category, context)

    def reset_brain(self):
        """Deletes all user-specific AI data and re-bootstraps."""
        files_to_delete = [
            self.user_path / "brain.pth",
            self.user_path / "vocab.json",
            self.user_path / "categories.json",
            self.user_path / "usage_log.json"
        ]
        for f in files_to_delete:
            if f.exists():
                try:
                    f.unlink()
                except OSError as e:
                    print(f"Error deleting {f}: {e}")
        
        # Reset stats in the main state
        if "stats" in self.state:
            self.state["stats"]["ai_total_reviewed"] = 0
            self.state["stats"]["ai_total_confirmed"] = 0
        
        self.review_queue.clear()
        self._new_samples_counter = 0
        self.load_pipeline_and_model()
        print("AI Brain has been reset to its default state.")

    def learn_task(self, text: str, category: str, context: Optional[Dict] = None, difficulty: int = 1, duration: int = 30, task_id: Optional[str] = None):
        """
        Adds or updates a verified task in the training log.
        Now supports tracking by task_id to allow 'Outcome Learning'.
        """
        self.status_changed.emit("Observing behavior...")
        
        # Enrich context with current mood if missing
        if context is None or "mood" not in context:
            mood_data = get_today_mood(self.state)
            context = context or {}
            context["mood"] = mood_data.get("value", "Okay") if mood_data else "Okay"

        log_path = self.user_path / "usage_log.json"
        log_data = []
        if log_path.exists():
            with open(log_path, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
        
        # Outcome Learning: If this task_id already exists in the log, update it with actual results
        if task_id:
            for entry in reversed(log_data):
                if entry.get("task_id") == task_id:
                    # Calculate 'Surprise' - how much did we miss the mark?
                    est_dur = entry.get("duration", 30)
                    error_factor = abs(duration - est_dur) / max(1, est_dur)
                    
                    entry["learning_priority"] = 2.0 if error_factor > 0.5 else 1.0
                    entry["actual_difficulty"] = difficulty
                    entry["actual_duration"] = duration
                    entry["completed"] = True
                    
                    if error_factor > 0.8:
                        self.status_changed.emit("Noting significant outlier...")
                        # Flag for review: Let the user decide if the category was also a mismatch
                        if not any(q['text'] == text for q in self.review_queue):
                            self.review_queue.append({
                                "text": text, "predicted_category": category, 
                                "confidence": 1.0, "context": context,
                                "reason": "high_duration_error"
                            })

                    with open(log_path, 'w', encoding='utf-8') as f:
                        json.dump(log_data, f, indent=2)
                    return

        log_data.append({
            "task_id": task_id,
            "text": text, "category": category, "context": context or {},
            "difficulty": difficulty, "duration": duration,
            "learning_priority": 1.0
        })
        
        # Log Rotation: Keep the model focused on recent user behavior.
        MAX_LOG_ENTRIES = 500
        if len(log_data) > MAX_LOG_ENTRIES:
            # Keep the most recent N entries
            log_data = log_data[-MAX_LOG_ENTRIES:]
            print(f"AI log trimmed to the latest {MAX_LOG_ENTRIES} entries for relevance.")

        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2)
            
        # Remove from review queue if it was there
        self.review_queue = [item for item in self.review_queue if item['text'] != text]

        # Trigger auto-training if threshold is met
        if self._new_samples_counter >= self._training_threshold:
            self._new_samples_counter = 0
            print("Auto-training threshold reached. Starting background training.")
            self.train_model(background=True)
        else:
            self._new_samples_counter += 1
        self.status_changed.emit("Ready")

    def train_model(self, background: bool = True, on_finish_callback=None):
        """Initiates the model training process."""
        if self._training_worker and self._training_worker.isRunning():
            print("Training is already in progress.")
            return

        trainer = UserTrainer(self.user_id, self.user_manager)
        
        self.status_changed.emit("Training neural layers...")
        if background:
            self._training_worker = TrainingWorker(trainer)
            if on_finish_callback:
                self._training_worker.finished.connect(on_finish_callback)
            self._training_worker.finished.connect(self._on_training_complete)
            self._training_worker.start()
        else:
            success = trainer.train_model()
            if success:
                self._on_training_complete(True)

    def _on_training_complete(self, success: bool):
        """Called after training finishes to load the new model."""
        if success:
            print("AIEngine: Training complete. Reloading model.")
            self.load_pipeline_and_model()
        self.status_changed.emit("Ready")

    def get_stats(self) -> Dict:
        """Returns statistics about the AI's state."""
        status = "Ready"
        if self._training_worker and self._training_worker.isRunning():
            status = "Training"
        elif not (self.user_path / "brain.pth").exists():
            status = "Untrained"
            
        log_path = self.user_path / "usage_log.json"
        log_count = 0
        if log_path.exists():
            with open(log_path, 'r') as f:
                log_count = len(json.load(f))

        agreement_rate = 0
        total_reviewed = self.state.get("stats", {}).get("ai_total_reviewed", 0)
        total_confirmed = self.state.get("stats", {}).get("ai_total_confirmed", 0)
        if total_reviewed > 0:
            agreement_rate = (total_confirmed / total_reviewed) * 100

        return {
            "status": status,
            "vocab_size": len(self.pipeline.vocab),
            "task_log_count": log_count,
            "agreement_rate": agreement_rate,
        }

    def get_review_queue(self) -> List[Dict]:
        """Returns the list of low-confidence predictions for user review."""
        return self.review_queue

    def get_all_categories(self) -> List[str]:
        """Returns all categories known to the AI."""
        # Ensure pipeline is loaded and has categories
        if not self.pipeline.categories:
            self.pipeline.load()
        # Fallback to app state if still empty
        return self.pipeline.categories or self.state.get("categories", [])

    def get_proactive_suggestions(self, state: Optional[Dict] = None) -> List[Dict]:
        """Generates and returns actionable suggestions based on user history."""
        target_state = state if state is not None else self.state
        return analytics.generate_suggestions(target_state)

    def dismiss_suggestion(self, suggestion_id: str):
        """Adds a suggestion ID to the dismissed list to hide it."""
        dismissed = self.state.setdefault("dismissed_suggestions", [])
        if suggestion_id not in dismissed:
            dismissed.append(suggestion_id)
        # The caller is expected to schedule a save.

    def get_daily_forecast(self, state: Dict) -> str:
        """Generates a short, encouraging forecast based on current state."""
        mood_data = get_today_mood(state)
        mood = mood_data.get("value", "Okay") if mood_data else "Okay"
        tasks = tasks_in_section(state, "Today")
        incomplete = [t for t in tasks if not t.get("completed")]
        
        if not incomplete:
            return "A clear slate! Perfect for reflecting or picking a 'Someday' project."
            
        if mood in ["Low energy", "Stressed"]:
            return "Energy is low today. I recommend focusing on 1-2 small 'Quick Wins' to build momentum."
            
        # Cognitive Load Balancing: Warn about too many hard tasks
        hard_tasks = [t for t in incomplete if t.get("difficulty", 1) >= 4]
        if len(hard_tasks) >= 3:
            return f"Caution: You have {len(hard_tasks)} complex tasks planned. Consider spreading these out to avoid burnout."

        hard_tasks = [t for t in incomplete if t.get("difficulty", 1) >= 4]
        if hard_tasks and current_time_of_day() == "morning":
            return f"Your focus is likely high. It's a great time to tackle: '{hard_tasks[0]['text']}'."
            
        return f"Steady progress! You have {len(incomplete)} tasks to navigate today."

    def rank_tasks(self, tasks: List[Dict], context: Dict) -> List[Dict]:
        """
        Ranks tasks based on AI-driven heuristics and context.
        Returns a sorted list of tasks.
        """
        mood = context.get("mood", "Okay")
        time_of_day = context.get("time_of_day", current_time_of_day())
        prefer_easy = mood in ["Low energy", "Stressed"]

        def score_task(t):
            score = 0
            # --- Factors that INCREASE score (higher priority) ---

            # 1. Importance is paramount
            if t.get("important"):
                score += 100

            # 2. Scheduled items with a due date today
            schedule = t.get("schedule")
            if schedule and schedule.get("date") == today_str():
                score += 50
                # Bonus if it has a time
                if schedule.get("time"):
                    score += 10

            # 3. Difficulty (context-dependent)
            difficulty = t.get("difficulty", 1)
            if prefer_easy:
                # If low energy, give a large boost to easier tasks to get momentum
                score += (5 - difficulty) * 10
            else:
                # If motivated, give a slight bonus to harder tasks
                score += difficulty * 2

            # 4. Duration (Quick Wins)
            duration = t.get("estimatedDuration", 0)
            if duration > 0 and duration <= 15:
                score += 15  # Big bonus for very short tasks
            elif duration > 0 and duration <= 30:
                score += 5  # Small bonus for short tasks

            # 5. Age of task (older tasks get a small nudge)
            try:
                created_dt = datetime.fromisoformat(t.get("createdAt", ""))
                days_old = (datetime.now() - created_dt).days

                if t.get("important"):
                    # Neglected important task -> Boost urgency significantly
                    score += days_old * 2
                else:
                    # Stale tasks get a small nudge
                    score += days_old // 2
                    # Fresh tasks get a small momentum bonus
                    if days_old < 3:
                        score += 5
            except:
                pass

            # 6. Category-Time Alignment
            category = t.get("category")
            # High-Focus periods: Morning is for complex "Work/Dev", Afternoon for "Learning"
            if time_of_day == "morning" and category in ["Work", "Dev"] and t.get("difficulty", 1) >= 3:
                score += 15
            elif time_of_day == "afternoon" and category in ["Learning"]:
                score += 5
            if time_of_day == "evening" and category in ["Personal", "Health", "Creative"]:
                score += 5

            return score

        # Sort descending by score (higher score = higher priority)
        return sorted(tasks, key=score_task, reverse=True)

    def analyze_task_complexity(self, text: str) -> int:
        """Uses local neural brain to estimate complexity."""
        return self.neural_inference(text)["complexity"]

    def estimate_duration(self, text: str) -> int:
        """Uses local neural brain to estimate duration."""
        return self.neural_inference(text)["duration"]

    def generate_subtasks(self, text: str) -> List[str]:
        """
        Generates subtasks, using LLM if enabled, otherwise falling back to heuristics.
        """
        # Personality Prefix
        style = self.state.get("userProfile", {}).get("style", "Encouraging")
        style_prompt = ""
        if style == "Stoic": style_prompt = "Keep instructions brief and objective. "
        elif style == "Direct": style_prompt = "Focus on efficiency and specific metrics. "
        elif style == "Hype": style_prompt = "Be extremely energetic and motivating. "
        elif style == "Encouraging": style_prompt = "Be supportive and kind. "

        if self.llm_pipeline:
            self.status_changed.emit("Phi-2 is reasoning...")
            print(f"Using LLM for subtask generation for: '{text}'")
            # Improved reasoning prompt for Phi-2
            prompt = (
                f"Instruct: You are a productivity expert. {style_prompt}Analyze the task '{text}'. "
                "First, identify the logical phases. Then, output 3 to 5 actionable, "
                "one-line subtasks that a user can complete in under 30 minutes each.\nOutput:"
            )
            
            try:
                outputs = self.llm_pipeline(
                    prompt, 
                    max_new_tokens=150, 
                    do_sample=True, 
                    temperature=0.7, 
                    pad_token_id=self.llm_pipeline.tokenizer.eos_token_id,
                    return_full_text=False
                )
                response = outputs[0]['generated_text'].strip()
                
                # Parse the response into clean lines
                lines = [l.strip() for l in response.split('\n') if l.strip()]
                subtasks = []
                for line in lines:
                    # Remove list markers like "1. ", "- ", etc.
                    clean = re.sub(r'^(\d+[\.\)]|\*|-)\s*', '', line).strip()
                    if clean and len(clean) > 3:
                        subtasks.append(clean)
                
                self.status_changed.emit("Ready")
                return subtasks[:6] if subtasks else ["Step 1: Preparation", "Step 2: Execution", "Step 3: Review"]
            except Exception as e:
                print(f"LLM Breakdown failed: {e}")
                return ["Step 1: Preparation", "Step 2: Execution", "Step 3: Review"]

        else:
            return ["Step 1: Preparation", "Step 2: Execution", "Step 3: Review"]

    def analyze_journal_sentiment(self, text: str) -> str:
        """Uses Local LLM for neural sentiment and reflection."""
        if self.llm_pipeline:
            prompt = f"Instruct: Act as a supportive coach. Read this journal entry and provide one sentence of neural insight or encouragement: '{text}'\nOutput:"
            try:
                out = self.llm_pipeline(prompt, max_new_tokens=60, return_full_text=False)
                return out[0]['generated_text'].strip()
            except:
                pass
        return "Writing is a powerful tool for clarity. What is the one thing you want to focus on after this?"

    def generate_project_tasks(self, project_name: str) -> List[str]:
        """Neural project reasoning via Local LLM."""
        if self.llm_pipeline:
            prompt = f"Instruct: Create a list of 5 actionable tasks for a project named '{project_name}'.\nOutput:"
            try:
                out = self.llm_pipeline(prompt, max_new_tokens=150, return_full_text=False)
                lines = out[0]['generated_text'].strip().split('\n')
                return [re.sub(r'^\d+[\.\)]\s*', '', l).strip() for l in lines if l.strip()][:5]
            except:
                pass
        return ["Brainstorm ideas", "Create project plan", "Execute first step", "Review progress"]

# ═══════════════════════════════════════════════════════════════════════════
# TODO / IDEAS LIST
# ═══════════════════════════════════════════════════════════════════════════
# [ ] Neural Duration Estimation: Replace heuristics in `estimate_duration` with a model trained on `actualDuration`.
# [ ] Integrate a small local LLM (like Phi-2) for complex task breakdown.
# [ ] Implement 'Time-of-Day' prediction for tasks (When do I usually do X?).
# [ ] Federated Learning: Enable (opt-in) privacy-preserving habit sharing to improve the base model.
# [ ] Biometric Integration: Sync with wearable data (Apple Health/Google Fit) to suggest "Deep Work" when HRV is high.
# [ ] Adaptive Difficulty: Automatically increase/decrease task difficulty ratings based on actual completion time vs estimate.
# [ ] Semantic Task Search: Find tasks based on meaning (e.g., searching for "car stuff" finds "oil change").
# [ ] Context-Aware Soundscapes: Automatically play specific sounds (e.g., 'Cafe') for 'Work' tasks and 'Rain' for 'Creative' tasks.
# [ ] Drift Detection: Identify tasks that are frequently rescheduled and prompt for a priority re-evaluation.
# [ ] Workflow Templates: Suggest "Design -> Build -> Test" flows when certain keywords are detected.
# [ ] Cognitive Load Balancing: Warn the user if they've scheduled too many "Hard" tasks in a single morning.
# [ ] Peer Benchmarking: (Opt-in) Compare anonymous productivity trends with other users in the same 'Role'.
# [ ] Outcome Prediction: AI predicts the likelihood of a task being completed today based on current mood and history.