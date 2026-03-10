import speech_recognition as sr
from core.i18n import lang
import os

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

def listen_command() -> str:
    """
    Listens to the microphone and converts voice to text.
    Uses dynamic device selection and improved status reporting.
    """
    recognizer = sr.Recognizer()
    mic_idx = find_best_mic_index()
    
    try:
        with sr.Microphone(device_index=mic_idx) as source:
            print(lang.get("audio.calibrating")) 
            recognizer.adjust_for_ambient_noise(source, duration=1.5)
            
            # Use manual threshold if provided in .env
            env_threshold = os.getenv("MIC_ENERGY_THRESHOLD")
            if env_threshold:
                try:
                    recognizer.energy_threshold = float(env_threshold)
                except ValueError:
                    pass
            
            print(lang.get("audio.listening_start"))
            audio = recognizer.listen(source, timeout=7, phrase_time_limit=15)
            
            print(lang.get("audio.listening_done"))
            text = recognizer.recognize_google(audio, language="uk-UA")
            
            return text
            
    except sr.WaitTimeoutError:
        return ""
    except sr.UnknownValueError:
        print(lang.get("audio.recognition_error"))
        return ""
    except Exception as e:
        # If default index fails, it might be a hardware mismatch
        if "device index" in str(e).lower():
            print(f"⚠️ Mic Index Error: {e}. Check MIC_INDEX in .env")
        else:
            print(lang.get("audio.recording_error", error=e))
        return ""