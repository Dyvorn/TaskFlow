import os
import re
import wave
import json
import math
import struct
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

# --- Dependency Checks ---
try:
    import pyaudio
except ImportError:
    pyaudio = None

try:
    from faster_whisper import WhisperModel # type: ignore
except ImportError:
    WhisperModel = None

try:
    import dateparser # type: ignore
    from dateparser.search import search_dates # type: ignore
except ImportError:
    dateparser = None
    search_dates = None


class VoiceListener:
    """
    Handles audio recording and offline transcription using Faster-Whisper.
    """
    def __init__(self, model_size: str = "tiny", device: str = "cpu", compute_type: str = "int8"):
        self.load_error = None
        if not WhisperModel:
            print("Warning: 'faster_whisper' not installed. Voice features will be disabled.")
            self.load_error = "faster_whisper not installed"
            self.model = None
            return
        
        print(f"Loading Whisper model '{model_size}' on {device}...")
        try:
            self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        except Exception as e:
            print(f"Failed to load Whisper model: {e}")
            self.load_error = str(e)
            self.model = None

    def record_audio(self, output_filename: str = "temp_voice.wav", duration: int = 5, 
                     chunk: int = 1024, format=None, channels: int = 1, rate: int = 16000,
                     amplitude_callback: Optional[Callable[[float], None]] = None) -> Optional[str]:
        """
        Records audio from the default microphone for a fixed duration.
        Returns the path to the saved WAV file.
        """
        if not pyaudio:
            print("Error: 'pyaudio' is not installed. Cannot record.")
            return None
            
        if format is None:
            format = pyaudio.paInt16

        p = pyaudio.PyAudio()

        print(f"Recording for {duration} seconds...")
        try:
            stream = p.open(format=format,
                            channels=channels,
                            rate=rate,
                            input=True,
                            frames_per_buffer=chunk)

            frames = []

            # Record loop
            for _ in range(0, int(rate / chunk * duration)):
                data = stream.read(chunk)
                frames.append(data)

                if amplitude_callback:
                    # Calculate RMS amplitude and call callback
                    shorts = struct.unpack(f"%dh" % (len(data) // 2), data)
                    sum_squares = sum(s**2 for s in shorts)
                    rms = math.sqrt(sum_squares / len(shorts))
                    amplitude_callback(min(1.0, rms / 32768.0))

            print("Recording finished.")

            stream.stop_stream()
            stream.close()
            p.terminate()

            # Save to file
            wf = wave.open(output_filename, 'wb')
            wf.setnchannels(channels)
            wf.setsampwidth(p.get_sample_size(format))
            wf.setframerate(rate)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            return output_filename
            
        except Exception as e:
            print(f"Recording error: {e}")
            return None

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribes the given audio file to text.
        """
        if not self.model:
            return "Error: Whisper model not loaded."
            
        if not os.path.exists(audio_path):
            return "Error: Audio file not found."

        try:
            segments, info = self.model.transcribe(audio_path, beam_size=5)
            
            # Collect all segments
            full_text = " ".join([segment.text for segment in segments])
            return full_text.strip()
        except Exception as e:
            return f"Transcription error: {e}"


class CommandParser:
    """
    NLP Engine to parse natural language into structured actions.
    Handles 'Brain Dumps' by splitting multiple commands.
    """
    def __init__(self):
        if not dateparser:
            print("Warning: 'dateparser' not installed. Date extraction will be limited.")

        # Regex patterns for intent detection
        self.patterns = {
            "project": re.compile(r"\b(?:start|create|new)\s+project\s+(?:called|named)?\s*(?P<name>.+)", re.IGNORECASE),
            "goal": re.compile(r"\b(?:set|my)\s+goal\s+(?:is|to)\s+(?P<goal>.+)", re.IGNORECASE),
            "mood": re.compile(r"\b(?:i(?:'m| am)|feeling|feel)\s+(?P<mood>happy|sad|stressed|tired|great|good|bad|anxious|excited|motivated|low energy|okay)", re.IGNORECASE),
            # Reminder pattern to clean up task text
            "reminder": re.compile(r"\b(?:remind me to|don't forget to|i need to)\s+(?P<task>.+)", re.IGNORECASE)
        }
        
        # Splitter for brain dumps (e.g., "do X AND do Y")
        self.split_pattern = re.compile(r"\s+(?:and|then|also|plus)\s+", re.IGNORECASE)

    def parse(self, text: str) -> List[Dict[str, Any]]:
        """
        Main entry point. Takes raw text, splits it, and returns a list of action dicts.
        """
        # 1. Split Brain Dump
        raw_commands = self.split_pattern.split(text)
        actions = []

        for cmd in raw_commands:
            cmd = cmd.strip()
            if not cmd:
                continue
            
            action = self._process_single_command(cmd)
            if action:
                actions.append(action)
                
        return actions

    def _process_single_command(self, text: str) -> Dict[str, Any]:
        """Identifies intent and extracts entities for a single command string."""
        
        # 1. Check for Project Intent
        match = self.patterns["project"].search(text)
        if match:
            return {
                "intent": "create_project",
                "name": match.group("name").strip().strip("."),
                "original_text": text
            }

        # 2. Check for Goal Intent
        match = self.patterns["goal"].search(text)
        if match:
            return {
                "intent": "set_goal",
                "text": match.group("goal").strip().strip("."),
                "original_text": text
            }

        # 3. Check for Mood Intent
        match = self.patterns["mood"].search(text)
        if match:
            mood_val = match.group("mood").lower().capitalize()
            return {
                "intent": "log_mood",
                "value": mood_val,
                "note": text,
                "original_text": text
            }

        # 4. Default: Task Intent
        task_text = text
        # Clean up prefix like "Remind me to"
        match = self.patterns["reminder"].search(text)
        if match:
            task_text = match.group("task").strip()
            
        # Extract metadata like the old parse_task_input
        important = False
        category = None
        tags = []

        # Priority
        if "!" in task_text or "urgent" in task_text.lower():
            important = True
            task_text = task_text.replace("!", "").replace("urgent", "", 1).strip()
            
        # Category hashtags
        match = re.search(r"#(\w+)", task_text)
        if match:
            category = match.group(1)
            task_text = task_text.replace(match.group(0), "").strip()

        # Tags (@tag)
        tags_found = re.findall(r"@(\w+)", task_text)
        if tags_found:
            tags = tags_found
            task_text = re.sub(r"@(\w+)", "", task_text).strip()

        # Extract Date/Time using dateparser
        due_date = None
        due_time = None
        
        if search_dates:
            # Find dates in the text
            found_dates = search_dates(task_text, settings={'PREFER_DATES_FROM': 'future', 'RELATIVE_BASE': datetime.now()})
            
            if found_dates:
                # Take the last found date (usually at the end of the sentence)
                date_str, date_obj = found_dates[-1]
                
                # Remove the date string from the task text to clean it up
                # (Case insensitive replace)
                pattern = re.compile(re.escape(date_str), re.IGNORECASE)
                task_text = pattern.sub("", task_text).strip()
                
                due_date = date_obj.date().isoformat()
                # Only set time if it's specific (not default 00:00)
                if date_obj.hour != 0 or date_obj.minute != 0:
                    due_time = date_obj.strftime("%H:%M")

        return {
            "intent": "create_task",
            "text": task_text.strip("."),
            "due_date": due_date,
            "due_time": due_time,
            "original_text": text,
            "important": important,
            "category": category,
            "tags": tags
        }

# --- Example Usage ---
if __name__ == "__main__":
    # 1. Setup
    # listener = VoiceListener(model_size="tiny") # Uncomment to load model
    parser = CommandParser()
    
    # 2. Simulate Recording (or use listener.record_audio())
    # audio_file = listener.record_audio(duration=5)
    # text = listener.transcribe(audio_file)
    
    # Simulated Text (Brain Dump)
    simulated_text = "Remind me to submit the report next Friday at 2pm and I'm feeling really stressed about work also start a new project called Website Redesign"
    
    print(f"Simulated Voice Input: '{simulated_text}'\n")
    
    # 3. Process
    actions = parser.parse(simulated_text)
    
    # 4. Result
    print("--- Extracted Actions ---")
    print(json.dumps(actions, indent=2))