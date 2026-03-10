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

def listen_command(silent: bool = False) -> str:
    """
    Listens to the microphone and converts voice to text.
    Uses dynamic device selection and improved status reporting.
    """
    recognizer = sr.Recognizer()
    mic_idx = find_best_mic_index()
    
    try:
        with sr.Microphone(device_index=mic_idx) as source:
            if not silent: print(lang.get("audio.calibrating")) 
            recognizer.adjust_for_ambient_noise(source, duration=1.0)
            
            # Use manual threshold if provided in .env
            env_threshold = os.getenv("MIC_ENERGY_THRESHOLD")
            if env_threshold:
                try:
                    recognizer.energy_threshold = float(env_threshold)
                except ValueError:
                    pass
            
            if not silent: print(lang.get("audio.listening_start"))
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            if not silent: print(lang.get("audio.listening_done"))
            text = recognizer.recognize_google(audio, language="uk-UA")
            
            return text
            
    except sr.WaitTimeoutError:
        return ""
    except sr.UnknownValueError:
        if not silent: print(lang.get("audio.recognition_error"))
        return ""
    except Exception as e:
        # If default index fails, it might be a hardware mismatch
        if "device index" in str(e).lower():
            if not silent: print(f"⚠️ Mic Index Error: {e}. Check MIC_INDEX in .env")
        else:
            if not silent: print(lang.get("audio.recording_error", error=e))
        return ""

def _voice_listener_loop(axis_core):
    """Background loop with 'Phrase-Burst' logic (Wake + Command in one go)."""
    print("🎙️ [AXIS]: Voice Listener ACTIVE (Local-First Listening)")
    wake_words = ["аксис", "аксіс", "axis"]
    
    while True:
        try:
            # 1. Listen in silent mode for the wake word
            text = listen_command(silent=True)
            if text:
                query = text.strip().lower()
                
                # Check if wake word is present
                trigger_word = next((w for w in wake_words if w in query), None)
                
                if trigger_word:
                    print(f"🔔 [EVENT]: {trigger_word.upper()} DETECTED")
                    
                    # Clean the command part: "Аксис зроби скріншот" -> "зроби скріншот"
                    clean_command = query.replace(trigger_word, "").strip()
                    
                    if clean_command:
                        # Case A: User said wake word + command in one phrase
                        print(f"👂 [DIRECT COMMAND]: {clean_command}")
                        response = axis_core.think(clean_command, source="voice")
                        print(f"🤖 [AXIS REPLY]: {response}")
                    else:
                        # Case B: User said ONLY wake word, wait for input
                        axis_core.think("озвуч 'Слухаю вас, Командоре'")
                        print("🚀 [LISTENING FOR COMMAND...]")
                        command_text = listen_command(silent=False)
                        
                        if command_text:
                            print(f"👂 [FOLLOW-UP]: {command_text}")
                            response = axis_core.think(command_text, source="voice")
                            print(f"🤖 [AXIS REPLY]: {response}")
                        else:
                            print("💤 [TIMEOUT] Returning to sleep.")
                
        except Exception as e:
            from core.logger import logger
            logger.error(f"audio.listener_loop_error: {e}")
            time.sleep(1)
        
        time.sleep(0.1)

def start_voice_listener(axis_core):
    """Starts the voice listener in a background thread."""
    thread = threading.Thread(target=_voice_listener_loop, args=(axis_core,), daemon=True)
    thread.start()