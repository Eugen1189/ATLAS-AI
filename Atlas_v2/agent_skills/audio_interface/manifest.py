import os
import time
import pyttsx3
from core.i18n import lang
from .listener import listen_command
from core.logger import logger
from core.skills.wrapper import agent_tool

def _play_audio(fpath: str):
    """Internal audio player for saved files."""
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(fpath)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy(): pygame.time.Clock().tick(15)
        pygame.mixer.quit()
    except Exception: os.system(f'start /min "" "{fpath}"')

def _clean_text_for_speech(text: str) -> str:
    """Removes Markdown and technical symbols for clear speech."""
    import re
    # Remove markdown formatting
    text = re.sub(r'[*_#`~>\[\]\(\)]', '', text)
    # Remove code blocks and backticks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    # Remove multi-newlines
    text = re.sub(r'\n+', ' ', text)
    return text.strip()

@agent_tool
def speak(text: str, **kwargs) -> str:
    """
    Озвучує текст вголос (Offline TTS). 
    Можна вказати voice_index (ціле число) або speed (множник, за замовчуванням 1.0).
    """
    speed_factor = kwargs.get("speed", 1.0)
    voice_idx = kwargs.get("voice_index")
    
    # Clean text before speaking
    clean_text = _clean_text_for_speech(text)
    if not clean_text:
        return "Nothing to speak (text was empty after cleaning)."

    try:
        engine = pyttsx3.init()
        
        # 1. Налаштування швидкості (170 - золота середина)
        base_rate = 170
        engine.setProperty('rate', int(base_rate * speed_factor))
        
        # 2. Вибір голосу
        voices = engine.getProperty('voices')
        if voice_idx is not None and 0 <= int(voice_idx) < len(voices):
            engine.setProperty('voice', voices[int(voice_idx)].id)
        else:
            uk_keywords = ["ukrainian", "uk-ua", "olena", "anatol", "ирина", "ukr"]
            for v in voices:
                if any(k in v.name.lower() or k in v.id.lower() for k in uk_keywords):
                    engine.setProperty('voice', v.id)
                    break
            else:
                if len(voices) > 1:
                    engine.setProperty('voice', voices[1].id)

        engine.say(clean_text)
        engine.runAndWait()
        engine.stop()
        
        return f"Vocal confirmation: '{clean_text}'"
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        return f"TTS Local Error: {e}"

@agent_tool
def listen_for_voice(**kwargs) -> str:
    """Standard 2026 Microphone Input (Voice-to-Text)."""
    try:
        text = listen_command()
        return f"Vocal Command Capture: '{text}'" if text else "Silence."
    except Exception as e: 
        return f"Mic Err: {e}"

@agent_tool
def voice_alert(level: str = "warning", **kwargs) -> str:
    """Standard 2026 System Alerts: Play predefined audio notification signals."""
    msg = "AXIS System Warning: Action Required." if level == "warning" else "Task Completed Successfully."
    return speak(msg, speed=1.1)

EXPORTED_TOOLS = [speak, listen_for_voice, voice_alert]

