"""
skills/voice_output.py
Модуль для генерації голосових повідомлень через OpenAI TTS.
Використовує OpenAI Text-to-Speech API (Model tts-1).
"""

from openai import OpenAI
import os
import sys
from pathlib import Path
from typing import Optional
import tempfile

# Додаємо батьківську директорію для імпорту config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

# Ініціалізація клієнта
# Переконайтеся, що ключ є в config.py
try:
    if config.OPENAI_API_KEY:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        HAS_OPENAI_TTS = True
    else:
        client = None
        HAS_OPENAI_TTS = False
        print("⚠️ [TTS] OpenAI API Key не знайдено в config.py")
except Exception as e:
    client = None
    HAS_OPENAI_TTS = False
    print(f"⚠️ [TTS] Помилка ініціалізації OpenAI: {e}")

# Директорія для збереження аудіо файлів
# Використовуємо централізований шлях з config
AUDIO_DIR = config.AUDIO_OUTPUT_DIR
AUDIO_DIR.mkdir(exist_ok=True, parents=True)

# Голос за замовчуванням — з config (OPENAI_TTS_VOICE)
VOICE = getattr(config, "OPENAI_TTS_VOICE", "onyx")


def text_to_speech_file(text: str, voice: str = None) -> Optional[str]:
    """
    Генерує аудіо через OpenAI TTS (Model tts-1).
    
    Args:
        text: Текст для озвучування
        voice: Назва голосу (alloy, echo, fable, onyx, nova, shimmer); якщо None — з config.OPENAI_TTS_VOICE
        
    Returns:
        Шлях до згенерованого файлу або None при помилці
    """
    if not HAS_OPENAI_TTS or not client:
        print("[TTS] OpenAI API Key не знайдено.")
        return None

    if not text or not text.strip():
        return None

    try:
        print(f"[TTS] Генерую голос для: {text[:30]}...")
        
        # Створюємо унікальне ім'я файлу
        safe_name = "".join(c for c in text[:20] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')[:20] if safe_name else "response"
        output_file = AUDIO_DIR / f"{safe_name}_{os.getpid()}.mp3"
        
        # Генеруємо аудіо через OpenAI TTS (використовуємо модель та голос з config)
        # Джарвіс має низький, розмірений, впевнений голос
        try:
            response = client.audio.speech.create(
                model=config.OPENAI_TTS_MODEL,  # Модель з config
                voice=voice or getattr(config, "OPENAI_TTS_VOICE", "onyx"),
                input=text,
                speed=0.9  # Повільніша мова для більш розміреної та впевненої мови (як у Джарвіса)
            )
        except Exception as speed_error:
            # Якщо параметр speed не підтримується, використовуємо без нього
            print(f"[TTS] Параметр speed не підтримується, використовую стандартну швидкість")
            response = client.audio.speech.create(
                model=config.OPENAI_TTS_MODEL,
                voice=voice or getattr(config, "OPENAI_TTS_VOICE", "onyx"),
                input=text
            )
        
        # Зберігаємо файл
        response.stream_to_file(str(output_file))
        
        if os.path.exists(output_file):
            print(f"[TTS] Аудіо згенеровано: {output_file}")
            return str(output_file)
        else:
            print(f"⚠️ [TTS] Файл не створено: {output_file}")
            return None

    except Exception as e:
        print(f"[TTS] Помилка OpenAI TTS: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_available_voices() -> list:
    """
    Повертає список доступних голосів OpenAI TTS.
    
    Returns:
        Список доступних голосів
    """
    return ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]


# Функція для тестування
if __name__ == "__main__":
    print("[TTS] Тестування OpenAI TTS...")
    
    # Тестовий текст
    test_text = "Привіт, я Атлас. Готовий до роботи."
    
    print(f"[TTS] Текст: {test_text}")
    print(f"[TTS] Голос: {VOICE}")
    print("[TTS] Генерую аудіо...")
    
    result = text_to_speech_file(test_text)
    
    if result:
        print(f"[TTS] Аудіо згенеровано: {result}")
        print(f"[TTS] Розмір файлу: {os.path.getsize(result) / 1024:.2f} KB")
    else:
        print("[TTS] Не вдалося згенерувати аудіо")
    
    # Список доступних голосів
    print("\n[TTS] Доступні голоси OpenAI TTS:")
    voices = get_available_voices()
    for voice in voices:
        gender = "чоловічий" if voice in ["onyx", "echo", "fable"] else "жіночий" if voice in ["shimmer", "nova"] else "нейтральний"
        print(f"  - {voice} ({gender})")
