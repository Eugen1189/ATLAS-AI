import pyautogui
import time
import os

# Налаштування безпеки: зупинка скрипта, якщо мишу завести в кут екрана
pyautogui.FAILSAFE = True

def take_screenshot() -> str:
    """
    Робить знімок поточного екрана і зберігає його на диск.
    Використовуй цей інструмент, коли користувач просить 'подивися на екран', 'що ти бачиш',
    або коли тобі потрібно проаналізувати інтерфейс перед тим, як клікнути.
    Повертає шлях до збереженого файлу.
    """
    print("👁️ [OS_Control]: Роблю знімок екрана...")
    # Створюємо папку для скріншотів, якщо її немає
    os.makedirs("memories/vision", exist_ok=True)
    
    file_path = f"memories/vision/screen_{int(time.time())}.png"
    screenshot = pyautogui.screenshot()
    screenshot.save(file_path)
    
    abs_path = os.path.abspath(file_path)
    return abs_path

def click_screen(x: int, y: int) -> str:
    """
    Клікає лівою кнопкою миші по заданих координатах X та Y на екрані.
    Використовуй це ТІЛЬКИ після того, як ти проаналізував скріншот і точно знаєш координати потрібної кнопки.
    
    Args:
        x: Координата X на екрані.
        y: Координата Y на екрані.
    """
    print(f"🖱️ [OS_Control]: Клік мишкою на ({x}, {y})")
    pyautogui.moveTo(x, y, duration=0.5) # Плавний рух виглядає природніше
    pyautogui.click()
    return f"Виконано клік по координатах X:{x}, Y:{y}."

def type_text(text: str, press_enter: bool = False) -> str:
    """
    Друкує заданий текст на клавіатурі.
    Використовуй це для введення пошукових запитів, написання коду або повідомлень.
    
    Args:
        text: Текст, який потрібно надрукувати.
        press_enter: Якщо True, після введення тексту буде натиснуто клавішу Enter.
    """
    print(f"⌨️ [OS_Control]: Друкую текст: '{text[:20]}...'")
    pyautogui.write(text, interval=0.05)
    if press_enter:
        pyautogui.press('enter')
    return f"Текст '{text}' успішно надруковано."

def press_hotkey(hotkey: str) -> str:
    """
    Натискає системну клавішу або комбінацію клавіш.
    Приклади: 'enter', 'win', 'ctrl,c', 'ctrl,v', 'alt,tab', 'esc'.
    
    Args:
        hotkey: Назва клавіші або комбінація через кому.
    """
    print(f"⌨️ [OS_Control]: Натискаю комбінацію: {hotkey}")
    keys = hotkey.split(',')
    pyautogui.hotkey(*keys)
    return f"Комбінацію клавіш '{hotkey}' натиснуто."

# Експортуємо інструменти для Оркестратора
EXPORTED_TOOLS = [take_screenshot, click_screen, type_text, press_hotkey]
