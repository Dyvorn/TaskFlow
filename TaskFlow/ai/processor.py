# ============================================================================
# TASKFLOW - VOICE COMMAND PROCESSOR
# ============================================================================

import re
import wave
import pyaudio
from datetime import datetime

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    WhisperModel = None
    FASTER_WHISPER_AVAILABLE = False
    print("Warning: 'faster_whisper' not installed. Voice features will be disabled.")

try:
    import dateparser
    DATEPARSER_AVAILABLE = True
except ImportError:
    dateparser = None
    DATEPARSER_AVAILABLE = False
    print("Warning: 'dateparser' not installed. Date extraction will be limited.")

class VoiceListener:
    """
    Handles audio recording and transcription using faster-whisper.
    """
    def __init__(self, model_size="tiny"):
        self.model_size = model_size
        self.model = None
        self.load_error = None
        if FASTER_WHISPER_AVAILABLE:
            try:
                print(f"Loading Whisper model '{model_size}' on cpu...")
                self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
            except Exception as e:
                self.load_error = str(e)
                print(f"Error loading Whisper model: {e}")
        else:
            self.load_error = "faster_whisper library not found."

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribes the given audio file to text.
        """
        if not self.model:
            return f"Error: Transcription model not loaded ({self.load_error})."
        try:
            segments, _ = self.model.transcribe(audio_path, beam_size=5)
            transcription = " ".join([segment.text for segment in segments])
            return transcription.strip()
        except Exception as e:
            return f"Transcription error: {e}"

class CommandParser:
    """
    Parses transcribed text to identify user intents and extract entities.
    """
    def __init__(self):
        # Keywords for different intents, ordered by priority
        self.create_task_keywords = ["add task", "new task", "remind me to", "add", "create"]
        self.create_project_keywords = ["new project", "create project"]
        self.set_goal_keywords = ["my goal is", "main goal", "focus on"]
        self.log_mood_keywords = ["i feel", "i'm feeling", "mood is"]

    def parse(self, text: str) -> list:
        """
        Parses a string of text and returns a list of action dictionaries.
        """
        text = text.lower()
        actions = []

        # --- Intent Matching ---
        for keyword in self.create_task_keywords:
            if text.startswith(keyword):
                task_text = text.replace(keyword, "", 1).strip()
                if task_text:
                    actions.append({"intent": "create_task", "text": task_text})
                    return actions

        for keyword in self.create_project_keywords:
            if text.startswith(keyword):
                project_name = text.replace(keyword, "", 1).strip()
                if project_name:
                    actions.append({"intent": "create_project", "name": project_name})
                    return actions

        for keyword in self.set_goal_keywords:
            if text.startswith(keyword):
                goal_text = text.replace(keyword, "", 1).strip()
                if goal_text:
                    actions.append({"intent": "set_goal", "text": goal_text})
                    return actions

        # Default Fallback: If no other intent is found, assume it's a task.
        if text and not actions:
            actions.append({"intent": "create_task", "text": text})

        return actions