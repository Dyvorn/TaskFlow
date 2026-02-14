# c:\Users\Lennard Finn Penzler\Documents\VSC_Projects\todo_app\TaskFlow\taskflowai.py

import os
import json
import re
import random
from datetime import datetime
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
        "updated_at": "2026-02-14",
        "notes": "Default embedded KB."
    },
    "task_inference": {
        "priority_keywords": ["urgent", "asap", "important", "deadline", "now", "🔥", "❗", "critical", "alert"],
        "section_keywords": {
            "Tomorrow": ["tomorrow", "tmrw"],
            "This Week": ["next week", "this week", "weekend"],
            "Someday": ["later", "someday", "eventually", "maybe", "idea"]
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
            
            # Creative (Niche)
            "design": {"category": "Creative", "important": False},
            "sketch": {"category": "Creative", "important": False},
            "render": {"category": "Creative", "important": True},
            "edit": {"category": "Creative", "important": False},
            "video": {"category": "Creative", "important": True},
            "photo": {"category": "Creative", "important": False},
            "write": {"category": "Creative", "important": False},
            "blog": {"category": "Creative", "important": False},
            
            # Household
            "groceries": {"category": "Personal", "important": False},
            "cook": {"category": "Personal", "important": False},
            "clean": {"category": "Personal", "important": False},
            "laundry": {"category": "Personal", "important": False},
            "plants": {"category": "Personal", "important": False},
            "dishes": {"category": "Personal", "important": False},
            "mom": {"category": "Personal", "important": True},
            "dad": {"category": "Personal", "important": True},
            
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
            
            # Finance
            "pay": {"category": "Finance", "important": True},
            "bill": {"category": "Finance", "important": True},
            "invoice": {"category": "Finance", "important": True},
            "tax": {"category": "Finance", "important": True},
            "budget": {"category": "Finance", "important": False},
            "invest": {"category": "Finance", "important": False},
            
            # Learning
            "study": {"category": "Learning", "important": True},
            "read": {"category": "Learning", "important": False},
            "course": {"category": "Learning", "important": True},
            "practice": {"category": "Learning", "important": False},
            "learn": {"category": "Learning", "important": False}
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
    "category_preferences": {}  # "Work": 10
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
        except Exception:
            pass

# ============================================================================
# AI LOGIC
# ============================================================================

def _infer_metadata(text: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Infers category and priority using a hybrid of user history and pre-trained data.
    """
    text_lower = text.lower()
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
    
    for w in words:
        if w in kb_keywords:
            data = kb_keywords[w]
            # Base weight for KB matches
            kb_cat_scores[data["category"]] += 2 
            if data.get("important", False):
                kb_prio_scores += 2

    # 3. Priority Keywords (Explicit)
    prio_kws = inference_data.get("priority_keywords", ["urgent", "asap", "important", "deadline", "now", "🔥", "❗"])
    explicit_prio = any(x in text_lower for x in prio_kws)
    
    # 4. Decision Logic
    # Merge scores (User history is additive to KB)
    final_cat_scores = kb_cat_scores + user_cat_scores
    
    category = None
    if final_cat_scores:
        category = final_cat_scores.most_common(1)[0][0]
        
    # Priority threshold
    # If explicit keyword found OR combined score is high enough
    is_important = explicit_prio or (user_prio_scores + kb_prio_scores >= 2)
    
    # 5. Section Inference
    section = "Today"
    section_kws = inference_data.get("section_keywords", {})
    found_section = False
    for sec_name, kws in section_kws.items():
        if any(kw in text_lower for kw in kws):
            section = sec_name
            found_section = True
            break
            
    if not found_section:
        if "tomorrow" in text_lower: section = "Tomorrow"
        elif "next week" in text_lower: section = "This Week"
        elif any(x in text_lower for x in ["later", "someday", "eventually"]): section = "Someday"
    
    return {"category": category, "important": is_important, "section": section}

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
                     meta = _infer_metadata(p.strip(), state)
                     results.append({
                         "text": p.strip(),
                         "category": meta["category"],
                         "important": meta["important"],
                         "section": meta["section"]
                     })
        else:
            # Remove common list markers
            clean = re.sub(r'^[-*•\d\.]+\s+', '', clean)
            if not clean: continue
            
            meta = _infer_metadata(clean, state)
            results.append({
                "text": clean,
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
            
    return {
        "generated_at": datetime.now().isoformat(),
        "user_profile": state.get("userProfile", {}),
        "word_associations": word_associations,
        "category_preferences": dict(cat_counts)
    }

def save_user_training(state: Dict[str, Any], path: str) -> None:
    """Saves the user's personal AI model to disk."""
    data = generate_user_training_data(state)
    
    # Update in-memory model immediately so we don't need to reload
    global USER_MODEL
    USER_MODEL["word_associations"] = data.get("word_associations", {})
    USER_MODEL["category_preferences"] = data.get("category_preferences", {})
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

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

def generate_insights(state: Dict[str, Any]) -> Dict[str, str]:
    """
    Generates context-aware advice using the AI engine.
    """
    now = datetime.now()
    hour = now.hour
    today_str = now.date().isoformat()
    
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
    
    # 1. New User Detection
    if len(tasks) < 5:
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
