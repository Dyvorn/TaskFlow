# c:\Users\Lennard Finn Penzler\Documents\VSC_Projects\todo_app\TaskFlow\taskflowai.py

import re
import random
from datetime import datetime
from collections import Counter
from typing import Any, Dict, List
import taskflowanalytics

# ============================================================================
# PRE-TRAINED KNOWLEDGE BASE
# ============================================================================
# This acts as the "seed" for the AI, allowing it to be smart even
# when the user has no history.

KNOWLEDGE_BASE = {
    "keywords": {
        # Work
        "email": {"category": "Work", "prio": False},
        "call": {"category": "Work", "prio": False},
        "meeting": {"category": "Work", "prio": True},
        "report": {"category": "Work", "prio": True},
        "presentation": {"category": "Work", "prio": True},
        "code": {"category": "Work", "prio": True},
        "bug": {"category": "Work", "prio": True},
        "client": {"category": "Work", "prio": True},
        "review": {"category": "Work", "prio": False},
        # Health
        "gym": {"category": "Health", "prio": True},
        "workout": {"category": "Health", "prio": True},
        "walk": {"category": "Health", "prio": False},
        "water": {"category": "Health", "prio": False},
        "meditate": {"category": "Health", "prio": False},
        "doctor": {"category": "Health", "prio": True},
        # Personal
        "groceries": {"category": "Personal", "prio": False},
        "clean": {"category": "Personal", "prio": False},
        "laundry": {"category": "Personal", "prio": False},
        "read": {"category": "Personal", "prio": False},
        "mom": {"category": "Personal", "prio": True},
        "dad": {"category": "Personal", "prio": True},
        # Finance
        "budget": {"category": "Finance", "prio": True},
        "pay": {"category": "Finance", "prio": True},
        "bill": {"category": "Finance", "prio": True},
        "tax": {"category": "Finance", "prio": True},
        # Learning
        "study": {"category": "Learning", "prio": True},
        "course": {"category": "Learning", "prio": True},
        "practice": {"category": "Learning", "prio": False},
        # Admin / Misc
        "invoice": {"category": "Finance", "prio": True},
        "deadline": {"category": "Work", "prio": True},
        "schedule": {"category": "Work", "prio": False},
    },
    "advice": {
        "morning": [
            "Eat the frog: Tackle your hardest task first while your brain is fresh.",
            "Review your main goal before checking emails.",
            "A calm morning sets the tone. Breathe.",
            "What is the one thing that would make today a success?"
        ],
        "afternoon": [
            "Energy dipping? A 10-minute walk can reset your brain.",
            "Switch to administrative tasks if your focus is fading.",
            "Hydrate. Your brain needs water to focus.",
            "Take a moment to celebrate what you've already done."
        ],
        "evening": [
            "Plan tomorrow tonight to sleep with a clear mind.",
            "Reflect on one small win from today.",
            "Disconnect to recharge. Screens off soon.",
            "You've done enough. It's time to rest."
        ],
        "burnout": [
            "You've been pushing hard. Rest is productive too.",
            "It's okay to reschedule non-essentials.",
            "Be gentle with yourself today. Survival is enough.",
            "Take a real break. Not a scrolling break."
        ],
        "new_user": [
            "Welcome! Start by adding just one small task.",
            "Don't worry about filling every box. Just flow.",
            "Try the 'Brain Dump' feature to clear your mind."
        ]
    }
}

STYLED_ADVICE = {
    "Gentle": {
        "morning": ["Good morning. Start gently.", "One small step is enough.", "Be kind to yourself today."],
        "afternoon": ["Take a breath. You're doing fine.", "Hydrate and stretch."],
        "evening": ["Rest is productive too.", "Let go of today."],
        "burnout": ["Please rest. You matter more than productivity."],
        "recovery": ["It's okay to have a slow day. Just existing is enough.", "Be gentle. Small wins count double today."],
        "wrapup": ["You've done well. Time to wind down.", "Close the loop for today."]
    },
    "Direct": {
        "morning": ["Morning. What's the target?", "Focus. Execute.", "Prioritize the hard stuff."],
        "afternoon": ["Stay on track.", "Don't drift. Finish the block."],
        "evening": ["Review the wins. Plan tomorrow.", "Done is done."],
        "burnout": ["Efficiency is dropping. Take a break to reset."],
        "recovery": ["Low energy? Focus on the one absolute must-do.", "Cut the fluff. Do the essential."],
        "wrapup": ["Wrap it up. Plan tomorrow. Disconnect.", "Mission complete. Shut it down."]
    },
    "Stoic": {
        "morning": ["The day has begun. Do what is necessary.", "Amor Fati.", "Focus on what you control."],
        "afternoon": ["Endurance is a muscle.", "Stay present."],
        "evening": ["Reflect without judgment.", "The day is finished."],
        "burnout": ["The mind needs rest to sharpen the edge."],
        "recovery": ["Accept your limits today. Work within them.", "Rest is not idleness; it is preparation."],
        "wrapup": ["The day's work is done. Be at peace.", "Prepare the mind for tomorrow."]
    },
    "Hype": {
        "morning": ["Let's CRUSH this day!", "Wake up and win!", "Let's GO!"],
        "afternoon": ["Keep that momentum rolling!", "You're on fire!"],
        "evening": ["What a day! High five!", "Rest up, champion."],
        "burnout": ["Recharge those batteries! You're a machine!"],
        "recovery": ["Even champions take rest days! Recover hard!", "Listen to your body so you can win tomorrow!"],
        "wrapup": ["Victory lap! You crushed it today!", "Celebrate the wins! Time to chill."]
    }
}

# ============================================================================
# AI LOGIC
# ============================================================================

def _infer_metadata(text: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Infers category and priority using a hybrid of user history and pre-trained data.
    """
    text_lower = text.lower()
    words = re.findall(r'\w+', text_lower)
    
    # 1. User History Learning (Personalized)
    user_cat_scores = Counter()
    user_prio_scores = 0
    
    tasks = state.get("tasks") or []
    # Simple "Bag of Words" learning from existing tasks
    for t in tasks:
        if not isinstance(t, dict): continue
        cat = t.get("category")
        if not cat: continue
        
        # If this task's text shares words with input, boost its category
        t_words = set(re.findall(r'\w+', t.get("text", "").lower()))
        common = t_words.intersection(words)
        if common:
            weight = len(common)
            user_cat_scores[cat] += weight
            if t.get("important"):
                user_prio_scores += weight

    # 2. Pre-trained Knowledge Base (General)
    kb_cat_scores = Counter()
    kb_prio_scores = 0
    
    for w in words:
        if w in KNOWLEDGE_BASE["keywords"]:
            data = KNOWLEDGE_BASE["keywords"][w]
            # Base weight for KB matches
            kb_cat_scores[data["category"]] += 2 
            if data["prio"]:
                kb_prio_scores += 2

    # 3. Priority Keywords (Explicit)
    explicit_prio = any(x in text_lower for x in ["urgent", "asap", "important", "deadline", "now", "🔥", "❗"])
    
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
    if "tomorrow" in text_lower:
        section = "Tomorrow"
    elif "next week" in text_lower:
        section = "This Week"
    elif any(x in text_lower for x in ["later", "someday", "eventually"]):
        section = "Someday"
    
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
    
    # --- AI "Thinking" ---
    advice = ""
    suggestion = ""
    
    # 1. New User Detection
    if len(tasks) < 5:
        advice = random.choice(KNOWLEDGE_BASE["advice"]["new_user"])
        mood_guess = "Fresh Start"
    
    # 2. Detect Burnout Risk (High activity + Low Mood) or Recovery Mode
    elif len(done_today) > 5 and mood_guess in ("Stressed", "Low energy"):
        pool = STYLED_ADVICE.get(style, STYLED_ADVICE["Gentle"]).get("burnout", KNOWLEDGE_BASE["advice"]["burnout"])
        advice = random.choice(pool)
    elif mood_guess in ("Stressed", "Low energy") and len(done_today) < 2:
        # Recovery Mode
        pool = STYLED_ADVICE.get(style, STYLED_ADVICE["Gentle"]).get("recovery", KNOWLEDGE_BASE["advice"]["burnout"])
        advice = random.choice(pool)
        
    # 3. Wrap-up Mode (Evening + Good Progress)
    elif hour >= 18 and len(done_today) >= 3:
        pool = STYLED_ADVICE.get(style, STYLED_ADVICE["Gentle"]).get("wrapup", KNOWLEDGE_BASE["advice"]["evening"])
        advice = random.choice(pool)
        mood_guess = "Wrapping Up"
    
    # 3. Time-based Advice (if no specific condition met)
    else:
        pool_key = "morning"
        if hour < 11:
            pool_key = "morning"
        elif 11 <= hour < 17:
            pool_key = "afternoon"
        else:
            pool_key = "evening"
            
        # Try to get styled advice, fallback to generic KB
        pool = STYLED_ADVICE.get(style, STYLED_ADVICE["Gentle"]).get(pool_key, KNOWLEDGE_BASE["advice"][pool_key])
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
