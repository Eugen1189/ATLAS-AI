import threading
import time
import random

class PersonalityEngine:
    """
    Manages ATLAS's emotional state, proactivity, and tone.
    Ensures the system adapts to the user and avoids being annoying.
    """
    
    def __init__(self):
        # State Variables
        self.irritation_threshold = 0  # 0 to 10. High = user annoyed.
        self.interaction_count = 0     # Number of unsolicited interactions
        self.last_interaction_time = 0
        self.silent_mode_until = 0     # Timestamp for silence
        
        # User Context
        self.focus_level = "normal"    # normal, high, low
        self.current_activity = "idle"
        
    def update_interaction(self, user_response_type):
        """
        Updates internal state based on user reaction.
        user_response_type: 'positive', 'negative', 'ignored', 'command'
        """
        current_time = time.time()
        
        if user_response_type == 'negative':
            self.irritation_threshold += 3
            self.silent_mode_until = current_time + 3600 # 1 hour silence
            print("🤐 [PERSONALITY] User annoyed. Entering Silent Mode for 1h.")
            
        elif user_response_type == 'ignored':
            self.irritation_threshold += 1
            if self.irritation_threshold >= 2:
                self.silent_mode_until = current_time + 1800 # 30 min silence
                print("🤐 [PERSONALITY] Ignored twice. Entering Silent Mode for 30m.")
                
        elif user_response_type == 'positive' or user_response_type == 'command':
            self.irritation_threshold = max(0, self.irritation_threshold - 1)
            self.interaction_count = 0 # Reset count on positive engagement
            
        self.last_interaction_time = current_time

    def should_intervene(self):
        """
        Decides if ATLAS should make a proactive suggestion.
        """
        if time.time() < self.silent_mode_until:
            return False
            
        # Don't interrupt high focus unless critical
        if self.focus_level == "high":
            return False
            
        return True

    def get_system_instruction(self):
        """Returns the dynamic system prompt instructions based on state."""
        base_personality = "You are ATLAS, an advanced AI Operating System and companion."
        
        tone = "Professional but friendly."
        if self.focus_level == "high":
            tone = "Concise, minimal, efficient. Do not chat."
        elif self.focus_level == "low":
            tone = "Conversational, encouraging, perhaps a bit witty."
            
        if self.irritation_threshold > 0:
            tone += " Be extremely apologetic and brief."
            
        return f"{base_personality}\n\nCAPABILITIES:\n- You have access to a VISION module. If the user asks to 'turn on camera', 'start vision', 'watch', or 'zapuste kameru', you MUST use the 'vision_control' tool or route to the 'Vision' department.\n- You have FULL ACCESS to system resources (CPU, RAM, Battery, Temperature). You can ALWAYS check them using `sys_ops` or `scanner` tools. NEVER say you cannot check system status. Using `psutil` and `PowerShell` is your native ability.\n\nTRANSCRIPTION HANDLING:\n- You work with the Ukrainian language. Transcription may be error-prone (Latin characters, distorted words). Your task is to guess the user's intent. If you hear something like 'camera' or 'zapuste' - it is a command for the Vision department.\n\nCurrent Tone: {tone}\nUser Focus: {self.focus_level}"
