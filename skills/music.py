import os
import sys
from pathlib import Path

# Додаємо батьківську директорію для імпорту config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
MUSIC_DIR = str(config.MUSIC_DIR)

# Глобальний AudioManager (буде встановлений ззовні)
_audio_manager = None

def set_audio_manager(audio_manager):
    """Встановлює глобальний AudioManager для використання."""
    global _audio_manager
    _audio_manager = audio_manager

def play_music():
    """Запускає випадковий трек з папки music"""
    try:
        # Використовуємо AudioManager виключно
        if not _audio_manager:
            return "⚠️ AudioManager не ініціалізовано. Музика не може працювати."
        
        return _audio_manager.play_music(volume=0.3)
    except Exception as e:
        return f"Помилка аудіосистеми: {e}"

def stop_music():
    """Зупиняє відтворення музики"""
    if _audio_manager:
        _audio_manager.stop_music()
    else:
        print("⚠️ [MUSIC] AudioManager не ініціалізовано. Неможливо зупинити музику.")



