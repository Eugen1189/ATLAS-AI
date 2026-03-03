import speech_recognition as sr
from core.i18n import lang

def listen_command() -> str:
    """
    Listens to the microphone and converts voice to text.
    This is not an LLM tool, this is a function for main.py.
    """
    recognizer = sr.Recognizer()
    
    with sr.Microphone() as source:
        print(lang.get("audio.listening_done")) # Calibrating
        recognizer.adjust_for_ambient_noise(source, duration=1)
        
        print(lang.get("audio.listening_start"))
        try:
            # Wait max 5 seconds for phrase start, and max 15 seconds for the phrase itself
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
            
            print(lang.get("audio.listening_done"))
            # Use Google Speech Recognition (can specify 'uk-UA' or 'en-US')
            text = recognizer.recognize_google(audio, language="uk-UA")
            
            return text
            
        except sr.WaitTimeoutError:
            print(lang.get("audio.listening_done")) # Silence -> done/idle
            return ""
        except sr.UnknownValueError:
            print(lang.get("audio.recognition_error"))
            return ""
        except Exception as e:
            print(lang.get("audio.recording_error", error=e))
            return ""