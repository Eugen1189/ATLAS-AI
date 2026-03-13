import os
import requests

from core.skills.wrapper import agent_tool
from .processor import speak as _core_speak, transcribe_audio

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
    Можна вказати voice_index (ціле число) або speed (множник, за замовчуванням 1.0).
    """
    speed_factor = kwargs.get("speed", 1.0)
    voice_idx = kwargs.get("voice_index")
    # Call core processing logic
    result = _core_speak(text, speed_factor=speed_factor, voice_idx=voice_idx)
    return f"Vocal response: '{text[:100]}...'" if "Error" not in result else result

@agent_tool
def listen_for_voice(**kwargs) -> str:
    """Standard 2026 Microphone Input (Voice-to-Text)."""
    from .listener import listen_command
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

# --- Internal bridges for Telegram/API ---
def transcribe_audio_file(file_path: str) -> str:
    """Non-tool function for other modules to transcribe saved files."""
    return transcribe_audio(file_path)

def respond_with_voice(text: str, chat_id: str, bot_token: str) -> tuple[bool, str]:
    """
    Acts as a 'Vocal Response' for remote users. (v2.9.7: Returns (success, error_msg))
    """
    from .processor import generate_voice_file
    path = generate_voice_file(text)
    if not path or not os.path.exists(path): 
        return False, "Failed to generate .ogg file via TTS/FFmpeg."
    
    url = f"https://api.telegram.org/bot{bot_token}/sendVoice"
    try:
        with open(path, 'rb') as f:
            r = requests.post(url, data={'chat_id': chat_id}, files={'voice': f}, timeout=30)
            if r.status_code == 200:
                success = True
                err = ""
            else:
                success = False
                err = f"Telegram API Error {r.status_code}: {r.text}"
        
        # Cleanup
        if os.path.exists(path): os.remove(path)
        return success, err
    except Exception as e: 
        return False, str(e)

EXPORTED_TOOLS = [speak, listen_for_voice, voice_alert]
