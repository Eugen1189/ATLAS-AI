import pyautogui
import time
import os
from core.i18n import lang

# Security setting: stop script if mouse is moved to a corner of the screen
pyautogui.FAILSAFE = True

def take_screenshot() -> str:
    """
    Takes a screenshot of the current screen and saves it to disk.
    Use this tool when the user asks 'look at the screen', 'what do you see',
    or when you need to analyze the UI before clicking.
    Returns the path to the saved file.
    """
    print(lang.get("os.taking_screenshot"))
    # Create screenshots folder if it doesn't exist
    os.makedirs("memories/vision", exist_ok=True)
    
    file_path = f"memories/vision/screen_{int(time.time())}.png"
    screenshot = pyautogui.screenshot()
    screenshot.save(file_path)
    
    abs_path = os.path.abspath(file_path)
    return abs_path

def click_screen(x: int, y: int) -> str:
    """
    Clicks the left mouse button at specified X and Y coordinates on the screen.
    Use this ONLY after analyzing a screenshot and knowing the exact coordinates of the target button.
    
    Args:
        x: X coordinate on screen.
        y: Y coordinate on screen.
    """
    print(lang.get("os.mouse_click", x=x, y=y))
    pyautogui.moveTo(x, y, duration=0.5) # Smooth movement looks more natural
    pyautogui.click()
    return lang.get("os.clicked", x=x, y=y)

def type_text(text: str, press_enter: bool = False) -> str:
    """
    Types the specified text on the keyboard.
    Use this for typing search queries, writing code, or messages.
    
    Args:
        text: Text to type.
        press_enter: If True, Enter key will be pressed after typing.
    """
    print(lang.get("os.typing", text=text[:20]))
    pyautogui.write(text, interval=0.05)
    if press_enter:
        pyautogui.press('enter')
    return lang.get("os.typed", text=text)

def press_hotkey(hotkey: str) -> str:
    """
    Presses a system key or keyboard shortcut.
    Examples: 'enter', 'win', 'ctrl,c', 'ctrl,v', 'alt,tab', 'esc'.
    
    Args:
        hotkey: Name of the key or combo separated by comma.
    """
    print(lang.get("os.pressing", hotkey=hotkey))
    keys = hotkey.split(',')
    pyautogui.hotkey(*keys)
    return lang.get("os.pressed", hotkey=hotkey)

# Export tools for Orchestrator
EXPORTED_TOOLS = [take_screenshot, click_screen, type_text, press_hotkey]
