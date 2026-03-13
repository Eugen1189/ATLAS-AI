import speech_recognition as sr
from core.i18n import lang
import os
import threading
import time
from .processor import transcribe_audio, speak

def find_best_mic_index():
    """Dynamically finds the best microphone based on priority keywords."""
    env_index = os.getenv("MIC_INDEX")
    if env_index is not None:
        try: return int(env_index)
        except ValueError: pass

    try:
        mics = sr.Microphone.list_microphone_names()
        for i, name in enumerate(mics):
            if "MT-MC14" in name: return i
        for i, name in enumerate(mics):
            if "Realtek" in name: return i
    except Exception: pass
    return 0 

class VoiceCommandListener:
    """
    Standard 2026 Audio Input Controller (v2.9.6).
    Handles wake-word detection with Sub-0.5s response.
    """
    def __init__(self, axis_core, device_index: int = None):
        self.axis = axis_core
        self.device_index = device_index if device_index is not None else find_best_mic_index()
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.wake_words = ["аксис", "аксіс", "axis"]
        self._running = False
        self._calibrated = False

    def calibrate(self):
        """Initial calibration for ambient noise."""
        try:
            with sr.Microphone(device_index=self.device_index) as source:
                print(f"🎙️ [VOICE]: Calibrating (Index {self.device_index})...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
                self._calibrated = True
        except Exception as e:
            print(f"⚠️ [VOICE]: Calibration Error: {e}")

    def listen_command(self, silent: bool = False) -> str:
        """Captures audio and transcribes via processor (v2.9.6)."""
        if not self._calibrated: self.calibrate()
        try:
            with sr.Microphone(device_index=self.device_index) as source:
                if not silent: print(lang.get("audio.listening_start"))
                timeout = 10 if not silent else 5
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=8)
                if not silent: print(lang.get("audio.listening_done"))
                # Use Universal Transcriber
                return transcribe_audio(audio)
        except (sr.WaitTimeoutError, sr.UnknownValueError): return ""
        except Exception as e:
            if not silent: print(f"🎙️ Audio Err: {e}")
            return ""

    def _loop(self):
        """Phrase-Burst loop with Immediate Feedback & Auto-Voice."""
        print(f"🎙️ [AXIS]: Voice Pipeline v2.9.6 ACTIVE (Mic: {self.device_index})")
        while self._running:
            try:
                # 1. Listen for background noise (passive)
                text = self.listen_command(silent=True)
                if not text: continue
                
                query = text.strip().lower()
                trigger_word = next((w for w in self.wake_words if w in query), None)
                
                if trigger_word:
                    print(f"🔔 [WAKE WORD]: {trigger_word}")
                    clean_command = query.replace(trigger_word, "").strip()
                    
                    if clean_command:
                        # 2a. Direct Command Execution
                        print(f"🚀 [DIRECT]: {clean_command}")
                        response = self.axis.think(clean_command, source="voice")
                        print(f"🤖 [AXIS]: {response}")
                        speak(response) # Auto-Voice (v2.9.6)
                    else:
                        # 2b. Wake-word only: Sub-0.5s Greeting
                        speak("Слухаю вас, Командоре") # Direct TTS call
                        print("🚀 [LISTENING FOR COMMAND...]")
                        command_text = self.listen_command(silent=False)
                        if command_text:
                            print(f"👂 [FOLLOW-UP]: {command_text}")
                            response = self.axis.think(command_text, source="voice")
                            print(f"🤖 [AXIS]: {response}")
                            speak(response) # Auto-Voice
                        else:
                            print("💤 [TIMEOUT] Back to idle.")
            except Exception as e:
                time.sleep(1)

    def start(self):
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

def start_voice_listener(axis_core, device_index: int = None):
    listener = VoiceCommandListener(axis_core, device_index=device_index)
    listener.start()
    return listener

def listen_command(silent: bool = False, device_index: int = None) -> str:
    """Standard STT bridge (v2.9.6)."""
    return VoiceCommandListener(None, device_index=device_index).listen_command(silent=silent)
