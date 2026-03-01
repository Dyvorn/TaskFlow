import re
from typing import List, Dict, Optional
from datetime import datetime

class EmailService:
    """
    Handles connection to email providers and parsing of email content
    into potential tasks with extracted metadata for integrations.
    """
    def __init__(self):
        # Placeholder: In a real app, initialize IMAP/API clients here (e.g., Gmail API)
        pass

    def fetch_recent_emails(self, limit: int = 5) -> List[Dict]:
        """
        Fetches recent emails. Currently returns mock data for demonstration.
        """
        # Mock data representing what we might get from an API
        return [
            {
                "id": "e1",
                "subject": "Project Kickoff Meeting",
                "sender": "manager@company.com",
                "body": "Hi team, let's meet at the Conference Room A tomorrow at 10 AM to discuss the new roadmap.",
                "received_at": datetime.now().isoformat()
            },
            {
                "id": "e2",
                "subject": "Lunch at Joe's Pizza",
                "sender": "friend@email.com",
                "body": "Hey, want to grab lunch at Joe's Pizza on Main St today?",
                "received_at": datetime.now().isoformat()
            }
        ]

    def parse_email_to_task(self, email: Dict) -> Dict:
        """
        Parses an email dictionary into a standardized task format.
        Extracts potential locations and dates for Maps/Calendar integration.
        """
        text = f"{email['subject']} {email['body']}"
        
        return {
            "source": "email",
            "source_id": email["id"],
            "text": email["subject"], # Use subject as main task text
            "description": email["body"],
            "extracted_location": self._extract_location(text),
            "extracted_date": self._extract_date_hint(text),
            "meta": {
                "sender": email["sender"],
                "received": email["received_at"]
            }
        }

    def _extract_location(self, text: str) -> Optional[str]:
        # Heuristic: Look for "at [Capitalized Words]" to guess a location
        match = re.search(r"\bat\s+((?:[A-Z][a-zA-Z0-9']+\s?)+)", text)
        if match:
            candidate = match.group(1).strip()
            if candidate.lower() not in ["the", "a", "an", "my", "our", "least", "most"]:
                return candidate
        return None

    def _extract_date_hint(self, text: str) -> Optional[str]:
        # Heuristic: Look for common time keywords
        text_lower = text.lower()
        keywords = ["today", "tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for k in keywords:
            if k in text_lower:
                return k
        
        # Look for simple time patterns like "10 AM"
        time_match = re.search(r"\d{1,2}(?::\d{2})?\s?(?:am|pm|AM|PM)", text)
        if time_match:
            return time_match.group(0)
            
        return None