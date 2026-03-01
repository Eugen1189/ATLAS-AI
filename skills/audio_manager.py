"""
AudioManager - централізоване управління аудіо для ATLAS.

Використовує окремі канали pygame.mixer для TTS та музики,
щоб дозволити одночасне відтворення без конфліктів.
"""

import pygame
import os
import random

# Імпортуємо config для використання централізованих шляхів
import config
DEFAULT_MUSIC_DIR = str(config.MUSIC_DIR)


class AudioManager:
    """
    Централізований менеджер аудіо для ATLAS.
    
    Використовує окремі канали для TTS та музики,
    що дозволяє одночасне відтворення без конфліктів.
    """
    
    def __init__(self, music_dir: str = None):
        """
        Ініціалізація AudioManager.
        
        Args:
            music_dir: Шлях до папки з музичними файлами (за замовчуванням з config.py)
        """
        if music_dir is None:
            music_dir = DEFAULT_MUSIC_DIR
        # Ініціалізація міксера (якщо ще не ініціалізовано)
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception as e:
                print(f"⚠️ [AUDIO] Помилка ініціалізації звуку: {e}")
        
        # Виділяємо окремі канали для TTS та музики
        self.tts_channel = pygame.mixer.Channel(0)
        self.music_channel = pygame.mixer.Channel(1)
        self.music_dir = music_dir
        
        print("✅ [AUDIO] AudioManager ініціалізовано")
    
    def play_tts(self, audio_file_path: str, volume: float = 1.0):
        """
        Відтворює TTS аудіо на окремому каналі.
        
        Args:
            audio_file_path: Шлях до аудіо файлу
            volume: Гучність (0.0 - 1.0)
        """
        try:
            # Зупиняємо попереднє відтворення TTS, якщо воно активне
            if self.tts_channel.get_busy():
                self.tts_channel.stop()
            
            # Завантажуємо та відтворюємо звук
            sound = pygame.mixer.Sound(audio_file_path)
            self.tts_channel.set_volume(volume)
            self.tts_channel.play(sound)
            
        except Exception as e:
            print(f"❌ [AUDIO] Помилка відтворення TTS: {e}")
    
    def wait_for_tts(self, timeout: float = 10.0):
        """
        Чекає, поки TTS закінчить відтворення.
        
        Args:
            timeout: Максимальний час очікування в секундах
        """
        import time
        start = time.time()
        while self.tts_channel.get_busy() and (time.time() - start) < timeout:
            pygame.time.Clock().tick(10)
    
    def play_music(self, volume: float = 0.3, track_path: str = None):
        """
        Відтворює музику на окремому каналі.
        
        Args:
            volume: Гучність (0.0 - 1.0)
            track_path: Шлях до конкретного треку (якщо None - випадковий)
            
        Returns:
            Повідомлення про відтворення або помилку
        """
        try:
            # Якщо не вказано конкретний трек, вибираємо випадковий
            if track_path is None:
                if not os.path.exists(self.music_dir):
                    os.makedirs(self.music_dir)
                    return "Папка з музикою порожня."
                
                files = [f for f in os.listdir(self.music_dir) if f.endswith('.mp3')]
                
                if not files:
                    return "Я не знайшов музичних файлів, сер."
                
                track = random.choice(files)
                track_path = os.path.join(self.music_dir, track)
            else:
                track = os.path.basename(track_path)
            
            # Зупиняємо попереднє відтворення музики, якщо воно активне
            if self.music_channel.get_busy():
                self.music_channel.stop()
            
            # Завантажуємо та відтворюємо звук
            sound = pygame.mixer.Sound(track_path)
            self.music_channel.set_volume(volume)
            self.music_channel.play(sound, loops=-1)  # -1 = безкінечне повторення
            
            return f"Грає: {track}"
            
        except Exception as e:
            return f"Помилка аудіосистеми: {e}"
    
    def stop_music(self, fadeout: int = 1000):
        """
        Зупиняє відтворення музики з плавним затуханням.
        
        Args:
            fadeout: Час затухання в мілісекундах
        """
        if self.music_channel.get_busy():
            self.music_channel.fadeout(fadeout)
    
    def stop_tts(self):
        """Зупиняє відтворення TTS."""
        if self.tts_channel.get_busy():
            self.tts_channel.stop()
    
    def is_music_playing(self) -> bool:
        """Перевіряє, чи відтворюється музика."""
        return self.music_channel.get_busy()
    
    def is_tts_playing(self) -> bool:
        """Перевіряє, чи відтворюється TTS."""
        return self.tts_channel.get_busy()
    
    def is_any_playing(self) -> bool:
        """Перевіряє, чи відтворюється будь-яке аудіо."""
        return self.is_music_playing() or self.is_tts_playing()
