import threading
import time
import os

# Core components
from skills.brain import Brain
from skills.command_queue import CommandQueue
from skills.task_manager import TaskManager
from skills.music import play_music, stop_music, set_audio_manager as set_music_audio_manager
from skills.audio_manager import AudioManager
# hud import removed - will be attached externally

# Subsystems
try:
    from agents.queue_manager import get_queue_manager
    HAS_QUEUE_MANAGER = True
except ImportError:
    HAS_QUEUE_MANAGER = False

try:
    from core.voice_output import VoiceOutput
    HAS_TTS = True
except ImportError:
    HAS_TTS = False

class AtlasCore:
    """
    ATLAS Core Kernel.
    Central coordinator for all subsystems: Voice, Brain, Execution, UI State.
    """
    
    def __init__(self):
        print("🏗️ [CORE] Initializing ATLAS Kernel...")
        
        # 0. Initialize AudioManager first (before other subsystems) - тільки для музики
        self.audio_manager = AudioManager()
        # Set AudioManager for music module
        set_music_audio_manager(self.audio_manager)
        
        # 1. Initialize Subsystems
        self.brain = Brain()
        self.command_queue = CommandQueue(processor=self.brain.think)
        
        # 2. State
        self.is_listening = False
        self.status = "Initializing..."
        self.ui_callback = None # Function to update UI status/chat
        self.background_layer_callback = None # Function to control UI visuals
        
        # 2.5 HUD Reference (attached externally to avoid thread issues)
        self.hud_window = None
        
        # 3. Setup Inbox Watcher via Brain (без TTS)
        self.brain.set_inbox_callback(tts_callback=None)
        
        # 4. Setup System Observer (Heartbeat)
        from skills.system_observer import SystemObserver
        self.system_observer = SystemObserver(self)
        
        # 5. Initialize Voice Control (Optional)
        self.voice_control = None
        try:
            from core.voice_control import VoiceControl
            # Check if key is available before initializing
            if os.getenv("PICOVOICE_ACCESS_KEY"):
                self.voice_control = VoiceControl(
                    command_callback=self.process_text_command,
                    status_callback=self.set_visual
                )
            else:
                print("⚠️ [CORE] VoiceControl skipped: PICOVOICE_ACCESS_KEY not found.")
        except Exception as e:
             print(f"⚠️ [CORE] VoiceControl not available: {e}")
             self._voice_error = str(e)
        
        # 6. Initialize Vision Control (Optional)
        self.vision_manager = None
        try:
            from core.vision_manager import VisionManager
            import config
            router_callback = (lambda intent: self.brain.router.dispatch_vision_intent(intent)) if self.brain and getattr(self.brain, "router", None) else None
            self.vision_manager = VisionManager(
                camera_index=config.CAMERA_INDEX,
                ui_callback=self.update_status,
                router_callback=router_callback,
                hud_callback=self._update_hud_zone
            )
        except Exception as e:
            print(f"⚠️ [CORE] VisionManager not available: {e}")
            
        # 7. Initialize Voice Output (TTS)
        self.voice_output = None
        if HAS_TTS:
            try:
                self.voice_output = VoiceOutput()
            except Exception as e:
                print(f"⚠️ [CORE] VoiceOutput init failed: {e}")

        print("✅ [CORE] Kernel Initialized.")
    
    def start(self):
        """Starts all background threads and systems."""
        print("🚀 [CORE] Starting systems...")
        
        # Start Command Queue
        self.command_queue.start()
        
        # Start System Observer (Етап 5)
        self.system_observer.start()
        
        # Start Voice Control
        if self.voice_control:
            self.voice_control.start()
            
        self.update_status("Online. Voice: CLOUD (OpenAI)", "cyanAccent")
        
        print("✅ [CORE] Systems started")
    
    def stop(self):
        """Stops all background threads and systems."""
        print("🛑 [CORE] Stopping systems...")
        
        # Stop System Observer
        if hasattr(self.system_observer, 'stop'):
            self.system_observer.stop()
            
        # Stop Voice Control
        if self.voice_control:
            self.voice_control.stop()
            
        # Stop Vision Control
        if self.vision_manager:
            try:
                self.vision_manager.stop()
            except:
                pass
        
        # Stop Command Queue
        if hasattr(self.command_queue, 'stop'):
            self.command_queue.stop()
        
        # Stop music if playing
        try:
            stop_music()
        except:
            pass
        
        self.update_status("Offline")
        print("✅ [CORE] Systems stopped")

    def set_ui_callback(self, callback):
        """Sets the callback function to update UI (chat, status)."""
        self.ui_callback = callback
    
    def set_visual_callback(self, callback):
        """Sets callback for visual effects (border, opacity)."""
        self.background_layer_callback = callback

    def attach_hud(self, hud_instance):
        """Attaches externally created HUD to the core."""
        self.hud_window = hud_instance
        print("🖥️ [CORE] HUD attached.")

    def update_status(self, text, color="cyanAccent"):
        self.status = text
        if self.ui_callback:
            self.ui_callback("status", {"text": text, "color": color})
        
        # Update HUD
        if self.hud_window:
            color_map = {"cyanAccent": "#00FFFF", "red": "#FF5555", "greenAccent": "#55FF55", "purpleAccent": "#FF55FF"}
            hex_color = color_map.get(color, "#00FFFF")
            self.hud_window.signals.status_changed.emit(text, hex_color)

    def add_chat_message(self, text, is_user=False):
        if self.ui_callback:
            self.ui_callback("chat", {"text": text, "is_user": is_user})
        
        # Update HUD Log Stream (only bot messages for cleaner HUD)
        if self.hud_window and not is_user:
            # Clean up message for HUD (shorten if too long)
            clean_text = text.replace("\n", " ")[:40] + ("..." if len(text) > 40 else "")
            self.hud_window.signals.log_added.emit(clean_text)

    def set_visual(self, state):
        """
        state: 'idle', 'listening', 'thinking', 'speaking', 'error'
        """
        if self.background_layer_callback:
            self.background_layer_callback(state)
            
        # Update HUD Thinking State
        if self.hud_window:
            self.hud_window.signals.thinking_state_changed.emit(state == "thinking")

    def _update_hud_zone(self, zone_index, is_active, confidence=0.0):
        """Callback from VisionManager to update HUD zone visualizer and confidence."""
        if self.hud_window:
            self.hud_window.signals.zone_changed.emit(zone_index, is_active)
            self.hud_window.signals.confidence_changed.emit(confidence)

    def process_text_command(self, command: str):
        """Handles text input from UI."""
        if command:
            self.add_chat_message(command, is_user=True)
            self._process_command(command)

    def _process_command(self, command: str):
        """Internal command processor."""
        if not command: return

        command_lower = command.lower()


        self.update_status(f"Thinking: {command}...", "cyan")
        self.set_visual("thinking")
        
        # Dynamic Timeout Calculation
        timeout = 60.0
        if any(k in command_lower for k in ["аналіз", "код", "coder", "стаття", "пошук", "search", "web"]):
            timeout = 300.0
        
        # Visual Grounding Check
        image_context = None
        visual_keywords = ["що це", "what is this", "подивись", "бачиш", "look", "see", "аналіз", "камер"]
        if any(k in command_lower for k in visual_keywords):
             if self.vision_manager and self.vision_manager.is_running:
                 print("👁️ [CORE] Visual query detected. Capturing frame...")
                 image_context = self.vision_manager.get_latest_frame()
                 if image_context:
                     print("📸 [CORE] Frame captured for analysis.")
                     self.update_status("Analyzing Visuals...", "purpleAccent")
                 else:
                     print("⚠️ [CORE] Vision active but no frame available.")

        # Add to non-blocking queue
        self.command_queue.add_command(
            command,
            image=image_context,
            callback=self._on_command_result,
            timeout=timeout
        )

    def _on_command_result(self, response, error):
        """Callback from CommandQueue."""
        if error:
            print(f"❌ [CORE] Error: {error}")
            error_msg = f"Помилка: {error}"
            self.add_chat_message(error_msg, is_user=False)
            self.update_status(f"Error: {error}", "red")
            self.set_visual("error")
        elif response:
            # Check for INTERNAL commands
            if response.startswith("INTERNAL:"):
                cmd = response.split(":", 1)[1]
                if cmd == "vision:start":
                    if self.vision_manager:
                         try:
                             self.vision_manager.start()
                             self.add_chat_message("Зір активовано. Слідкую за жестами.", is_user=False)
                             self.update_status("Vision Active", "cyanAccent")
                         except Exception as e:
                             self.add_chat_message(f"Помилка запуску зору: {e}", is_user=False)
                    else:
                         self.add_chat_message("Vision Manager не знайдено.", is_user=False)
                elif cmd == "vision:stop":
                    if self.vision_manager:
                         try:
                             self.vision_manager.stop()
                             self.add_chat_message("Зір деактивовано.", is_user=False)
                             self.update_status("Idle", "cyanAccent")
                         except Exception as e:
                             self.add_chat_message(f"Помилка зупинки зору: {e}", is_user=False)
                    else:
                         self.add_chat_message("Vision Manager не знайдено.", is_user=False)
                return

            # Відображаємо результат в GUI
            print(f"✅ [CORE] Результат: {response[:100]}...")
            self.add_chat_message(response, is_user=False)
            self.update_status("Task Complete", "greenAccent")
            self.set_visual("idle")
            
            # Speak result
            if self.voice_output:
                # Apply Voice Filter based on Personality
                try:
                    focus_level = self.brain.personality.focus_level
                    if focus_level == "high":
                        self.voice_output.set_mode("focus")
                    else:
                        self.voice_output.set_mode("casual")
                except:
                    pass
                
                self.voice_output.speak(response)
        else:
            # Якщо немає результату, все одно оновлюємо статус
            self.update_status("Idle", "cyanAccent")
            self.set_visual("idle")
        
        # Refresh Agent Queue UI if available
        if HAS_QUEUE_MANAGER and self.ui_callback:
            self.ui_callback("queue_update", {})

    # Голосові функції видалено - тестування через GUI

    # --- Protocols ---
