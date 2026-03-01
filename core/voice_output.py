import os
import time
import threading
import queue
import sys
from pathlib import Path

# Add root for config import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

try:
    from openai import OpenAI
    client = OpenAI(api_key=config.GOOGLE_API_KEY if "AIza" not in config.GOOGLE_API_KEY else config.OPENAI_API_KEY)
    # Note: Using OPENAI_API_KEY as primary for OpenAI services
    if not config.OPENAI_API_KEY:
        print("⚠️ [TTS] OpenAI API Key not found in config.py")
        HAS_OPENAI = False
    else:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("⚠️ [TTS] openai library not installed.")

try:
    import pygame
    pygame.mixer.init()
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False
    print("⚠️ [TTS] pygame not installed. Cannot play audio.")

class VoiceOutput:
    """
    Cloud Voice Output: OpenAI TTS (tts-1). Premium quality, no local DLLs.
    """
    def __init__(self):
        print("🔊 [TTS] Initializing cloud voice output (OpenAI)...")
        self.msg_queue = queue.Queue()
        self.is_playing = False
        self.voice = getattr(config, "OPENAI_TTS_VOICE", "onyx")
        self.model = getattr(config, "OPENAI_TTS_MODEL", "tts-1")
        
        if HAS_OPENAI and HAS_PYGAME:
            print(f"✅ [TTS] OpenAI Cloud Voice activated (Voice: {self.voice}).")
            threading.Thread(target=self._worker, daemon=True).start()
        else:
            status = "Missing OpenAI Key" if not HAS_OPENAI else "Missing Pygame"
            print(f"❌ [TTS] Cloud Voice disabled: {status}")

    def set_mode(self, mode):
        """Supported for API compatibility, but OpenAI voices are already high quality."""
        pass

    def speak(self, text):
        """Adds text to the speech queue."""
        if text and HAS_OPENAI:
            # Clean text (remove markdown symbols that sound weird)
            clean_text = text.replace("*", "").replace("#", "").replace("`", "")
            self.msg_queue.put(clean_text)

    def _worker(self):
        """Consumer thread for speech queue."""
        while True:
            text = self.msg_queue.get()
            if text is None: break
            
            try:
                self.is_playing = True
                
                # 1. Generate Audio via API
                temp_file = Path(config.AUDIO_OUTPUT_DIR) / f"tts_{int(time.time())}.mp3"
                temp_file.parent.mkdir(exist_ok=True, parents=True)
                
                response = client.audio.speech.create(
                    model=self.model,
                    voice=self.voice,
                    input=text,
                    speed=1.0
                )
                
                # 2. Save Stream
                response.stream_to_file(str(temp_file))
                
                # 3. Play via Pygame
                if HAS_PYGAME:
                    pygame.mixer.music.load(str(temp_file))
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                
                # 4. Cleanup
                try:
                    # Delay cleanup slightly to avoid file access errors
                    threading.Timer(2.0, lambda: os.remove(str(temp_file)) if temp_file.exists() else None).start()
                except: pass

            except Exception as e:
                print(f"❌ [TTS] OpenAI Error: {e}")
            finally:
                self.is_playing = False
                self.msg_queue.task_done()

# For testing
if __name__ == "__main__":
    tts = VoiceOutput()
    tts.speak("Привіт! Я Атлас, твоя хмарна операційна система. Тепер я звучу набагато краще.")
    time.sleep(10)
