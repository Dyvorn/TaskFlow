import json
import torch
import shutil
import random
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime

from core.model import today_str, current_time_of_day
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
    def analyze_task_complexity(self, text: str) -> int:
        """
        Estimates difficulty (1-5) based on keywords, length, and cognitive load.
        1: Trivial, 2: Easy, 3: Medium, 4: Hard, 5: Epic
        """
        text = text.lower()
        words = text.split()
        score = 1
        
        # 1. Length heuristic (longer tasks often imply more detail/steps)
        if len(words) > 12:
            score += 2
        elif len(words) > 6:
            score += 1
            
        # 2. Scope Keywords
        epic_keywords = ["entire", "whole", "complete", "overhaul", "rewrite", "migration", "launch", "thesis", "dissertation", "infrastructure"]
        hard_keywords = ["project", "report", "presentation", "plan", "design", "build", "refactor", "study", "research", "analysis", "develop", "implement", "debug", "audit"]
        medium_keywords = ["write", "email", "call", "schedule", "fix", "review", "read", "organize", "clean", "prepare", "draft", "meeting", "discuss", "update"]
        
        if any(k in text for k in epic_keywords):
            score += 3
        elif any(k in text for k in hard_keywords):
            score += 2
        elif any(k in text for k in medium_keywords):
            score += 1
            
        # 3. Time heuristics (explicit mentions)
        if "days" in text or "week" in text:
            score += 3
        elif "hours" in text or "hr" in text:
            score += 1
        elif "min" in text or "quick" in text:
            score -= 1 # Explicitly short
            
        # 4. Cognitive Load (Abstract vs Concrete)
        # "Think about", "Decide", "Strategy" imply high cognitive load
        cognitive_heavy = ["decide", "strategy", "architecture", "solve", "debug", "figure out", "understand"]
        if any(k in text for k in cognitive_heavy):
            score += 1

        # Cap at 5, Min 1
        return min(5, max(1, score))

    def generate_subtasks(self, text: str) -> List[str]:
        """
        Returns a list of suggested subtasks based on the parent task text.
        Uses heuristics for now, can be upgraded to LLM later.
        """
        text = text.lower()
        
        if "report" in text or "paper" in text:
            return ["Research topic", "Create outline", "Draft introduction", "Write body paragraphs", "Review and edit"]
        elif "presentation" in text or "slides" in text or "deck" in text:
            return ["Outline key points", "Gather visuals/data", "Create slides", "Practice delivery"]
        elif "meeting" in text or "sync" in text:
            return ["Prepare agenda", "Send invites", "Prepare notes"]
        elif "code" in text or "feature" in text or "api" in text:
            return ["Define requirements", "Design architecture", "Implement core logic", "Write tests", "Refactor"]
        elif "bug" in text or "error" in text or "fix" in text:
            return ["Reproduce issue", "Check logs", "Identify root cause", "Apply fix", "Verify fix"]
        elif "workout" in text or "gym" in text:
            return ["Pack gear", "Warm up", "Main exercise", "Cool down/Stretch"]
        elif "clean" in text or "tidy" in text or "house" in text:
            return ["Clear surfaces", "Dust", "Vacuum/Sweep", "Take out trash"]
        elif "shop" in text or "groceries" in text:
            return ["Check fridge", "Make list", "Go to store"]
        elif "learn" in text or "study" in text:
            return ["Find resources/tutorial", "Set up environment", "Practice exercises", "Review notes"]
        elif "fix" in text or "debug" in text:
            return ["Reproduce issue", "Analyze logs", "Implement fix", "Test solution"]
        elif "email" in text:
            return ["Draft content", "Proofread", "Send"]
        elif "trip" in text or "travel" in text:
            return ["Book tickets", "Book accommodation", "Pack bags", "Check documents"]
        
        # Generic breakdown
        return ["Step 1: Preparation", "Step 2: Execution", "Step 3: Review"]

    def estimate_duration(self, text: str) -> int:
        """
        Returns estimated duration in minutes based on text.
        Returns 0 if no estimate could be made.
        """
        text = text.lower()
        
        # Explicit time mentions could be parsed here, but for now we use heuristics
        if any(k in text for k in ["quick", "call", "email", "check", "pay"]):
            return 15
        if any(k in text for k in ["meeting", "review", "clean", "fix", "write", "read", "gym", "workout"]):
            return 30
        if any(k in text for k in ["report", "presentation", "design", "study", "code", "debug"]):
            return 60
        if any(k in text for k in ["project", "build", "refactor"]):
            return 120
            
        # Fallback to complexity-based estimation if no keywords found
        complexity = self.analyze_task_complexity(text)
        # 1:15m, 2:30m, 3:45m, 4:90m, 5:180m
        base_map = {1: 15, 2: 30, 3: 45, 4: 90, 5: 180}
        return base_map.get(complexity, 30)

    def calculate_xp_for_task(self, task: Dict[str, Any]) -> int:
        """Calculates XP based on difficulty and importance."""
        base = task.get("xpReward", 10)
        difficulty = task.get("difficulty", 1)
        
        # Multiplier for difficulty
        multiplier = 1.0 + (0.5 * (difficulty - 1))
        
        return int(base * multiplier)

class AIEngine:
    """
    Orchestrates all AI operations, including prediction, learning, and training.
    """
    def __init__(self, user_id: str, state: Dict):
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

        self.load_pipeline_and_model()

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
            hidden_size=64,
            num_classes=len(self.pipeline.categories),
            context_dims=context_dims
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
                    hidden_size=64,
                    num_classes=len(self.pipeline.categories),
                    context_dims=context_dims
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
        Calculates and caches the confidence threshold based on model maturity.
        This should be called after loading or training the model.
        """
        base_threshold = 0.85
        min_threshold = 0.60
        vocab_size = len(self.pipeline.vocab)
        # This still reads the file, but only on model load/train, not every prediction.
        log_count = self.get_stats()["task_log_count"]

        # Lower threshold by 0.05 for every 100 vocab words and 50 log entries
        vocab_bonus = (vocab_size // 100) * 0.05
        log_bonus = (log_count // 50) * 0.05

        self.dynamic_threshold = max(min_threshold, base_threshold - vocab_bonus - log_bonus)
        print(f"Updated dynamic confidence threshold to: {self.dynamic_threshold:.2f}")

    def predict_category(self, text: str, context: Optional[Dict] = None) -> Optional[str]:
        """Predicts the category for a given task text and context."""
        if not self.model or not text:
            return None

        if context is None:
            context = {}

        text_indices, offsets, context_indices = self.pipeline.process_input(text, context)
        with torch.no_grad():
            output = self.model(text_indices, offsets, context_indices)
            probabilities = torch.softmax(output, dim=1)
            confidence, predicted_idx = torch.max(probabilities, 1)

        if confidence.item() < self.dynamic_threshold:
            # Low confidence, add to review queue
            prediction = {
                "text": text,
                "predicted_category": self.pipeline.get_category_name(predicted_idx.item()),
                "confidence": confidence.item(),
                "context": context
            }
            if len(self.review_queue) < 20: # Limit queue size
                self.review_queue.append(prediction)
            return None # Don't return a guess if unsure

        return self.pipeline.get_category_name(predicted_idx.item())

    def learn_task(self, text: str, category: str, context: Optional[Dict] = None):
        """Adds a verified task to the training log."""
        log_path = self.user_path / "usage_log.json"
        log_data = []
        if log_path.exists():
            with open(log_path, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
        
        log_data.append({"text": text, "category": category, "context": context or {}})
        
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
        self._new_samples_counter += 1
        if self._new_samples_counter >= self._training_threshold:
            print("Auto-training threshold reached. Starting background training.")
            self.train_model(background=True)
            self._new_samples_counter = 0

    def train_model(self, background: bool = True, on_finish_callback=None):
        """Initiates the model training process."""
        if self._training_worker and self._training_worker.isRunning():
            print("Training is already in progress.")
            return

        trainer = UserTrainer(self.user_id, self.user_manager)
        
        if background:
            self._training_worker = TrainingWorker(trainer)
            if on_finish_callback:
                self._training_worker.finished.connect(on_finish_callback)
            self._training_worker.finished.connect(self._on_training_complete)
            self._training_worker.start()
        else:
            trainer.train_model()
            self._on_training_complete()

    def _on_training_complete(self):
        """Called after training finishes to load the new model."""
        print("AIEngine: Training complete. Reloading model.")
        self.load_pipeline_and_model()

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

        return {
            "status": status,
            "vocab_size": len(self.pipeline.vocab),
            "task_log_count": log_count,
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
            if time_of_day in ["morning", "afternoon"] and category in ["Work", "Learning", "Dev"]:
                score += 5
            if time_of_day == "evening" and category in ["Personal", "Health", "Creative"]:
                score += 5

            return score

        # Sort descending by score (higher score = higher priority)
        return sorted(tasks, key=score_task, reverse=True)

    def analyze_task_complexity(self, text: str) -> int:
        return self.insights.analyze_task_complexity(text)

    def generate_subtasks(self, text: str) -> List[str]:
        return self.insights.generate_subtasks(text)

    def estimate_duration(self, text: str) -> int:
        return self.insights.estimate_duration(text)

    def analyze_journal_sentiment(self, text: str) -> str:
        """Simple sentiment/reflection analysis for journal entries."""
        text = text.lower()
        score = 0
        
        # Negatives
        neg_words = ["sad", "tired", "stressed", "anxious", "bad", "fail", "overwhelmed", "angry", "lonely", "hurt", "lost", "hard", "frustrated", "disappointed"]
        score -= sum(1 for w in neg_words if w in text)
        
        # Positives
        pos_words = ["happy", "great", "excited", "good", "win", "success", "proud", "calm", "peace", "love", "progress", "learned", "grateful", "thankful", "achieved"]
        score += sum(1 for w in pos_words if w in text)
        
        # Contexts
        is_busy = any(w in text for w in ["busy", "work", "deadline", "rush", "late", "pressure", "so much to do"])
        is_growth = any(w in text for w in ["learn", "study", "read", "grow", "understand", "realize", "discover"])
        is_gratitude = any(w in text for w in ["grateful", "thankful", "appreciate"])
        is_planning = any(w in text for w in ["plan", "next", "tomorrow", "goal", "focus on"])
            
        # Combined reasoning
        if is_gratitude and score > 0:
            return "It's wonderful to see you practicing gratitude. Holding onto these positive feelings can make a real difference. What's one more small thing you're thankful for?"
        elif score < -1 and is_busy:
            return "It seems like work pressure is weighing you down. When we are overwhelmed, our brain needs a hard stop. Can you pick just ONE thing to finish today and forgive yourself for the rest?"
        elif score < -1:
            return "I hear that things are tough right now. It's okay to not be okay. Sometimes the most productive thing you can do is rest. What does your body need right now?"
        elif score > 1 and is_growth:
            return "You're on fire! It sounds like you're making progress and learning. Capture this feeling—what's the main lesson you want to remember from today?"
        elif score > 0:
            return "It's great to see you in high spirits! Success builds momentum. How can you use this energy to tackle something you've been putting off?"
        elif is_growth:
            return "Learning is a journey. Even if it feels slow, you are moving forward. What's one concept that clicked for you today?"
        elif is_busy:
             return "Sounds like a busy time. Don't forget to breathe. Is there anything you can delegate or delay to tomorrow?"
        elif is_planning:
            return "Thinking ahead is a great skill. You're setting yourself up for success. What's the very first step for that plan?"
        else:
            return "Writing is a powerful tool for clarity. What is the one thing you want to focus on after this?"

    def generate_project_tasks(self, project_name: str) -> List[str]:
        """Generates a list of tasks for a new project based on its name."""
        project_name = project_name.lower()
        if "website" in project_name or "app" in project_name or "code" in project_name:
            return ["Define requirements", "Design UI/UX", "Set up repository", "Implement core features", "Write tests", "Deploy"]
        elif "vacation" in project_name or "trip" in project_name or "travel" in project_name:
            return ["Choose dates", "Book flights", "Book accommodation", "Create itinerary", "Pack luggage"]
        elif "party" in project_name or "event" in project_name or "birthday" in project_name:
            return ["Set date and time", "Create guest list", "Send invitations", "Plan menu/food", "Buy decorations"]
        elif "move" in project_name or "house" in project_name or "apartment" in project_name:
            return ["Sort belongings", "Buy packing supplies", "Pack rooms", "Hire movers", "Clean old place", "Update address"]
        elif "learn" in project_name or "course" in project_name:
            return ["Find resources", "Create study schedule", "Complete module 1", "Practice exercises", "Review notes"]
        else:
            # Generic fallback based on verbs
            if "write" in project_name:
                return ["Outline content", "Draft first version", "Review and edit", "Finalize"]
            elif "build" in project_name or "make" in project_name:
                return ["Design/Plan", "Gather materials", "Construct", "Test/Verify"]
            else:
                return ["Brainstorm ideas", "Create project plan", "Execute first step", "Review progress"]