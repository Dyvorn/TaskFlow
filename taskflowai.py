# c:\Users\Lennard Finn Penzler\Documents\VSC_Projects\todo_app\TaskFlow\taskflowai.py

import os
import json
import re
import random
import difflib
from datetime import datetime, timedelta, date
from collections import Counter
from typing import Any, Dict, List, Optional
import taskflowanalytics

# ============================================================================
# CONFIGURATION
# ============================================================================

STOP_WORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours",
    "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers",
    "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
    "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does",
    "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until",
    "while", "of", "at", "by", "for", "with", "about", "against", "between", "into",
    "through", "during", "before", "after", "above", "below", "to", "from", "up", "down",
    "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here",
    "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"
}

# ============================================================================
# PRE-TRAINED KNOWLEDGE BASE
# ============================================================================
# This acts as the "seed" for the AI, allowing it to be smart even
# when the user has no history.

DEFAULT_KNOWLEDGE_BASE = {
    "schema_version": "1.1",
    "meta": {
        "name": "TaskFlowKnowledgeBase",
        "language": "en",
        "updated_at": "2026-02-16",
        "notes": "Expanded embedded KB with fuzzy matching support."
    },
    "task_inference": {
        "priority_keywords": ["urgent", "asap", "important", "deadline", "now", "🔥", "❗", "critical", "alert", "high", "top"],
        "section_keywords": {
            "Tomorrow": ["tomorrow", "tmrw"],
            "This Week": ["next week", "this week", "weekend", "mon", "tue", "wed", "thu", "fri", "sat", "sun", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "Someday": ["later", "someday", "eventually", "maybe", "idea"]
        },
        "verb_domains": {
            "Work": ["submit", "review", "present", "email", "sync", "draft", "finalize", "approve", "schedule"],
            "Dev": ["code", "debug", "push", "deploy", "commit", "merge", "refactor", "compile", "build", "test"],
            "Personal": ["call", "text", "message", "visit", "invite", "meet", "plan"],
            "Health": ["run", "jog", "walk", "lift", "train", "drink", "eat", "sleep", "stretch"],
            "Chores": ["wash", "clean", "fix", "repair", "tidy", "organize", "buy", "purchase", "order", "pay", "cook", "bake", "make", "vacuum", "mop"],
            "Learning": ["read", "study", "practice", "learn", "watch", "listen", "research"]
        },
        "keywords": {
            # Work - General
            "email": {"category": "Work", "important": False},
            "meeting": {"category": "Work", "important": True},
            "call": {"category": "Work", "important": False},
            "slack": {"category": "Work", "important": False},
            "presentation": {"category": "Work", "important": True},
            "report": {"category": "Work", "important": True},
            "client": {"category": "Work", "important": True},
            "boss": {"category": "Work", "important": True},
            "strategy": {"category": "Work", "important": True},
            "roadmap": {"category": "Work", "important": True},
            "sync": {"category": "Work", "important": False},
            "jira": {"category": "Work", "important": False},
            "zoom": {"category": "Work", "important": False},
            "teams": {"category": "Work", "important": False},
            
            # Dev / Tech (Niche)
            "bug": {"category": "Dev", "important": True},
            "fix": {"category": "Dev", "important": True},
            "deploy": {"category": "Dev", "important": True},
            "commit": {"category": "Dev", "important": False},
            "push": {"category": "Dev", "important": False},
            "merge": {"category": "Dev", "important": True},
            "refactor": {"category": "Dev", "important": False},
            "api": {"category": "Dev", "important": True},
            "database": {"category": "Dev", "important": True},
            "server": {"category": "Dev", "important": True},
            "python": {"category": "Dev", "important": False},
            "javascript": {"category": "Dev", "important": False},
            "css": {"category": "Dev", "important": False},
            "docker": {"category": "Dev", "important": False},
            "code": {"category": "Dev", "important": True},
            "react": {"category": "Dev", "important": False},
            "vue": {"category": "Dev", "important": False},
            "node": {"category": "Dev", "important": False},
            "aws": {"category": "Dev", "important": True},
            "azure": {"category": "Dev", "important": True},
            "git": {"category": "Dev", "important": False},
            "github": {"category": "Dev", "important": False},
            "sql": {"category": "Dev", "important": True},
            "db": {"category": "Dev", "important": True},
            "frontend": {"category": "Dev", "important": False},
            "backend": {"category": "Dev", "important": False},
            "ui": {"category": "Dev", "important": False},
            "ux": {"category": "Dev", "important": False},
            "pr": {"category": "Dev", "important": True},
            
            # Creative (Niche)
            "design": {"category": "Creative", "important": False},
            "sketch": {"category": "Creative", "important": False},
            "render": {"category": "Creative", "important": True},
            "edit": {"category": "Creative", "important": False},
            "video": {"category": "Creative", "important": True},
            "photo": {"category": "Creative", "important": False},
            "write": {"category": "Creative", "important": False},
            "blog": {"category": "Creative", "important": False},
            "draw": {"category": "Creative", "important": False},
            "paint": {"category": "Creative", "important": False},
            
            # Household
            "groceries": {"category": "Personal", "important": False},
            "cook": {"category": "Personal", "important": False},
            "clean": {"category": "Personal", "important": False},
            "laundry": {"category": "Personal", "important": False},
            "plants": {"category": "Personal", "important": False},
            "dishes": {"category": "Personal", "important": False},
            "mom": {"category": "Personal", "important": True},
            "dad": {"category": "Personal", "important": True},
            "kids": {"category": "Personal", "important": True},
            "dad": {"category": "Personal", "important": True},
            "trash": {"category": "Personal", "important": False},
            "garbage": {"category": "Personal", "important": False},
            "vacuum": {"category": "Personal", "important": False},
            "dog": {"category": "Personal", "important": True},
            "cat": {"category": "Personal", "important": True},
            "vet": {"category": "Personal", "important": True},
            "gift": {"category": "Personal", "important": False},
            "shop": {"category": "Personal", "important": False},
            
            # Health
            "gym": {"category": "Health", "important": True},
            "workout": {"category": "Health", "important": True},
            "run": {"category": "Health", "important": True},
            "yoga": {"category": "Health", "important": False},
            "meditate": {"category": "Health", "important": False},
            "doctor": {"category": "Health", "important": True},
            "dentist": {"category": "Health", "important": True},
            "water": {"category": "Health", "important": False},
            "walk": {"category": "Health", "important": False},
            "diet": {"category": "Health", "important": False},
            "vitamin": {"category": "Health", "important": False},
            "sleep": {"category": "Health", "important": True},
            "meds": {"category": "Health", "important": True},
            "therapy": {"category": "Health", "important": True},
            
            # Finance
            "pay": {"category": "Finance", "important": True},
            "bill": {"category": "Finance", "important": True},
            "invoice": {"category": "Finance", "important": True},
            "tax": {"category": "Finance", "important": True},
            "budget": {"category": "Finance", "important": False},
            "invest": {"category": "Finance", "important": False},
            "bank": {"category": "Finance", "important": True},
            "transfer": {"category": "Finance", "important": True},
            "rent": {"category": "Finance", "important": True},
            "insurance": {"category": "Finance", "important": True},
            "stock": {"category": "Finance", "important": False},
            "refund": {"category": "Finance", "important": True},
            "subscription": {"category": "Finance", "important": False},
            "salary": {"category": "Finance", "important": True},
            
            # Social / Events
            "party": {"category": "Personal", "important": False},
            "birthday": {"category": "Personal", "important": True},
            "dinner": {"category": "Personal", "important": False},
            "date": {"category": "Personal", "important": True},
            
            # Learning
            "study": {"category": "Learning", "important": True},
            "read": {"category": "Learning", "important": False},
            "course": {"category": "Learning", "important": True},
            "practice": {"category": "Learning", "important": False},
            "learn": {"category": "Learning", "important": False},
            "research": {"category": "Learning", "important": False},
            "tutorial": {"category": "Learning", "important": False},
            "article": {"category": "Learning", "important": False}
        }
    },
    "advice": {
        "generic": {
            "morning": ["Eat the frog.", "Review goals.", "Hydrate first.", "Deep work block."],
            "afternoon": ["Hydrate.", "Take a walk.", "Clear inbox.", "Stretch."],
            "evening": ["Plan tomorrow.", "Disconnect.", "Read a bit.", "Reflect."],
            "burnout": ["Rest is productive.", "Take a break.", "Go outside.", "Sleep early."],
            "new_user": ["Welcome! Start small.", "Try Brain Dump.", "One task at a time."]
        },
        "styles": {
            "Gentle": {
                "morning": ["Start gently.", "Be kind to yourself.", "One step."],
                "afternoon": ["Breathe.", "You're doing enough.", "Pause."],
                "evening": ["Rest.", "Let go.", "Peace."],
                "burnout": ["Rest.", "It's okay to stop.", "Self-care first."]
            },
            "Direct": {
                "morning": ["Focus.", "Execute.", "No distractions."],
                "afternoon": ["Push through.", "Stay sharp.", "Finish it."],
                "evening": ["Done.", "Plan.", "Sleep."],
                "burnout": ["Stop.", "Recover.", "Reset."]
            },
            "Stoic": {
                "morning": ["Begin.", "Control what you can.", "Duty calls."],
                "afternoon": ["Persist.", "Endure.", "Focus."],
                "evening": ["Reflect.", "Accept.", "Rest."],
                "burnout": ["Sharpen the saw.", "Pause.", "Nature."]
            },
            "Hype": {
                "morning": ["Let's go!", "Crush it!", "Win the morning!"],
                "afternoon": ["Keep winning!", "Beast mode!", "Don't stop!"],
                "evening": ["Victory!", "What a day!", "Recharge!"],
                "burnout": ["Refuel!", "Come back stronger!", "Sleep like a king!"]
            }
        }
    }
}

# The active knowledge base starts as the default but can be overwritten by the external JSON
KNOWLEDGE_BASE = DEFAULT_KNOWLEDGE_BASE.copy()

# The active user model (Personalized Brain)
# This is loaded from user_training.json and updated dynamically
USER_MODEL = {
    "word_associations": {},    # "word": {"Work": 5, "Personal": 1}
    "category_preferences": {},  # "Work": 10
    "time_preferences": {}      # "Work": {"morning": 5, "evening": 1}
}

def init_knowledge_base(path: str) -> None:
    """
    Loads the 'Life JSON' from disk. If it doesn't exist, creates it from defaults.
    This allows you to easily update the pre-trained AI by editing the json file.
    """
    global KNOWLEDGE_BASE
    
    # If file doesn't exist, create it so the user/dev can see and edit it
    if not os.path.exists(path):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_KNOWLEDGE_BASE, f, indent=4)
        except Exception:
            pass
    
    # Load external KB to override/extend defaults
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                external_kb = json.load(f)
                # Merge top-level keys (keywords, advice)
                for key, value in external_kb.items():
                    if isinstance(value, dict) and key in KNOWLEDGE_BASE:
                        KNOWLEDGE_BASE[key].update(value)
                    else:
                        KNOWLEDGE_BASE[key] = value
        except Exception as e:
            print(f"AI Init Error: {e}")

def load_user_model(path: str) -> None:
    """
    Loads the 'User JSON' (Personal Brain) from disk.
    This enables identity portability.
    """
    global USER_MODEL
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                USER_MODEL["word_associations"] = data.get("word_associations", {})
                USER_MODEL["category_preferences"] = data.get("category_preferences", {})
                USER_MODEL["time_preferences"] = data.get("time_preferences", {})
        except Exception:
            pass

def extract_datetime_info(text: str) -> tuple[Optional[str], Optional[str], str]:
    """
    Extracts date (YYYY-MM-DD) and time (HH:MM) from text.
    Returns (date_str, time_str, cleaned_text).
    """
    text_lower = text.lower()
    today = date.today()
    target_date = None
    target_time = None

    # 1. Date Parsing
    if "tomorrow" in text_lower or "tmrw" in text_lower:
        target_date = today + timedelta(days=1)
        text = re.sub(r"\b(tomorrow|tmrw)\b", "", text, flags=re.IGNORECASE)
    elif "today" in text_lower:
        target_date = today
        text = re.sub(r"\btoday\b", "", text, flags=re.IGNORECASE)
    elif "next week" in text_lower:
        target_date = today + timedelta(days=7)
        text = re.sub(r"\bnext week\b", "", text, flags=re.IGNORECASE)
    else:
        # Check for weekdays "on Friday" or just "Friday"
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for i, day in enumerate(weekdays):
            if day in text_lower:
                days_ahead = (i - today.weekday() + 7) % 7
                if days_ahead == 0: days_ahead = 7
                target_date = today + timedelta(days=days_ahead)
                text = re.sub(rf"\b(?:on\s+)?{day}\b", "", text, flags=re.IGNORECASE)
                break

    # 2. Time Parsing (e.g., "at 5pm", "14:00", "at 5:30 pm")
    # Regex for 12h or 24h time
    time_match = re.search(r"\b(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text, re.IGNORECASE)
    if time_match:
        h_str, m_str, ampm = time_match.groups()
        try:
            h = int(h_str)
            m = int(m_str) if m_str else 0
            if ampm:
                if ampm.lower() == "pm" and h < 12: h += 12
                if ampm.lower() == "am" and h == 12: h = 0
            target_time = f"{h:02}:{m:02}"
            text = text[:time_match.start()] + text[time_match.end():] # Remove time string
        except ValueError:
            pass

    date_str = target_date.isoformat() if target_date else None
    return date_str, target_time, " ".join(text.split())

# ============================================================================
# AI LOGIC
# ============================================================================

def infer_metadata(text: str, state: Dict[str, Any], default_section: str = "Today") -> Dict[str, Any]:
    """
    Infers category and priority using a hybrid of user history and pre-trained data.
    Also handles explicit tags like #Work or !important.
    """
    # 0. Explicit Overrides (Tags)
    explicit_cat = None
    explicit_prio_tag = False
    
    # Check for #Category
    categories = state.get("categories", [])
    for cat in categories:
        # Match #Category at start, end, or surrounded by whitespace
        if re.search(rf"(?:^|\s)#{re.escape(cat)}\b", text, re.IGNORECASE):
            explicit_cat = cat
            text = re.sub(rf"(?:^|\s)#{re.escape(cat)}\b", " ", text, flags=re.IGNORECASE)
            break
            
    # Clean up conversational prefixes
    prefixes = ["remind me to", "don't forget to", "i need to", "please", "add task", "new task", "todo"]
    lower_check = text.lower()
    for p in prefixes:
        if lower_check.startswith(p):
            text = text[len(p):].strip()
            break

    # Check for !important or trailing !
    if "!important" in text.lower():
        explicit_prio_tag = True
        text = re.sub(r"!important", "", text, flags=re.IGNORECASE)
    elif text.strip().endswith("!"):
        explicit_prio_tag = True
        text = text.strip().rstrip("!")

    # Extract Date/Time (Natural Language)
    sched_date, sched_time, text = extract_datetime_info(text)
        
    # Cleanup whitespace after tag removal
    text = re.sub(r'\s+', ' ', text).strip()

    text_clean = text.strip()
    text_lower = text_clean.lower()
    words = [w for w in re.findall(r'\w+', text_lower) if w not in STOP_WORDS]
    
    # 1. User Model Learning (Personalized & Portable)
    user_cat_scores = Counter()
    user_prio_scores = 0
    
    # Check our loaded brain for these words
    associations = USER_MODEL.get("word_associations", {})
    
    for w in words:
        if w in associations:
            # associations[w] looks like {"Work": 5, "Personal": 1}
            cats = associations[w]
            for cat, score in cats.items():
                # Add the learned score for this category
                user_cat_scores[cat] += score
                # (Priority inference could be added here if we stored it in associations)

    # 2. Pre-trained Knowledge Base (General)
    kb_cat_scores = Counter()
    kb_prio_scores = 0
    
    # Access new structure (v1.1)
    inference_data = KNOWLEDGE_BASE.get("task_inference", {})
    kb_keywords = inference_data.get("keywords", {})
    
    # Helper for fuzzy matching
    def get_kb_data(word):
        if word in kb_keywords:
            return kb_keywords[word]
        # Fuzzy match (expensive, so only if exact fails)
        matches = difflib.get_close_matches(word, kb_keywords.keys(), n=1, cutoff=0.85)
        if matches:
            return kb_keywords[matches[0]]
        return None

    for w in words:
        data = get_kb_data(w)
        if data:
            # Base weight for KB matches
            kb_cat_scores[data["category"]] += 2 
            if data.get("important", False):
                kb_prio_scores += 2
    
    # 2.5 Verb Inference (Action-based guessing)
    verb_domains = inference_data.get("verb_domains", {})
    for w in words:
        for dom, verbs in verb_domains.items():
            if w in verbs:
                kb_cat_scores[dom] += 1 # Weaker signal than a noun keyword

    # 3. Priority Keywords (Explicit)
    prio_kws = inference_data.get("priority_keywords", ["urgent", "asap", "important", "deadline", "now", "🔥", "❗"])
    explicit_prio = explicit_prio_tag or any(x in text_lower for x in prio_kws)
    
    # 4. Decision Logic
    # Merge scores (User history is additive to KB)
    final_cat_scores = kb_cat_scores + user_cat_scores
    
    category = None
    if final_cat_scores:
        category = final_cat_scores.most_common(1)[0][0]
        
    if explicit_cat:
        category = explicit_cat
        
    # Priority threshold
    # If explicit keyword found OR combined score is high enough
    is_important = explicit_prio or (user_prio_scores + kb_prio_scores >= 2)
    
    # 5. Section Inference
    section = default_section
    section_kws = inference_data.get("section_keywords", {})
    found_section = False
    for sec_name, kws in section_kws.items():
        if any(kw in text_lower for kw in kws):
            section = sec_name
            found_section = True
            break
            
    if not found_section:
        # If we found a specific date, decide section based on that
        if sched_date:
            today_str = date.today().isoformat()
            if sched_date == today_str:
                section = "Today"
            elif sched_date > today_str:
                section = "Scheduled" # Put future dated tasks in Scheduled
        elif any(x in text_lower for x in ["later", "someday", "eventually"]): 
            section = "Someday"
    
    schedule = {}
    if sched_date: schedule["date"] = sched_date
    if sched_time: schedule["time"] = sched_time
    if not schedule: schedule = None

    return {"category": category, "important": is_important, "section": section, "clean_text": text_clean, "schedule": schedule}

def strip_html(text: str) -> str:
    """Removes HTML tags from a string."""
    return re.sub('<[^<]+?>', '', text)

def analyze_brain_dump(text: str, state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Intelligent parsing of raw text into structured tasks.
    Splits paragraphs, removes bullets, and guesses metadata.
    """
    results = []
    lines = text.split('\n')
    
    for line in lines:
        clean = line.strip()
        if not clean: continue
        
        # Heuristic: Split paragraphs if they look like sentences (long + punctuation)
        if len(clean) > 60 and re.search(r'[.!?]\s', clean):
             parts = re.split(r'(?<=[.!?])\s+', clean)
             for p in parts:
                 if p.strip():
                     meta = infer_metadata(p.strip(), state)
                     results.append({
                         "text": meta["clean_text"],
                         "category": meta["category"],
                         "important": meta["important"],
                         "section": meta["section"]
                     })
        else:
            # Remove common list markers
            clean = re.sub(r'^[-*•\d\.]+\s+', '', clean)
            if not clean: continue
            
            meta = infer_metadata(clean, state)
            results.append({
                "text": meta["clean_text"],
                "category": meta["category"],
                "important": meta["important"],
                "section": meta["section"]
            })
            
    return results

def generate_user_training_data(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes the user's actions to generate a portable 'User Training JSON'.
    This file contains their personal likes, vocabulary, and priorities.
    """
    tasks = state.get("tasks") or []
    
    # 1. Learn Word-Category Associations
    # Structure: "word": {"Category": score, "Category2": score}
    word_associations = {}
    
    for t in tasks:
        if not isinstance(t, dict): continue
        
        cat = t.get("category")
        if not cat: continue
        
        # Weight: Completed tasks count more, Important tasks count double
        weight = 1
        if t.get("important"): weight += 2
        
        text = t.get("text", "").lower()
        words = [w for w in re.findall(r'\w+', text) if w not in STOP_WORDS]
        for w in words:
            if w not in word_associations: word_associations[w] = Counter()
            word_associations[w][cat] += weight

    # 2. Learn Category Preferences
    cat_counts = Counter()
    for t in tasks:
        if t.get("category"):
            cat_counts[t["category"]] += 1

    # 3. Learn Time Preferences (When do you complete certain categories?)
    # "Health": {"morning": 5, "evening": 1}
    time_prefs = {}
    for t in tasks:
        if t.get("completed") and t.get("completedAt"):
            cat = t.get("category")
            if not cat: continue
            try:
                dt = datetime.fromisoformat(t["completedAt"])
                hour = dt.hour
                period = "morning" if hour < 12 else ("afternoon" if hour < 18 else "evening")
                
                if cat not in time_prefs: time_prefs[cat] = Counter()
                time_prefs[cat][period] += 1
            except: pass
            
    return {
        "generated_at": datetime.now().isoformat(),
        "user_profile": state.get("userProfile", {}),
        "word_associations": word_associations,
        "category_preferences": dict(cat_counts),
        "time_preferences": {k: dict(v) for k, v in time_prefs.items()}
    }

def save_user_training(state: Dict[str, Any], path: str) -> None:
    """Saves the user's personal AI model to disk."""
    data = generate_user_training_data(state)
    
    # Update in-memory model immediately so we don't need to reload
    global USER_MODEL
    USER_MODEL["word_associations"] = data.get("word_associations", {})
    USER_MODEL["category_preferences"] = data.get("category_preferences", {})
    USER_MODEL["time_preferences"] = data.get("time_preferences", {})
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

def analyze_journal_context(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes the most recent journal entry for sentiment and topics.
    """
    journal = state.get("journal", [])
    if not journal:
        return {"sentiment": "Neutral", "topics": []}
    
    # Look at the latest entry
    latest = journal[0]
    text = strip_html(latest.get("text", "")).lower()
    
    # Simple sentiment keywords
    pos_words = {"good", "great", "happy", "excited", "proud", "love", "awesome", "win", "done", "productive"}
    neg_words = {"bad", "sad", "tired", "stressed", "angry", "hate", "fail", "hard", "difficult", "stuck", "anxious"}
    
    words = set(re.findall(r'\w+', text))
    pos_score = len(words.intersection(pos_words))
    neg_score = len(words.intersection(neg_words))
    
    sentiment = "Neutral"
    if pos_score > neg_score: sentiment = "Positive"
    elif neg_score > pos_score: sentiment = "Negative"
    
    # Topic detection using KB
    kb_keywords = KNOWLEDGE_BASE.get("task_inference", {}).get("keywords", {})
    topics = {kb_keywords[w]["category"] for w in words if w in kb_keywords}
    
    return {"sentiment": sentiment, "topics": list(topics)}

def estimate_duration(text: str) -> int:
    """
    Estimates task duration in minutes based on keywords.
    """
    text = text.lower()
    # Short tasks (< 15 mins)
    if any(w in text for w in ["quick", "call", "email", "msg", "message", "check", "pay", "schedule", "buy", "send"]):
        return 15
    # Medium tasks (15-45 mins)
    if any(w in text for w in ["read", "review", "clean", "meeting", "gym", "workout", "cook", "laundry"]):
        return 45
    # Long tasks (> 45 mins)
    if any(w in text for w in ["write", "report", "code", "design", "study", "project", "plan", "research"]):
        return 90
    return 30 # Default

def suggest_task_by_time(state: Dict[str, Any], minutes: int) -> Optional[Dict[str, Any]]:
    """
    Finds a task that fits within the given time (minutes).
    """
    tasks = state.get("tasks") or []
    candidates = []
    
    for t in tasks:
        if not isinstance(t, dict): continue
        if t.get("completed"): continue
        
        # Only look at active sections
        if t.get("section") not in ("Today", "This Week", "Someday"):
            continue
            
        # Use explicit duration if available (future proofing), otherwise guess
        duration = t.get("estimated_duration") or estimate_duration(t.get("text", ""))
        
        if duration <= minutes:
            candidates.append(t)
            
    if not candidates:
        return None
        
    # Prioritize: Important -> Today -> This Week -> Random
    def section_rank(s):
        if s == "Today": return 0
        if s == "This Week": return 1
        return 2
        
    candidates.sort(key=lambda x: (
        0 if x.get("important") else 1,
        section_rank(x.get("section")),
        random.random()
    ))
    
    return candidates[0]

def rank_tasks_smart(tasks: List[Dict[str, Any]], state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Reorders a list of tasks based on:
    1. Importance (High)
    2. Time of Day fit (Does user usually do this category now?)
    3. Original Order (Stability)
    """
    now = datetime.now()
    hour = now.hour
    period = "morning" if hour < 12 else ("afternoon" if hour < 18 else "evening")
    
    time_prefs = USER_MODEL.get("time_preferences", {})
    
    def score_task(t):
        score = 0
        
        # 1. Importance
        if t.get("important"): score += 10
        
        # 2. Category Time Fit
        cat = t.get("category")
        if cat and cat in time_prefs:
            # How often is this category done in this period?
            period_count = time_prefs[cat].get(period, 0)
            total_count = sum(time_prefs[cat].values())
            if total_count > 0:
                affinity = period_count / total_count
                score += (affinity * 5) # Up to +5 points for perfect time match
        
        # 3. Negate score slightly by order to preserve relative stability for ties
        order_penalty = t.get("order", 0) * 0.001
        return score - order_penalty

    # Sort descending by score
    return sorted(tasks, key=score_task, reverse=True)

def generate_insights(state: Dict[str, Any]) -> Dict[str, str]:
    """
    Generates context-aware advice using the AI engine.
    """
    now = datetime.now()
    hour = now.hour
    today_str = now.date().isoformat()
    journal_context = analyze_journal_context(state)
    
    # --- Data Gathering ---
    tasks = state.get("tasks") or []
    today_tasks = [t for t in tasks if isinstance(t, dict) and t.get("section") == "Today"]
    done_today = [t for t in today_tasks if t.get("completed")]
    incomplete_today = [t for t in today_tasks if not t.get("completed")]
    
    # User History Stats
    weekday_avgs = taskflowanalytics.get_weekday_averages(state)
    current_weekday = now.weekday()
    avg_for_today = weekday_avgs.get(current_weekday, 0)
    
    # Mood
    mood_log = state.get("moods") or []
    today_mood_entry = next((m for m in mood_log if isinstance(m, dict) and m.get("date") == today_str), None)
    mood_guess = today_mood_entry.get("value", "Neutral") if today_mood_entry else "Neutral"
    
    # User Profile
    profile = state.get("userProfile", {})
    name = profile.get("name", "Friend")
    style = profile.get("style", "Gentle")
    
    # Access advice structure (v1.1)
    advice_data = KNOWLEDGE_BASE.get("advice", {})
    generic_advice = advice_data.get("generic", {})
    styles = advice_data.get("styles", {})
    
    # --- AI "Thinking" ---
    advice = ""
    suggestion = ""
    
    # 1. Journal-based Context (High Priority)
    if journal_context["sentiment"] == "Negative":
        advice = f"{name}, I noticed some heavy thoughts in your journal. Be gentle with yourself today."
        mood_guess = "Reflective"
    elif journal_context["sentiment"] == "Positive":
        advice = f"Your journal sounds positive, {name}! Keep that momentum going."
        mood_guess = "Optimistic"
    elif "Dev" in journal_context["topics"]:
        advice = "Deep work mode detected. Stay in the flow."
    
    # 2. New User Detection
    elif len(tasks) < 5:
        advice = random.choice(generic_advice.get("new_user", ["Welcome!"]))
        mood_guess = "Fresh Start"
    
    # 2. Detect Burnout Risk (High activity + Low Mood) or Recovery Mode
    elif len(done_today) > 5 and mood_guess in ("Stressed", "Low energy"):
        style_pool = styles.get(style, styles.get("Gentle", {}))
        pool = style_pool.get("burnout", generic_advice.get("burnout", ["Rest."]))
        advice = random.choice(pool)
    elif mood_guess in ("Stressed", "Low energy") and len(done_today) < 2:
        # Recovery Mode
        style_pool = styles.get(style, styles.get("Gentle", {}))
        pool = style_pool.get("burnout", generic_advice.get("burnout", ["Rest."]))
        advice = random.choice(pool)
        
    # 3. Wrap-up Mode (Evening + Good Progress)
    elif hour >= 18 and len(done_today) >= 3:
        style_pool = styles.get(style, styles.get("Gentle", {}))
        pool = style_pool.get("evening", generic_advice.get("evening", ["Rest."]))
        advice = random.choice(pool)
        mood_guess = "Wrapping Up"
    
    # 4. Specific Task Suggestion (Focus Mode)
    elif incomplete_today and random.random() < 0.7:
        # Prioritize important tasks
        important_tasks = [t for t in incomplete_today if t.get("important")]
        target_task = random.choice(important_tasks) if important_tasks else random.choice(incomplete_today)
        
        task_text = target_task.get("text", "your task")
        
        # Style-based templates
        if style == "Direct":
            templates = [f"Do '{task_text}' now.", f"Focus on '{task_text}'.", f"Next up: '{task_text}'."]
        elif style == "Hype":
            templates = [f"Crush '{task_text}'!", f"You can destroy '{task_text}' right now!", f"Let's go! '{task_text}' is waiting."]
        elif style == "Stoic":
            templates = [f"The work is '{task_text}'.", f"Focus your attention on '{task_text}'.", f"Do what must be done: '{task_text}'."]
        else: # Gentle
            templates = [f"Maybe try '{task_text}' next?", f"How about working on '{task_text}'?", f"A small step on '{task_text}' would be good."]
            
        advice = random.choice(templates)

    # 5. Time-based Advice (if no specific condition met)
    else:
        pool_key = "morning"
        if hour < 11:
            pool_key = "morning"
        elif 11 <= hour < 17:
            pool_key = "afternoon"
        else:
            pool_key = "evening"
            
        # Try to get styled advice, fallback to generic KB
        style_pool = styles.get(style, styles.get("Gentle", {}))
        pool = style_pool.get(pool_key, generic_advice.get(pool_key, ["Keep going."]))
        advice = random.choice(pool)
            
    # 4. Task Suggestion
    # If Someday list has items, suggest one
    someday_tasks = [t for t in tasks if isinstance(t, dict) and t.get("section") == "Someday" and not t.get("completed")]
    if someday_tasks:
        pick = random.choice(someday_tasks)
        suggestion = f"From your Someday list: '{pick.get('text')}'"
    else:
        # Suggest a category based on what's missing today
        cats_today = {t.get("category") for t in today_tasks if t.get("category")}
        if "Health" not in cats_today:
            suggestion = "You haven't planned any Health tasks. Maybe a walk?"
        elif "Personal" not in cats_today and hour > 17:
            suggestion = "Time for a Personal task?"
        else:
            suggestion = "Review your goals for the week."

    # Personalize
    if "{name}" in advice:
        advice = advice.replace("{name}", name)
    elif random.random() < 0.3: # Occasionally prepend name
        advice = f"{name}, {advice.lower()}"

    return {
        "mood_guess": mood_guess,
        "advice": advice,
        "task_suggestion": suggestion
    }
