"""
skills/telegram_bridge.py
Міст між Telegram та ядром ATLAS.
Дозволяє керувати системою через чат та голосові повідомлення.
ВЕРСІЯ: Асинхронна (AsyncTeleBot)
"""
import asyncio
import threading
import time
import sys
import os
import tempfile
import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Додаємо батьківську директорію для імпортів
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config

# Спроба імпорту OpenAI для Whisper
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    OpenAI = None

# Спроба імпорту Google Generative AI для Vision
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False
    genai = None

# Спроба імпорту pyTelegramBotAPI (Async версія)
try:
    from telebot.async_telebot import AsyncTeleBot
    from telebot import types
    HAS_TELEBOT = True
except ImportError:
    HAS_TELEBOT = False

# Спроба імпорту голосового виходу
try:
    from skills.voice_output import text_to_speech_file
    HAS_VOICE_OUTPUT = True
except ImportError:
    HAS_VOICE_OUTPUT = False
    print("⚠️ [TELEGRAM] Голосовий вихід не доступний")


class TelegramBridge:
    """
    Асинхронний міст між Telegram та ядром ATLAS.
    """
    
    def __init__(self, atlas_core):
        if not HAS_TELEBOT:
            raise ImportError("pyTelegramBotAPI не встановлено")
        
        self.atlas = atlas_core
        self.bot = None
        self.is_running = False
        self.executor = ThreadPoolExecutor(max_workers=10) # Для синхронних викликів Brain
        self.loop = None
        
        # Ініціалізація клієнтів
        self.openai_client = None
        if HAS_OPENAI and config.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
        
        if HAS_GEMINI and config.GOOGLE_API_KEY:
            genai.configure(api_key=config.GOOGLE_API_KEY)
            model_name = getattr(config, "GEMINI_VISION_MODEL", "gemini-1.5-flash")
            self.gemini_model = genai.GenerativeModel(model_name)
        
        if config.TELEGRAM_BOT_TOKEN:
            self.bot = AsyncTeleBot(config.TELEGRAM_BOT_TOKEN)
            self._register_handlers()
            self.is_running = True

    def _register_handlers(self):
        """Реєстрація асинхронних обробників"""
        
        @self.bot.message_handler(commands=['start'])
        async def send_welcome(message):
            if not self._check_auth(message): return
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("Статус системи", "Зроби скріншот")
            markup.add("Скануй систему", "Що на екрані?")
            markup.add("Які дедлайни?", "Нагадування")
            await self.bot.reply_to(message, "👋 ATLAS активний. Чекаю вказівок.", reply_markup=markup)

        @self.bot.message_handler(commands=['status'])
        async def send_status(message):
            if not self._check_auth(message): return
            await self.bot.send_chat_action(message.chat.id, 'typing')
            response = await self._run_sync(self._process_command_sync, "Атлас, статус системи")
            await self.bot.reply_to(message, f"📊 Статус:\n{response}")

        @self.bot.message_handler(content_types=['voice'])
        async def handle_voice(message):
            if not self._check_auth(message): return
            await self.bot.send_chat_action(message.chat.id, 'typing')
            
            # Асинхронне розпізнавання
            transcribed_text = await self._run_sync(self._transcribe_voice_sync, message.voice.file_id)
            
            if transcribed_text:
                await self.bot.reply_to(message, f"🎤 Розпізнано: _{transcribed_text}_", parse_mode='Markdown')
                response = await self._run_sync(self._process_command_sync, transcribed_text)
                await self._send_response_with_voice(message, response)
            else:
                await self.bot.reply_to(message, "❌ Не вдалося розпізнати голос.")

        @self.bot.message_handler(func=lambda message: True)
        async def handle_text(message):
            if not self._check_auth(message): return
            user_text = message.text
            
            # Спеціальні обробники
            if any(kw in user_text.lower() for kw in ["скріншот", "скрін", "screenshot"]):
                await self._handle_screenshot_async(message)
                return
            
            if any(kw in user_text.lower() for kw in ["що на екрані", "проаналізуй екран"]):
                await self._handle_vision_async(message, user_text)
                return

            await self.bot.send_chat_action(message.chat.id, 'typing')
            # Важка операція в окремому потоці
            response = await self._run_sync(self._process_command_sync, user_text)
            await self._send_response_with_voice(message, response)

    async def _run_sync(self, func, *args):
        """Запускає синхронну функцію в ThreadPoolExecutor"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args)

    async def _send_response_with_voice(self, message, response):
        """Асинхронна відправка тексту та голосу (паралельно)"""
        # Спершу відправляємо текст (миттєво)
        await self.bot.reply_to(message, response[:4000]) # Обмеження Telegram
        
        # Якщо текст довгий, генеруємо голос у фоні
        if len(response) > 50 and HAS_VOICE_OUTPUT:
            async def generate_and_send():
                try:
                    audio_path = await self._run_sync(text_to_speech_file, response)
                    if audio_path and os.path.exists(audio_path):
                        with open(audio_path, 'rb') as f:
                            await self.bot.send_voice(message.chat.id, f)
                except Exception as e:
                    print(f"⚠️ [TTS] Помилка: {e}")
            
            # Запускаємо без очікування
            asyncio.create_task(generate_and_send())

    def _check_auth(self, message):
        user_id = message.from_user.id
        allowed = getattr(config, "ALLOWED_USER_IDS", [])
        if not allowed or user_id in allowed:
            return True
        print(f"⛔ [AUTH] Відмова доступу: {user_id}")
        return False

    def _process_command_sync(self, text):
        """Синхронна обробка через ядро (викликається через run_in_executor)"""
        if self.atlas and self.atlas.brain:
            return self.atlas.brain.think(text)
        return "⚠️ AtlasCore не готовий."

    def _transcribe_voice_sync(self, file_id):
        """Синхронне розпізнавання (викликається через run_in_executor)"""
        if not self.openai_client: return None
        try:
            # Отримання файлу через асинхронний метод, але downloader синхронний у telebot
            # Для простоти використовуємо блоки, які telebot надає
            file_info = asyncio.run_coroutine_threadsafe(self.bot.get_file(file_id), self.loop).result()
            downloaded = asyncio.run_coroutine_threadsafe(self.bot.download_file(file_info.file_path), self.loop).result()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as tmp:
                tmp.write(downloaded)
                tmp_path = tmp.name
            
            try:
                with open(tmp_path, 'rb') as f:
                    transcript = self.openai_client.audio.transcriptions.create(
                        model=config.OPENAI_WHISPER_MODEL,
                        file=f, language="uk"
                    )
                return transcript.text
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            print(f"❌ [VOICE] {e}")
            return None

    async def _handle_screenshot_async(self, message):
        await self.bot.send_chat_action(message.chat.id, 'upload_photo')
        path = await self._run_sync(self._take_screenshot_sync)
        if path:
            with open(path, 'rb') as f:
                await self.bot.send_photo(message.chat.id, f, caption="📸 Скріншот готовий")
        else:
            await self.bot.reply_to(message, "❌ Не вдалося зробити скріншот")

    async def _handle_vision_async(self, message, query):
        await self.bot.send_chat_action(message.chat.id, 'upload_photo')
        path = await self._run_sync(self._take_screenshot_sync)
        if not path:
            await self.bot.reply_to(message, "❌ Помилка камери/екрана")
            return
            
        await self.bot.send_chat_action(message.chat.id, 'typing')
        analysis = await self._run_sync(self._analyze_sync, path, query)
        
        with open(path, 'rb') as f:
            await self.bot.send_photo(message.chat.id, f, caption=f"👁️ Аналіз:\n{analysis[:1000]}")

    def _take_screenshot_sync(self):
        import pyautogui
        path = config.SCREENSHOTS_DIR / f"tg_{int(time.time())}.png"
        path.parent.mkdir(exist_ok=True)
        pyautogui.screenshot().save(path)
        return str(path)

    def _analyze_sync(self, path, query):
        if not HAS_GEMINI or not self.gemini_model: return "Vision недоступний"
        import PIL.Image
        img = PIL.Image.open(path)
        res = self.gemini_model.generate_content([f"Проаналізуй скріншот за запитом: {query}", img])
        return res.text

    def start(self):
        """Запуск асинхронного циклу в окремому потоці"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            print("🚀 [TELEGRAM] Асинхронний Polling запущено")
            self.loop.run_until_complete(self.bot.polling(non_stop=True))
        
        threading.Thread(target=run_loop, daemon=True).start()

    def stop(self):
        self.is_running = False
        if self.bot:
            # Асинхронна зупинка складніша з іншого потоку, 
            # але TeleBot зазвичай просто вбивається потоком
            pass
