import os
import time
from openai import OpenAI
from dotenv import load_dotenv

# Динамічно знаходимо шлях до .env (як ми це робили в Ядрі)
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.abspath(os.path.join(current_dir, "..", "..", ".env"))
load_dotenv(dotenv_path=env_path)

def speak(text: str) -> str:
    """
    Озвучує текст вголос через динаміки комп'ютера (OpenAI TTS).
    Використовуй цей інструмент, коли користувач просить тебе щось "сказати", "озвучити" або 
    коли ти хочеш повідомити користувачу щось важливе голосом.
    УВАГА: Не передавай сюди довгі тексти або код, лише короткі, природні розмовні фрази.
    
    Args:
        text: Текст, який потрібно сказати вголос (бажано до 2-3 речень).
    """
    print(f"🗣️ [Audio Interface]: Озвучую: '{text}'")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "Помилка: OPENAI_API_KEY не знайдено в .env файлі."
        
    try:
        client = OpenAI(api_key=api_key)
        
        # Створюємо папку для аудіо-пам'яті
        output_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "memories", "audio"))
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, f"speech_{int(time.time())}.mp3")
        
        # Генеруємо аудіо (Голос 'onyx' - Джарвіс)
        response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=text,
            speed=0.9
        )
        response.stream_to_file(file_path)
        
        # Відтворення аудіо у фоні
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            # Чекаємо, поки файл не дограє до кінця
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
            pygame.mixer.quit()
        except ImportError:
            # Запасний варіант, якщо pygame не встановлено
            os.system(f'start /min "" "{file_path}"')
            
        return "Текст успішно озвучено."
        
    except Exception as e:
        return f"Помилка генерації або відтворення голосу: {e}"

# Експортуємо інструмент
EXPORTED_TOOLS = [speak]