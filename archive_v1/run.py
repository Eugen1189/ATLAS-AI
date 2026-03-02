import os
import sys
import time
import threading
import colorama
from colorama import Fore, Style

# Ensure we can import from core/skills
sys.path.append(os.path.join(os.path.dirname(__file__), 'core'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'skills'))

from core.vision_manager import VisionManager
from core.voice_control import VoiceControl
from skills.launcher import Launcher
import config

# Initialize Colorama
colorama.init(autoreset=True)

class AtlasSystem:
    def __init__(self):
        self.vision = VisionManager()
        self.voice = VoiceControl(
            access_key=config.PICOVOICE_ACCESS_KEY,
            command_callback=self._on_voice_command,
            status_callback=self._on_voice_status,
            model_size="tiny" # Keep it fast
        )
        self.launcher = Launcher()
        self.is_running = True
        
    def start(self):
        print(f"{Fore.CYAN}🚀 [SYSTEM] Starting ATLAS...")
        
        # Start Voice Control (Always On)
        self.voice.start()
        
        print(f"{Fore.GREEN}✅ [SYSTEM] ATLAS is online.")
        print(f"{Fore.YELLOW}ℹ️  [INFO] WAKE WORD: 'Jarvis' (Default).")
        print(f"{Fore.YELLOW}ℹ️  [INFO] Say 'Jarvis' then 'Start Vision' to activate eyes.")
        print(f"{Fore.YELLOW}ℹ️  [INFO] Say 'Jarvis' then 'Open Chrome' to launch apps.")

        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        print(f"\n{Fore.RED}🛑 [SYSTEM] Shutting down...")
        self.is_running = False
        self.vision.stop()
        self.voice.stop()
        print(f"{Fore.RED}✅ [SYSTEM] Shutdown complete.")

    def _on_voice_status(self, status):
        # Visual feedback for voice status
        if status == "listening":
            print(f"{Fore.MAGENTA}🎤 [VOICE] Listening...")
        elif status == "thinking":
            print(f"{Fore.MAGENTA}🧠 [VOICE] Analyzing...")
        elif status == "idle":
            print(f"{Fore.DK_GRAY}zzz [VOICE] Idle")

    def _on_voice_command(self, text):
        if not text: return
        
        command = text.lower()
        print(f"{Fore.CYAN}🗣️  [COMMAND] '{command}'")
        
        # --- COMMAND MATCHING ---
        
        # 1. Vision Control
        if "start" in command and ("vision" in command or "camera" in command or "eyes" in command):
            print(f"{Fore.GREEN}👁️ [ATLAS] Starting Vision System...")
            self.vision.start()
            
        elif "stop" in command and ("vision" in command or "camera" in command):
            print(f"{Fore.RED}👁️ [ATLAS] Stopping Vision System...")
            self.vision.stop()
            
        # 2. App Launching
        elif "open" in command or "launch" in command:
            # Extract app name (simple heuristic)
            parts = command.split()
            if "open" in parts: idx = parts.index("open")
            else: idx = parts.index("launch")
            
            if idx + 1 < len(parts):
                app_name = " ".join(parts[idx+1:])
                print(f"{Fore.BLUE}🚀 [ATLAS] Opening {app_name}...")
                result = self.launcher.open_app(app_name)
                print(f"{Fore.BLUE}   > {result}")
        
        # 3. System Control
        elif "terminate" in command or "shutdown" in command:
            self.stop()
            
        # 4. Fallback
        else:
             print(f"{Fore.YELLOW}⚠️ [ATLAS] Unknown command.")

if __name__ == "__main__":
    app = AtlasSystem()
    app.start()
