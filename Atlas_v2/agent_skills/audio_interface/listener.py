import speech_recognition as sr
from core.i18n import lang
import os
import threading
import time

def find_best_mic_index():
    """Dynamically finds the best microphone based on priority keywords."""
    # 1. Allow manual override from .env
    env_index = os.getenv("MIC_INDEX")
    if env_index is not None:
        try:
            return int(env_index)
        except ValueError:
            pass

    # 2. Priority Auto-Discovery
    try:
        mics = sr.Microphone.list_microphone_names()
        
        # Priority 1: High-fidelity MT-MC14
        for i, name in enumerate(mics):
            if "MT-MC14" in name:
                return i
                
        # Priority 2: Standard Realtek Audio
        for i, name in enumerate(mics):
            if "Realtek" in name:
                return i
    except Exception:
        pass

    # Default fallback
    return 0 

class VoiceCommandListener:
    """
    Standard 2026 Audio Input Controller.
    Handles wake-word detection and command capturing with phrase-burst logic.
    """
    def __init__(self, axis_core, device_index: int = None):
        self.axis = axis_core
        self.device_index = device_index if device_index is not None else find_best_mic_index()
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True # Enable auto-adjust
        self.wake_words = ["аксис", "аксіс", "axis"]
        self._running = False
        self._calibrated = False

    def calibrate(self):
        """Initial calibration for ambient noise."""
        try:
            with sr.Microphone(device_index=self.device_index) as source:
                print(f"🎙️ [VOICE]: Calibrating MT-MC14 (Index {self.device_index})...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
                
                # Boost sensitivity if needed
                env_threshold = os.getenv("MIC_ENERGY_THRESHOLD")
                if env_threshold:
                    self.recognizer.energy_threshold = float(env_threshold)
                    self.recognizer.dynamic_energy_threshold = False
                
                print(f"✅ [VOICE]: Ready. Threshold: {self.recognizer.energy_threshold:.1f}")
                self._calibrated = True
        except Exception as e:
            print(f"⚠️ [VOICE]: Calibration Error: {e}")

    def listen_command(self, silent: bool = False) -> str:
        """Captures audio and converts to text via local/cloud engine."""
        if not self._calibrated: self.calibrate()
        
        try:
            with sr.Microphone(device_index=self.device_index) as source:
                if not silent: print(lang.get("audio.listening_start"))
                # Reduced timeout for wake-word (silent) phase to be more responsive
                timeout = 10 if not silent else 5
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=8)
                
                if not silent: print(lang.get("audio.listening_done"))
                return self.recognizer.recognize_google(audio, language="uk-UA")
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            return ""
        except Exception as e:
            if not silent: 
                 if "device index" in str(e).lower():
                     print(f"⚠️ Mic Index {self.device_index} Error.")
                 else:
                     print(f"🎙️ Audio Err: {e}")
            return ""

    def _loop(self):
        """Phrase-Burst background loop."""
        print(f"🎙️ [AXIS]: Voice Listener ACTIVE (Using Mic Index: {self.device_index})")
        while self._running:
            try:
                text = self.listen_command(silent=True)
                if not text: continue
                
                query = text.strip().lower()
                trigger_word = next((w for w in self.wake_words if w in query), None)
                
                if trigger_word:
                    print(f"🔔 [WAKE WORD DETECTED]: {trigger_word}")
                    clean_command = query.replace(trigger_word, "").strip()
                    
                    if clean_command:
                        print(f"🚀 [DIRECT]: {clean_command}")
                        response = self.axis.think(clean_command, source="voice")
                        print(f"🤖 [AXIS]: {response}")
                    else:
                        # Follow-up phase
                        time.sleep(0.5) # Stability pause
                        self.axis.think("озвуч 'Слухаю вас, Командоре'")
                        print("🚀 [LISTENING FOR COMMAND...]")
                        command_text = self.listen_command(silent=False)
                        if command_text:
                            print(f"👂 [FOLLOW-UP]: {command_text}")
                            response = self.axis.think(command_text, source="voice")
                            print(f"🤖 [AXIS]: {response}")
                        else:
                            print("💤 [TIMEOUT] Back to idle.")
            except Exception as e:
                time.sleep(1)

    def start(self):
        """Runs the listener in a daemon thread."""
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

def start_voice_listener(axis_core, device_index: int = None):
    """Bridge for main.py."""
    listener = VoiceCommandListener(axis_core, device_index=device_index)
    listener.start()
    return listener

def listen_command(silent: bool = False, device_index: int = None) -> str:
    """Standalone compatibility wrapper for voice-to-text conversion."""
    return VoiceCommandListener(None, device_index=device_index).listen_command(silent=silent)
