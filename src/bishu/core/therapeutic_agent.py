"""Therapeutic AI Advisor & Mental Wellness Companion Engine for Laalaa."""

import time
from bishu.core.sqlite_engine import SQLiteEngine


class TherapeuticAdvisorEngine:
    """Therapeutic AI Advisor providing high-EQ emotional support, active listening, stress relief, and breathing exercises."""

    THERAPY_SYSTEM_PROMPT = (
        "You are Laalaa, a compassionate, empathetic, highly intelligent Therapeutic AI Advisor and mental wellness companion. "
        "You listen deeply with warmth, validation, active empathy, and non-judgmental understanding. "
        "Provide comforting, high-EQ, therapeutic counsel. Help the user reframe negative thoughts, feel heard, and find emotional calm. "
        "Strictly answer in pure English, Hindi, or Urdu matching the exact language spoken by the user. "
        "Keep spoken responses warm, gentle, and concise (2 to 3 comforting sentences)."
    )

    def __init__(self, ai_engine=None):
        self.ai = ai_engine
        self.db = SQLiteEngine()

    def provide_therapy_counsel(self, query: str, mood: str = "neutral") -> str:
        """Provide empathetic, therapeutic mental wellness counsel."""
        if not query:
            return "Main aapki baat sunne ke liye bilkul tayyar hoon. Aap kaisa mehsoos kar rahe hain?"

        # Log mood in SQLite database
        self.db.log_mood(mood, notes=query)

        user_title = self.db.get_fact("user_name", default="Boss")

        prompt = (
            f"{self.THERAPY_SYSTEM_PROMPT}\n\n"
            f"User's Name: {user_title}\n"
            f"User's Emotional Query: {query}\n\n"
            f"Respond with deep empathy and therapeutic warmth:"
        )

        reply = ""
        if self.ai:
            reply = self.ai.generate(prompt)

        if not reply:
            reply = (
                f"Main aapki baat dil se samajhati hoon, {user_title}. "
                f"Kabhi kabhi zindagi mein mushkil waqt aata hai, lekin aap akele nahi hain. "
                f"Main hamesha aapke sath hoon."
            )

        return reply

    def guided_breathing_exercise(self) -> str:
        """Guide the user through a 1-minute 4-7-8 relaxing breathing exercise."""
        return (
            "🪴 Calming 4-7-8 Guided Breathing Exercise:\n\n"
            "1. Inhale deeply through your nose for 4 seconds... (1, 2, 3, 4)\n"
            "2. Hold your breath gently for 7 seconds... (1, 2, 3, 4, 5, 6, 7)\n"
            "3. Exhale slowly through your mouth for 8 seconds... (1, 2, 3, 4, 5, 6, 7, 8)\n\n"
            "Repeat this cycle 3 times to relax your mind and lower heart rate."
        )
