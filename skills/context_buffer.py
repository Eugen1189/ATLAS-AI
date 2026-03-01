import time
from collections import deque
import threading
import json
from datetime import datetime

class ContextBuffer:
    """
    Cognitive Context Buffer for ATLAS.
    Stores short-term interaction history and state.
    """
    
    def __init__(self, max_history=50):
        self.conversation_history = deque(maxlen=max_history)
        self.user_state = {
            "mood": "neutral",
            "activity": "unknown",
            "last_interaction": 0,
            "focus_level": "normal"
        }
        self.active_context = {} # Keys like 'project_name', 'file_open'
        
    def add_interaction(self, user_text, ai_text, intent=None):
        entry = {
            "timestamp": time.time(),
            "user": user_text,
            "ai": ai_text,
            "intent": intent
        }
        self.conversation_history.append(entry)
        self.user_state["last_interaction"] = time.time()
        
    def update_user_state(self, key, value):
        self.user_state[key] = value
        
    def get_context_string(self):
        """Generates a text summary of current context for LLM."""
        history_str = ""
        for item in self.conversation_history:
            t = datetime.fromtimestamp(item['timestamp']).strftime('%H:%M')
            history_str += f"[{t}] User: {item['user']}\nAtlas: {item['ai']}\n"
            
        state_str = f"User State: Mood={self.user_state['mood']}, Activity={self.user_state['activity']}\n"
        
        return f"{state_str}\nRecent Conversation:\n{history_str}"

    def clear(self):
        self.conversation_history.clear()
