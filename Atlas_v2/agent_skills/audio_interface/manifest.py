import os
import time
import pyttsx3
from core.i18n import lang
from .listener import listen_command
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

@agent_tool
def speak(text: str, **kwargs) -> str:
    """
    Озвучує текст вголос (Offline TTS). 
    Можна вказати voice_index (центне число) або speed (множник, за замовчуванням 1.0).
    """
    speed_factor = kwargs.get("speed", 1.0)
    voice_idx = kwargs.get("voice_index")
    
    try:
        engine = pyttsx3.init()
        
        # 1. Налаштування швидкості (170 - золота середина для природності)
        base_rate = 170
        engine.setProperty('rate', int(base_rate * speed_factor))
        
        # 2. Отримання списку голосів
        voices = engine.getProperty('voices')
        
        # Логуємо доступні голоси для користувача (видно в терміналі)
        logger.info(f"Audio.TTS: Found {len(voices)} system voices.")
        for i, v in enumerate(voices):
             logger.debug(f"Voice [{i}]: {v.name}")

        # 3. Вибір голосу
        if voice_idx is not None and 0 <= int(voice_idx) < len(voices):
            engine.setProperty('voice', voices[int(voice_idx)].id)
        else:
            # Спроба знайти український голос автоматично (просунутий пошук)
            uk_keywords = ["ukrainian", "uk-ua", "olena", "anatol", "ирина", "ukr"]
            found_uk = False
            for v in voices:
                if any(k in v.name.lower() or k in v.id.lower() for k in uk_keywords):
                    engine.setProperty('voice', v.id)
                    found_uk = True
                    break
            
            # Якщо української немає, а ми в UA-системі — David (0) або Zira (1) за замовчуванням
            if not found_uk and len(voices) > 1:
                # На Windows index 1 часто жіночий голос, який звучить м'якше
                engine.setProperty('voice', voices[1].id)

        engine.say(text)
        engine.runAndWait()
        engine.stop()
        
        return f"Vocal confirmation: '{text}'"
    except Exception as e:
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

