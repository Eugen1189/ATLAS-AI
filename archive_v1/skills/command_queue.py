"""
Черга команд для неблокуючої обробки запитів
"""
import queue
import threading
import time
from typing import Callable, Optional

class CommandQueue:
    """
    Черга команд з обробкою в окремому потоці.
    Запобігає блокуванню основного потоку.
    """
    def __init__(self, processor: Callable):
        """
        Args:
            processor: Функція, яка обробляє команди (brain.think)
        """
        self.queue = queue.Queue()
        self.processor = processor
        self.is_running = False
        self.worker_thread = None
        self.current_command = None
        self.callbacks = {}  # {command_id: callback}
        self.command_counter = 0
        self._current_stop_event = None # Reference to active stop event
        
    def start(self):
        """Запускає worker потік"""
        if self.is_running:
            return
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        print("✅ [QUEUE] Черга команд запущена")
    
    def stop(self):
        """Зупиняє worker потік"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2)
        print("⏹️ [QUEUE] Черга команд зупинена")
    
    def add_command(self, command: str, callback: Optional[Callable] = None, timeout: float = 30.0, **kwargs) -> int:
        """
        Додає команду до черги
        
        Args:
            command: Текст команди
            callback: Функція, яка викличеться з результатом (response, error)
            timeout: Максимальний час обробки (секунди)
            **kwargs: Додаткові аргументи для процесора (напр. image)
        """
        self.command_counter += 1
        command_id = self.command_counter
        
        item = {
            'id': command_id,
            'command': command,
            'callback': callback,
            'timeout': timeout,
            'kwargs': kwargs,
            'timestamp': time.time()
        }
        
        self.queue.put(item)
        print(f"📥 [QUEUE] Додано команду #{command_id}: {command[:50]}...")
        return command_id
    
    def _worker(self):
        """Worker потік - обробляє команди з черги"""
        while self.is_running:
            try:
                # Беремо команду з черги (з таймаутом, щоб можна було перевірити is_running)
                try:
                    item = self.queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                command_id = item['id']
                command = item['command']
                callback = item['callback']
                timeout = item['timeout']
                kwargs = item.get('kwargs', {})
                
                self.current_command = command
                print(f"🔄 [QUEUE] Обробляю команду #{command_id}: {command[:50]}...")
                
                start_time = time.time()
                result = None
                error = None
                
                try:
                    # Обробка з таймаутом
                    result = self._process_with_timeout(command, timeout, **kwargs)
                    elapsed = time.time() - start_time
                    result_preview = str(result)[:100] if result else "None"
                    print(f"✅ [QUEUE] Команда #{command_id} виконана за {elapsed:.2f}с")
                    print(f"📤 [QUEUE] Результат: {result_preview}...")
                except TimeoutError:
                    error = f"Таймаут обробки команди (>{timeout}с)"
                    print(f"⏱️ [QUEUE] Таймаут команди #{command_id}")
                except Exception as e:
                    error = str(e)
                    print(f"❌ [QUEUE] Помилка команди #{command_id}: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Викликаємо callback, якщо є
                if callback:
                    try:
                        print(f"📞 [QUEUE] Викликаю callback для команди #{command_id}")
                        callback(result, error)
                    except Exception as e:
                        print(f"⚠️ [QUEUE] Помилка callback: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"⚠️ [QUEUE] Callback не вказано для команди #{command_id}")
                
                self.current_command = None
                self.queue.task_done()
                
            except Exception as e:
                print(f"⚠️ [QUEUE] Помилка worker: {e}")
                time.sleep(0.1)
    
    
    
    def cancel_current_command(self):
        """Сигналізує поточній команді про зупинку"""
        if self._current_stop_event:
            print("🛑 [QUEUE] Sending STOP signal to current command...")
            self._current_stop_event.set()
    
    def _process_with_timeout(self, command: str, timeout: float, **kwargs):
        """
        Обробляє команду з таймаутом і підтримкою скасування
        """
        result_container = {'value': None, 'error': None}
        stop_event = threading.Event()
        self._current_stop_event = stop_event # Save reference for external cancellation
        
        def process_wrapper():
            try:
                # 1. Try passing stop_event
                try:
                    result_container['value'] = self.processor(command, stop_event=stop_event, **kwargs)
                except TypeError:
                    # 2. Configure kwargs without stop_event if not supported
                    try:
                        result_container['value'] = self.processor(command, **kwargs)
                    except TypeError:
                         # 3. Last resort: just command
                         result_container['value'] = self.processor(command)
            except Exception as e:
                result_container['error'] = e
        
        # Запускаємо в окремому потоці (daemon=True, щоб не блокував вихід)
        thread = threading.Thread(target=process_wrapper, daemon=True)
        thread.start()
        
        # Чекаємо завершення або таймауту
        thread.join(timeout=timeout)
        
        self._current_stop_event = None # Clear reference
        
        if thread.is_alive():
            # Якщо потік ще живий - це таймаут
            stop_event.set() # Signal intent to stop
            print(f"⚠️ [QUEUE] Thread timeout/hang on command: {command[:20]}...")
            raise TimeoutError(f"Command execution timed out (> {timeout}s)")
        
        if result_container['error']:
            raise result_container['error']
        
        return result_container['value']
    
    def get_status(self) -> dict:
        """Повертає статус черги"""
        return {
            'queue_size': self.queue.qsize(),
            'current_command': self.current_command,
            'is_running': self.is_running
        }

