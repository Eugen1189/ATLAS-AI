"""
Оновлений Brain - координатор для департаментів.

Brain тепер використовує Router для маршрутизації команд
до відповідних департаментів.
"""

import os
import threading
import re
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

from skills.router import Router
from skills.journal import Journal
from skills.context_buffer import ContextBuffer
from skills.personality import PersonalityEngine
# Імпорт інструментів для Function Calling
from skills.tools_definition import get_atlas_tools, execute_tool

# Завантаження ключів
current_dir = Path(__file__).resolve().parent.parent
env_path = current_dir / '.env'
load_dotenv(dotenv_path=env_path)

# Додаємо батьківську директорію для імпорту config
import sys
sys.path.insert(0, str(current_dir))

import config


class Brain:
    """
    Головний координатор ATLAS.
    
    Відповідає за:
    - Нормалізацію запитів
    - Маршрутизацію через Router
    - Збереження фактів у журнал
    """
    
    def __init__(self):
        # Завантаження API ключа з config.py
        api_key = config.GOOGLE_API_KEY
        if not api_key:
            print("⚠️ [BRAIN] Немає API ключа!")
        else:
            genai.configure(api_key=api_key)
        
        # Ініціалізація моделі з каскадним фолбеком (використовуємо моделі з config)
        try:
            # 1. Пріоритет: Модель з config
            self.model = genai.GenerativeModel(config.GEMINI_DEFAULT_MODEL) 
            print(f"🧠 [BRAIN] Model: {config.GEMINI_DEFAULT_MODEL}")
        except:
            try:
                # 2. Фолбек: Fallback модель з config
                self.model = genai.GenerativeModel(config.GEMINI_FALLBACK_MODEL)
                print(f"🧠 [BRAIN] Model: {config.GEMINI_FALLBACK_MODEL} (Fallback)")
            except Exception as e:
                # 3. Критична помилка
                print(f"❌ [BRAIN] Критична помилка ініціалізації моделі: {e}")
                self.model = None



        # Ініціалізація компонентів
        # Ініціалізація компонентів
        self.journal = Journal()
        self.context_buffer = ContextBuffer()
        self.personality = PersonalityEngine()
        from skills.memory_storage import get_memory_storage
        self.memory = get_memory_storage()
        self.router = Router(model=self.model)
        
        # Inbox Watcher буде ініціалізовано через set_inbox_callback()
        self.inbox_watcher = None
        self.tts_callback = None  # Callback для TTS сповіщень
        
        print("✅ [BRAIN] Ініціалізовано")
    
    def set_inbox_callback(self, tts_callback=None):
        """
        Встановлює callback для Inbox Watcher.
        
        Args:
            tts_callback: Функція для TTS сповіщень (опціонально)
        """
        from skills.inbox_watcher import InboxWatcher
        from pathlib import Path
        
        current_dir = Path(__file__).resolve().parent.parent
        inbox_dir = config.INBOX_DIR
        
        self.tts_callback = tts_callback
        self.inbox_watcher = InboxWatcher(
            inbox_dir=inbox_dir,
            callback=self._on_new_file_detected,
            check_interval=10.0  # Перевірка кожні 10 секунд
        )
        self.inbox_watcher.start()
        print("✅ [BRAIN] Inbox Watcher запущено")
    
    def _on_new_file_detected(self, file_path: str):
        """
        Callback для Inbox Watcher - викликається при виявленні нового файлу.
        
        Args:
            file_path: Шлях до нового файлу
        """
        try:
            from pathlib import Path
            file = Path(file_path)
            
            # Витягуємо тему з імені файлу
            filename = file.stem  # Без розширення
            parts = filename.split("_DONE_")
            
            # Визначаємо тип контенту та тему
            if filename.startswith("Article_"):
                content_type = "Стаття"
                if len(parts) > 0:
                    topic_part = parts[0].replace("Article_", "").replace("_", " ")
                    topic = topic_part[:30]
                else:
                    topic = "статтю"
            elif filename.startswith("Post_"):
                content_type = "Пост"
                if len(parts) > 0:
                    topic_part = parts[0].replace("Post_", "").replace("_", " ")
                    topic = topic_part[:30]
                else:
                    topic = "пост"
            else:
                content_type = "Контент"
                topic = "готовий"
            
            print(f"🔔 [BRAIN] Новий файл готовий: {file.name}")
            print(f"📝 [BRAIN] Тип: {content_type}, Тема: {topic}")
            
            # TTS сповіщення (якщо callback встановлено)
            if self.tts_callback:
                try:
                    if content_type == "Пост":
                        message = f"Пост в Instagram про {topic} готовий"
                    else:
                        message = f"{content_type} про {topic} готова"
                    self.tts_callback(message, priority=True)
                except Exception as e:
                    print(f"⚠️ [BRAIN] Помилка TTS сповіщення: {e}")
            
        except Exception as e:
            print(f"⚠️ [BRAIN] Помилка обробки нового файлу: {e}")

    def _normalize_query(self, query: str) -> str:
        """
        Мінімальна нормалізація запиту.
        """
        return query.lower().strip()

    def _check_emergency_commands(self, text: str) -> str:
        """Перевірка екстрених команд"""
        text_lower = text.lower().strip()
        emergency_patterns = {
            r'(стоп|stop|зупини|замовкни|вимкни все|turn off|shut down)': "🛑 Зупиняю всі процеси...",
            r'(тиша|silence|замовкни|вимкни звук)': "🔇 Вимкнено звук.",
            r'(вимкни|виключи|turn off|shutdown).*(все|all|систему|system)': "⚠️ Вимкнення системи..."
        }
        for pattern, response in emergency_patterns.items():
            if re.search(pattern, text_lower):
                print(f"⚡ [BRAIN] Екстрена команда виявлена: {pattern}")
                return response
        return None
    
    def _oracle_fallback(self, text: str) -> str:
        """Fallback до загальної AI розмови"""
        if not self.model: return "Помилка: модель не ініціалізована"
        try:
            context = self.context_buffer.get_context_string()
            # Dynamic System Prompt from Personality Engine
            system_prompt = self.personality.get_system_instruction()
            
            # Оптимізація контексту по проекту
            project_context = ""
            for project in ["кафе", "ghostsmm", "atlas"]:
                if project in text.lower():
                    project_context = self.memory.get_project_context(project)
                    break
            
            prompt = f"{system_prompt}\n\nCurrent Context:\n{context}\n{project_context}\nUser: {text}\nAtlas:"
            response = self.model.generate_content(prompt)
            return response.text if response.text else "Не зрозумів запит."
        except Exception as e:
            print(f"❌ [BRAIN] Помилка Oracle fallback: {e}")
            return f"Помилка обробки: {e}"

    def think(self, text: str, image=None, stop_event: threading.Event = None) -> str:
        """
        Основний мисленнєвий процес.
        Accepts optional image for visual context.
        """
        if stop_event and stop_event.is_set():
            return "Команда скасована."
        if not self.model:
            return "Помилка: модель не ініціалізована"
        
        query = self._normalize_query(text.strip())
        if not query: return ""
        
        # 1. Екстрені команди
        emergency = self._check_emergency_commands(query)
        if emergency: return emergency

        # 1.6. SCREEN AUDIT TRIGGER
        if any(w in query for w in ["аудит", "audit", "screen audit"]):
             print("📸 [BRAIN] Спрацював тригер аудиту екрана")
             if self.tts_callback:
                 self.tts_callback("Роблю знімок екрана, зачекайте секунду...", priority=True)
             
             if self.router.context and self.router.context.operations_dept:
                 path = self.router.context.operations_dept.screen_audit()
                 if "temp_audit.png" in path:
                     try:
                         import PIL.Image
                         img = PIL.Image.open(path)
                         audit_prompt = "Ти — експерт-аналітик SystemCOO. Проаналізуй цей скріншот робочого простору. Знайди баги в UI, помилки в коді або дай пораду щодо оптимізації проекту."
                         
                         print("🧠 [BRAIN] Відправляю скріншот на аудит в Gemini...")
                         response = self.model.generate_content([audit_prompt, img])
                         return response.text if response.text else "Не вдалося провести аудит."
                     except Exception as e:
                         print(f"❌ [BRAIN] Помилка аудиту: {e}")
                         return f"Помилка при спробі зробити аудит: {e}"
                 else:
                     return f"Не вдалося зробити знімок екрана: {path}"

        print(f"🧠 [BRAIN] Думаю над: {query}")
        
        # Візуальний пульс роздумів
        try:
            from core.visual_bridge import get_visual_bridge
            get_visual_bridge().send_system_event("thinking_start")
        except: pass

        # 1.5. ATOMIC SEQUENCE ORCHESTRATOR inside Brain
        # This handles multi-step commands BEFORE they hit greedy Command Registry
        from skills.command_registry import get_registry
        registry = get_registry()
        steps = registry.split_sequence(query)
        
        if len(steps) > 1:
            import time
            results = []
            print(f"🔄 [BRAIN] Detected atomic sequence: {steps}")
            
            for i, step in enumerate(steps):
                if stop_event and stop_event.is_set():
                     break
                
                print(f"👉 [BRAIN] Step {i+1}: {step}")
                # Recursively call think for each step
                res = self.think(step, image=image, stop_event=stop_event)
                results.append(f"Step {i+1}: {res}")
                
                # Removed artificial delay for performance
                # if i < len(steps) - 1:
                #     time.sleep(2.0) 
            
            return "\n".join(results)

        # 2. Command Registry (Deterministic Layer)
        try:
            from skills.command_registry import get_registry
            registry = get_registry()
            cmd_match = registry.find_command_with_handler(query)
            
            if cmd_match:
                cmd_name, cmd_def, args = cmd_match
                dept_name = cmd_def.get("department")
                handler_name = cmd_def.get("handler", "handle")
                
                # Знаходимо департамент
                target_dept = next((d for d in self.router.departments if d.name == dept_name), None)
                
                if target_dept:
                    # Check method existence
                    if hasattr(target_dept, handler_name):
                        handler = getattr(target_dept, handler_name)
                        print(f"✅ [BRAIN] Command Registry → {dept_name}.{handler_name} (command: {cmd_name})")
                        
                        try:
                            # Dynamic Argument Unpacking
                            if args:
                                result = handler(query, self.router.context, *args)
                            else:
                                result = handler(query, self.router.context)
                        except TypeError:
                             # Fallback: try without args or context if signature differs
                             try:
                                result = handler(query)
                             except:
                                result = handler()
                        
                        if result:
                             # threading.Thread(target=self.journal.analyze_and_save, args=(text, result), daemon=True).start()
                             return result
                    else:
                        print(f"⚠️ [BRAIN] Handler '{handler_name}' not found in {dept_name}. Using handle()")
                        result = target_dept.handle(query, self.router.context)
                        if result:
                             # threading.Thread(target=self.journal.analyze_and_save, args=(text, result), daemon=True).start()
                             return result

        except Exception as e:
            print(f"⚠️ [BRAIN] Помилка Command Registry: {e}")
            import traceback
            traceback.print_exc()

        # 3. Router Fallback (для сумісності)
        result = self.router.route(query)
        if result:
             # threading.Thread(target=self.journal.analyze_and_save, args=(text, result), daemon=True).start()
             return result


        # 4. SEMANTIC CORE (Function Calling) - для складних запитів
        try:
            from google.api_core.exceptions import ResourceExhausted
            
            # Отримуємо список інструментів (включаючи web_search!)
            tools_list = get_atlas_tools()
            
            # 🔥 МАГІЯ: Передаємо tools прямо у запит
            # Додаємо контекст для кращого виклику інструментів
            system_instruction = """
            SYSTEM INSTRUCTION:
            You are ATLAS. Your Vision Department manages the camera and gestures.
            If the user says 'start camera', 'zapuste kameru', or similar, you MUST use the 'vision_control' tool or respond with intent to start vision.

            MULTI-STEP COMMANDS:
            If a user command involves multiple steps (e.g. "Open Notepad, write text, save"), you should understand that these are sequential actions. 
            However, since you can only call one tool at a time effectively in this loop, prioritize the FIRST action (Open Notepad). 
            If you need to perform complex UI sequences, consider using the 'ui_automation' tool or a 'scenario'.
            """
            
            # Отримуємо історію розмови
            context_str = self.context_buffer.get_context_string()
            # Оптимізація контексту по проекту
            project_context = ""
            for project in ["кафе", "ghostsmm", "atlas", "systemcoo"]:
                if project in query.lower():
                    project_context = self.memory.get_project_context(project)
                    break

            full_query = f"{system_instruction}\n"
            if context_str:
                full_query += f"\n--- CONVERSATION CONTEXT ---\n{context_str}\n"
            if project_context:
                full_query += f"\n--- PROJECT SPECIFIC MEMORY ---\n{project_context}\n"
            
            full_query += f"\n---------------------------\nUser Query: {query}"
            
            if stop_event and stop_event.is_set():
                return "Команда скасована."

            # Prepare content for generation (Text or Text+Image)
            content_parts = [full_query]
            if image:
                print("📸 [BRAIN] Analyzing image with query...")
                content_parts.append(image)

            response = self.model.generate_content(
                content_parts,
                tools=tools_list,
                tool_config={'function_calling_config': 'AUTO'}
            )

            # Перевіряємо, чи захотіла модель викликати функцію
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        # 🛠 ВИКЛИК ІНСТРУМЕНТУ (напр. web_search)
                        fc = part.function_call
                        print(f"🔧 [BRAIN] Виклик інструменту: {fc.name} з аргументами {fc.args}")
                        
                        # Конвертуємо args у словник якщо потрібно
                        # MapComposite має метод .items() для ітерації
                        args_dict = {}
                        try:
                            if isinstance(fc.args, dict):
                                args_dict = fc.args
                            elif hasattr(fc.args, 'items'):
                                # MapComposite або подібний об'єкт (proto.marshal.collections.maps.MapComposite)
                                import proto
                                for key, val in fc.args.items():
                                    # Обробляємо RepeatedComposite якщо є
                                    if isinstance(val, proto.marshal.collections.repeated.RepeatedComposite):
                                        args_dict[key] = [v for v in val]
                                    elif hasattr(val, '__iter__') and not isinstance(val, (str, bytes)):
                                        try:
                                            args_dict[key] = [v for v in val]
                                        except:
                                            args_dict[key] = val
                                    else:
                                        args_dict[key] = val
                            elif hasattr(fc.args, '__dict__'):
                                args_dict = fc.args.__dict__
                            else:
                                # Остання спроба - спробуємо конвертувати через dict()
                                try:
                                    args_dict = dict(fc.args)
                                except:
                                    args_dict = {}
                        except Exception as e:
                            print(f"⚠️ [BRAIN] Помилка конвертації args: {e}")
                            args_dict = {}
                        
                        # Перевірка на "зламані" аргументи (тільки перша спроба - уникаємо рекурсії)
                        if fc.args and not args_dict and "ERROR:" not in query:
                            print("🔄 [BRAIN] Retry logic: Invalid JSON format detected. Asking LLM for a fix...")
                            retry_query = f"{query}\n\nERROR: Your previous tool call '{fc.name}' had invalid argument format. Please call it again with valid JSON arguments."
                            return self.think(retry_query, image=image, stop_event=stop_event)
                        
                        print(f"🔍 [BRAIN] Конвертовані аргументи: {args_dict}")
                        
                        if stop_event and stop_event.is_set():
                            return "Команда скасована."
                        # Виконуємо функцію
                        tool_result = execute_tool(fc.name, args_dict)
                        
                        # Повертаємо результат користувачу
                        result = f"✅ Виконано ({fc.name}):\n{tool_result}"
                        
                        # Зберігаємо у журнал (BATCH MODE: Аналіз вимкнено для економії квоти)
                        # if result:
                        #     threading.Thread(
                        #         target=self.journal.analyze_and_save,
                        #         args=(text, result),
                        #         daemon=True
                        #     ).start()
                        
                        return result

            # Якщо інструмент не знадобився - просто текст
            if response.text:
                result = response.text
            else:
                # Якщо немає тексту - fallback до Oracle
                result = self._oracle_fallback(query)

        except ResourceExhausted:
            print("⚠️ [BRAIN] Quota Exceeded (ResourceExhausted). Cooling down...")
            import time
            time.sleep(5)
            return "Сер, я перевантажений запитами (429). Зачекаю 5 секунд і продовжу. Спробуйте ще раз."
            
        except Exception as e:
            print(f"❌ [BRAIN] Помилка семантичного ядра: {e}")
            import traceback
            traceback.print_exc()
            result = self._oracle_fallback(query)
        
        
        # Update Cognitive Loop (Action Phase)
        if result:
             self.context_buffer.add_interaction(text, result)
             self.personality.update_interaction('command') # Treat successful processing as valid command
             
             # Background Journaling (DISABLED to save quota)
             # threading.Thread(
             #    target=self.journal.analyze_and_save,
             #    args=(text, result),
             #    daemon=True
             # ).start()
        
        return result if result else self._oracle_fallback(query)