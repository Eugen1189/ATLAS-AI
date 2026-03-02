import os
import flet as ft
import datetime
import random
import threading
import time
import asyncio

# --- DPI AWARENESS ---
os.environ["QT_FONT_DPI"] = "96"

# --- ГЛОБАЛЬНІ ЗМІННІ ---
atlas = None
telegram_bridge = None
scheduler = None

def get_dynamic_greeting():
    """Генерує привітання на основі часу доби"""
    hour = datetime.datetime.now().hour
    
    # Визначаємо час доби
    if 5 <= hour < 12:
        time_part = "Доброго ранку"
    elif 12 <= hour < 18:
        time_part = "Добрий день"
    else:
        time_part = "Добрий вечір"
    
    # Варіативні фрази для "людяності"
    phrases = [
        "Радий вас бачити. Системи готові до роботи.",
        "Сподіваюсь, ви гарно відпочили. Починаємо?",
        "На зв'язку. Чекаю ваших вказівок.",
        "Сьогодні чудовий час для нових досягнень."
    ]
    
    # Збираємо все разом
    return f"{time_part}, Сер. {random.choice(phrases)}"

def main(page: ft.Page):
    global atlas, telegram_bridge
    
    page.title = "SystemCOO - Jarvis"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.bgcolor = "#1a1a1a"  # Темний фон
    
    # Налаштування для режиму "Фантом" (трей)
    page.window.minimizable = True
    page.window.skip_task_bar = False  # Показуємо в таскбарі, але можемо згорнути в трей

    # --- ВІЗУАЛ ПЕРСОНАЖА ---
    avatar_image = ft.Image(
        src="",  # assets видалено 
        width=400,
        height=400,
        fit=ft.ImageFit.CONTAIN,
        border_radius=ft.border_radius.all(20),
        opacity=1.0,
        visible=False  # Приховано за замовчуванням, якщо немає файлу
    )
    
    avatar_icon = ft.Icon(ft.Icons.SMART_TOY, size=150, color=ft.Colors.CYAN)
    
    avatar_container = ft.Container(
        content=ft.Stack([avatar_icon, avatar_image]),
        alignment=ft.alignment.center
    )

    status_text = ft.Text("System Offline", color="grey", size=20)
    
    # Futuristic Indicator Badge
    indicator_text = ft.Text("STANDBY", size=10, color=ft.Colors.CYAN_200, weight=ft.FontWeight.BOLD)
    indicator_badge = ft.Container(
        content=indicator_text,
        bgcolor=ft.Colors.BLACK54,
        border=ft.border.all(1, ft.Colors.CYAN_700),
        border_radius=5,
        padding=5,
        visible=False
    )
    
    # Використовуємо Text з можливістю вибору тексту для копіювання та вирівнюванням зліва
    chat_text = ft.Text("", color="white", size=14, width=600, text_align=ft.TextAlign.LEFT, selectable=True)

    # Функція зміни стану (анімація)
    def set_state(state):
        if state == "speaking":
            avatar_image.src = ""  # assets видалено
            avatar_image.opacity = 1.0
            avatar_icon.color = ft.Colors.CYAN_400
        elif state == "listening":
            avatar_image.opacity = 0.8
            avatar_icon.color = ft.Colors.RED_400
        elif state == "thinking":
            avatar_icon.color = ft.Colors.AMBER_400
        else:  # idle
            avatar_image.src = ""  # assets видалено
            avatar_image.opacity = 0.9
            avatar_icon.color = ft.Colors.CYAN
        page.update()

    # Callback для оновлення UI з AtlasCore
    def update_ui(update_type, data):
        if update_type == "status":
            text = data.get("text", "Idle")
            status_text.value = text
            status_text.color = data.get("color", "grey")
            
            # Vision / Voice Indicator Logic
            gestures = ["Cursor", "Click", "Zoom", "Drag", "Listening", "Thinking"]
            if any(g in text for g in gestures):
                indicator_badge.visible = True
                indicator_text.value = text.upper()
                if "Listening" in text:
                    indicator_badge.border = ft.border.all(1, ft.Colors.RED_400)
                    indicator_text.color = ft.Colors.RED_200
                elif "Thinking" in text:
                    indicator_badge.border = ft.border.all(1, ft.Colors.AMBER_400)
                    indicator_text.color = ft.Colors.AMBER_200
                else: # Gestures
                     indicator_badge.border = ft.border.all(1, ft.Colors.CYAN_400)
                     indicator_text.color = ft.Colors.CYAN_200
            else:
                indicator_badge.visible = False
            
            page.update()
        elif update_type == "chat":
            text = data.get("text", "")
            is_user = data.get("is_user", False)
            # Додаємо текст до існуючого (для історії повідомлень)
            if chat_text.value and chat_text.value.strip():
                chat_text.value += "\n\n"
            if is_user:
                chat_text.value += f"👤 Ви: {text}"
            else:
                chat_text.value += f"🤖 Атлас: {text}"
            chat_text.color = ft.Colors.WHITE
            page.update()
    
    # Callback для візуальних ефектів
    def update_visual(state):
        set_state(state)
    
    # Ініціалізація AtlasCore та Telegram Bridge
    def init_atlas():
        global atlas, telegram_bridge
        try:
            # atlas is now initialized in main thread, we just need to set up callbacks
            print("🏗️ [GUI] Configuring AtlasCore callbacks...")
            if atlas is None:
                from core.atlas import AtlasCore
                atlas = AtlasCore()
            
            # Встановлюємо callbacks
            atlas.set_ui_callback(update_ui)
            atlas.set_visual_callback(update_visual)
            
            # Запускаємо систему
            atlas.start()
            
            print("✅ [GUI] AtlasCore запущено")
            
            # Ініціалізація Telegram Bridge
            try:
                from skills.telegram_bridge import TelegramBridge
                import config
                
                if config.TELEGRAM_BOT_TOKEN:
                    print("🌉 [GUI] Ініціалізація Telegram Bridge...")
                    telegram_bridge = TelegramBridge(atlas_core=atlas)
                    telegram_bridge.start()
                    print("✅ [GUI] Telegram Bridge запущено")
                else:
                    print("⚠️ [GUI] Telegram токен не налаштовано. Bridge не запущено.")
            except ImportError as e:
                print(f"⚠️ [GUI] Telegram Bridge не доступний: {e}")
                telegram_bridge = None
            except Exception as e:
                print(f"⚠️ [GUI] Помилка ініціалізації Telegram Bridge: {e}")
                telegram_bridge = None
            
            # Ініціалізація Scheduler (Ранковий Протокол)
            try:
                from skills.scheduler_module import MorningBriefingScheduler
                import config
                
                print("📅 [GUI] Ініціалізація Scheduler...")
                global scheduler
                scheduler = MorningBriefingScheduler(
                    telegram_bridge=telegram_bridge,
                    atlas_core=atlas
                )
                
                # Запускаємо scheduler з часом ранкового зведення (за замовчуванням 09:00)
                briefing_time = getattr(config, 'BRIEFING_TIME', '09:00')
                scheduler.start(briefing_time=briefing_time)
                print(f"✅ [GUI] Scheduler запущено. Ранкове зведення о {briefing_time}")
                
                # Опціонально: надіслати зведення при старті (для тестування)
                # scheduler.send_briefing_now()
                
            except ImportError as e:
                print(f"⚠️ [GUI] Scheduler не доступний: {e}")
                scheduler = None
            except Exception as e:
                print(f"⚠️ [GUI] Помилка ініціалізації Scheduler: {e}")
                scheduler = None
            
            # Привітання (без TTS - тільки в GUI)
            welcome_text = get_dynamic_greeting()
            chat_text.value = welcome_text
            page.update()
            
            # Speak Welcome
            if atlas.voice_output:
                atlas.voice_output.speak(welcome_text)
            
            # Оновлюємо статус
            status_text.value = "🟢 Система активна. Скажіть 'Атлас' для активації"
            status_text.color = ft.Colors.GREEN
            page.update()
            
        except Exception as e:
            print(f"❌ [GUI] Помилка ініціалізації AtlasCore: {e}")
            import traceback
            traceback.print_exc()
            status_text.value = f"❌ Помилка: {str(e)}"
            status_text.color = ft.Colors.RED
            page.update()

    # Кнопка для ручного введення команди
    command_input = ft.TextField(
        label="Команда",
        hint_text="Введіть команду або натисніть 'Слухати'",
        width=400,
        on_submit=lambda e: process_command(e.control.value)
    )
    
    def process_command(cmd):
        if cmd and atlas:
            command_input.value = ""
            page.update()
            atlas.process_text_command(cmd)
    
    def manual_listen():
        """Trigger voice listening manually"""
        if atlas and atlas.voice_control:
             print("🎤 [GUI] Manual Listen Triggered")
             status_text.value = "Listening..."
             status_text.color = ft.Colors.RED_400
             page.update()
             # Run in thread to not block UI
             threading.Thread(target=atlas.voice_control._on_wake).start()
        else:
             print("⚠️ [GUI] Voice Control not available")
             status_text.value = "Voice Control Unavailable"
             status_text.color = ft.Colors.RED
             page.update()

    listen_button = ft.Button(
        "🎤 Слухати",
        on_click=lambda e: manual_listen(),
        bgcolor=ft.Colors.RED_400,
        color=ft.Colors.WHITE,
        width=150,
        height=40
    )
    
    # Змінна для стану wake word
    wake_word_enabled = True
    
    # Vision Control Button
    def toggle_vision():
        if atlas and atlas.vision_manager:
            if atlas.vision_manager.is_running:
                 atlas.vision_manager.stop()
                 vision_button.text = "👁️ Start Vision"
                 vision_button.bgcolor = ft.Colors.BLUE_GREY_700
                 status_text.value = "Vision Stopped"
            else:
                 try:
                     # Start in thread to avoid blocking UI
                     threading.Thread(target=atlas.vision_manager.start).start()
                     vision_button.text = "👁️ Stop Vision"
                     vision_button.bgcolor = ft.Colors.BLUE_400
                     status_text.value = "Vision Active"
                 except Exception as e:
                     status_text.value = f"Error: {e}"
            page.update()
        else:
             status_text.value = "Vision Module Unavailable"
             page.update()

    vision_button = ft.Button(
        "👁️ Start Vision",
        on_click=lambda e: toggle_vision(),
        bgcolor=ft.Colors.BLUE_GREY_700,
        color=ft.Colors.WHITE,
        width=150,
        height=40
    )

    # Контейнер для чату з рамкою та прокруткою
    chat_container = ft.Container(
        content=ft.Column(
            [chat_text],
            scroll=ft.ScrollMode.AUTO,
            height=200,
        ),
        width=600,
        padding=10,
        border=ft.border.all(1, ft.Colors.GREY_700),
        border_radius=10,
        bgcolor=ft.Colors.BLACK26,
    )
    
    # Додаємо елементи на сторінку
    page.add(
        avatar_container,
        ft.Container(height=20),
        status_text,
        ft.Container(height=20),
        indicator_badge,
        ft.Container(height=10),
        chat_container,
        ft.Container(height=20),
        ft.Row([
            command_input,
            listen_button,
            vision_button
        ], alignment=ft.MainAxisAlignment.CENTER),
        ft.Container(height=20),
        ft.Text(
            "💡 Підказка: Введіть команду в текстове поле та натисніть Enter",
            color=ft.Colors.GREY_400,
            size=12
        )
    )

    # --- ЗАПУСК ---
    def on_start():
        # 1. Привітання (без озвучки поки що - чекаємо на AtlasCore)
        welcome_text = get_dynamic_greeting()
        status_text.value = f"🗣️ {welcome_text}"
        set_state("speaking")
        page.update()
        
        # 2. Ініціалізуємо AtlasCore в окремому потоці (callbacks only)
        # Привітання буде озвучено через AtlasCore після ініціалізації
        threading.Thread(target=init_atlas, daemon=True).start()

    # Запускаємо привітання в окремому потоці після рендеру сторінки
    threading.Thread(target=on_start, daemon=True).start()
    
    # Ініціалізація трею (режим "Фантом")
    tray_manager = None
    try:
        from skills.tray_manager import TrayManager
        
        def show_window():
            """Показує вікно з трею"""
            page.window.visible = True
            page.window.focused = True
            page.update()
        
        def quit_app():
            """Вихід з додатку"""
            # Зупиняємо Scheduler
            global scheduler
            if scheduler:
                print("[GUI] Зупиняємо Scheduler...")
                try:
                    scheduler.stop()
                except Exception as e:
                    print(f"[GUI] Помилка зупинки Scheduler: {e}")
            
            # Зупиняємо Telegram Bridge
            if telegram_bridge:
                print("[GUI] Зупиняємо Telegram Bridge...")
                try:
                    telegram_bridge.stop()
                except Exception as e:
                    print(f"[GUI] Помилка зупинки Telegram Bridge: {e}")
            
            # Зупиняємо AtlasCore
            if atlas:
                if hasattr(atlas, 'system_observer'):
                    print("[GUI] Зупиняємо System Observer...")
                    atlas.system_observer.stop()
                if hasattr(atlas, 'stop'):
                    print("[GUI] Зупиняємо AtlasCore...")
                    atlas.stop()
            page.window.close()
        
        tray_manager = TrayManager(on_show=show_window, on_quit=quit_app)
        tray_manager.start()
        print("[GUI] Режим 'Фантом' активовано - додаток можна згорнути в трей")
    except Exception as e:
        print(f"[GUI] Помилка ініціалізації трею: {e}")
        tray_manager = None
    
    # Cleanup при закритті вікна
    def on_window_event(e):
        if e.data == "close":
            # Якщо трей активний - ховаємо вікно замість закриття
            if tray_manager and tray_manager.is_running:
                print("[GUI] Згортаємо в трей (режим 'Фантом')")
                page.window.visible = False
                page.update()
                # Показуємо сповіщення
                if tray_manager:
                    tray_manager.notify("ATLAS", "Додаток згорнуто в трей. Клацніть на іконку для відкриття.")
                return
            
            # Якщо трей не активний - закриваємо нормально
            # Зупиняємо Scheduler
            global scheduler
            if scheduler:
                print("[GUI] Зупиняємо Scheduler...")
                try:
                    scheduler.stop()
                except Exception as e:
                    print(f"[GUI] Помилка зупинки Scheduler: {e}")
            
            # Зупиняємо Telegram Bridge
            if telegram_bridge:
                print("[GUI] Зупиняємо Telegram Bridge...")
                try:
                    telegram_bridge.stop()
                except Exception as e:
                    print(f"[GUI] Помилка зупинки Telegram Bridge: {e}")
            
            if atlas and hasattr(atlas, 'system_observer'):
                print("[GUI] Зупиняємо System Observer...")
                atlas.system_observer.stop()
            if atlas and hasattr(atlas, 'stop'):
                print("[GUI] Зупиняємо AtlasCore...")
                atlas.stop()
            if tray_manager:
                tray_manager.stop()
    
    page.on_window_event = on_window_event

if __name__ == "__main__":
    import sys
    import asyncio
    from PyQt6.QtWidgets import QApplication
    from core.hud_manager import AtlasHUD
    from core.atlas import AtlasCore
    
    print("🚀 [BOOT] Starting SYSTEM HUD and Core...")
    
    # 1. Create Qt App in Main Thread
    qt_app = QApplication(sys.argv)
    
    # 2. Create HUD
    hud = AtlasHUD()
    
    # 3. Create Core & Attach HUD
    atlas = AtlasCore()
    atlas.attach_hud(hud)
    
    # 4. Start Flet in a Background Thread
    def run_flet():
        import signal
        # Patch signal.signal to avoid "ValueError: signal only works in main thread"
        # This is required because Flet (and asyncio) try to set signal handlers
        _original_signal = signal.signal
        def safe_signal(sig, handler):
            try:
                return _original_signal(sig, handler)
            except ValueError:
                return None # Ignore signal errors in threads
        signal.signal = safe_signal

        time.sleep(1.2) # Give HUD time to show
        print("🌐 [GUI] Starting Flet Interface...")
        ft.app(target=main)
    
    flet_thread = threading.Thread(target=run_flet, daemon=True)
    flet_thread.start()
    
    # 5. Block Main Thread with Qt Loop (Essential for transparent HUD)
    print("💎 [GUI] HUD Event Loop Started.")
    sys.exit(qt_app.exec())
