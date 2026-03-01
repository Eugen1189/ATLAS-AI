import speech_recognition as sr

def listen_command() -> str:
    """
    Слухає мікрофон і перетворює голос на текст.
    Це не інструмент для LLM, це функція для main.py.
    """
    recognizer = sr.Recognizer()
    
    with sr.Microphone() as source:
        print("\n🎤 [Audio Interface]: Калібрую фоновий шум (1 сек)...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        
        print("🟢 [Audio Interface]: Говори! Я тебе слухаю...")
        try:
            # Чекаємо максимум 5 секунд на початок фрази, і максимум 15 секунд на саму фразу
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
            
            print("⏳ [Audio Interface]: Розпізнаю текст...")
            # Використовуємо Google Speech Recognition (можна вказати 'uk-UA' або 'en-US')
            text = recognizer.recognize_google(audio, language="uk-UA")
            
            return text
            
        except sr.WaitTimeoutError:
            print("⚠️ [Audio Interface]: Тиша. Переходжу в режим очікування.")
            return ""
        except sr.UnknownValueError:
            print("⚠️ [Audio Interface]: Не зміг розпізнати слова. Повтори, будь ласка.")
            return ""
        except Exception as e:
            print(f"❌ [Audio Interface]: Системна помилка мікрофона: {e}")
            return ""