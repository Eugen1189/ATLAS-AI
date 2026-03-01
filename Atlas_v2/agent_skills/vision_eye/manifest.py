import os
import threading
import sys
from .vision_manager import VisionManager

# Глобальна змінна для контролю драйвера
_vision_instance = None

def toggle_gestures(active: bool) -> str:
    """
    Вмикає або вимикає режим керування комп'ютером за допомогою жестів рук через веб-камеру.
    Використовуй це, коли користувач хоче керувати курсором, гортати сторінки або 
    працювати з інтерфейсом "без рук".
    
    Args:
        active: True для увімкнення, False для вимкнення.
    """
    global _vision_instance
    if active:
        if _vision_instance and _vision_instance.is_running:
            return "Система візуального керування вже активна."
        
        # Створюємо екземпляр драйвера
        _vision_instance = VisionManager(camera_index=0)
        # Запускаємо в окремому потоці, щоб не блокувати Атласа
        threading.Thread(target=_vision_instance.start, daemon=True).start()
        return "Система візуального керування активована. Тепер я бачу твої жести."
    else:
        if _vision_instance:
            _vision_instance.stop()
            _vision_instance = None
            return "Система візуального керування вимкнена."
        return "Система вже була вимкнена."

def capture_visual_context() -> str:
    """
    Робить миттєвий знімок з веб-камери та аналізує його.
    Використовуй це, щоб 'побачити' користувача, впізнати предмет у його руках 
    або зрозуміти обстановку навколо.
    """
    global _vision_instance
    # Якщо менеджер не запущений, запускаємо його тимчасово
    temp_mode = False
    if not _vision_instance or not _vision_instance.is_running:
        _vision_instance = VisionManager(camera_index=0)
        _vision_instance._init_resources()
        temp_mode = True

    frame = _vision_instance.get_latest_frame() 
    
    if temp_mode:
        _vision_instance.stop()

    if frame:
        save_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "memories", "vision"))
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, "vision_snap.jpg")
        frame.save(save_path)
        return f"Я зробив фото. (Системна замітка: Фото збережено в {save_path}. Gemini проаналізує його мультимодально)."
    
    return "Не вдалося отримати зображення з камери."

EXPORTED_TOOLS = [toggle_gestures, capture_visual_context]
