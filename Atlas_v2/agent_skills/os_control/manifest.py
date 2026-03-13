import pyautogui
from core.vision_engine import vision_engine
from core.logger import logger
from core.skills.wrapper import agent_tool

# Security: Failsafe enabled (move mouse to corner to abort)
pyautogui.FAILSAFE = True

@agent_tool
def click_screen(x: int, y: int, clicks: int = 1, button: str = 'left', **kwargs) -> str:
    """
    Standard 2026 Mouse Interaction.
    """
    logger.info("os.click", x=x, y=y, clicks=clicks, button=button)
    try:
        pyautogui.moveTo(x, y, duration=0.3)
        pyautogui.click(clicks=clicks, button=button)
        return f"Successfully clicked {button} button {clicks} time(s) at ({x}, {y})."
    except Exception as e:
        return f"Mouse Action Failed: {e}"

@agent_tool
def type_text(text: str, press_enter: bool = False, delay: float = 0.01) -> str:
    """
    Types text with human-like delay.
    """
    logger.info("os.type", length=len(text))
    try:
        pyautogui.write(text, interval=delay)
        if press_enter:
            pyautogui.press('enter')
        return f"Typed text sequence: '{text[:30]}...'"
    except Exception as e:
        return f"Keyboard Action Failed: {e}"

@agent_tool
def press_hotkey(hotkey: str, **kwargs) -> str:
    """
    Presses complex hotkeys. Example: 'ctrl,alt,delete' or 'win,r'.
    """
    try:
        keys = [k.strip() for k in hotkey.split(',')]
        pyautogui.hotkey(*keys)
        return f"Hotkey sequence '{hotkey}' executed."
    except Exception as e:
        return f"Hotkey Error: {e}"

@agent_tool
def get_screen_resolution(**kwargs) -> str:
    """Returns the current screen resolution (width, height)."""
    w, h = pyautogui.size()
    return f"Current Screen Resolution: {w}x{h}"

@agent_tool
def get_active_window(**kwargs) -> str:
    """Returns the title of the currently focused window."""
    try:
        import pygetwindow as gw
        win = gw.getActiveWindow()
        return f"Current Window: {win.title}" if win else "Desktop"
    except Exception: return "Unknown Window (Requires pygetwindow)"

@agent_tool
def find_and_click_text(target_text: str, **kwargs) -> str:
    """
    High-Level 2026 Skill: Uses Vision Engine to find text on screen and clicks it.
    Automatically handles multi-monitor or blurry text.
    """
    logger.info("os.vision_search", target=target_text)

    
    # 1. Take fresh screenshot
    img_path = vision_engine.capture_screen()
    if "Error" in img_path: return img_path
    
    # 2. Ask Moondream for coordinates
    prompt = f"Find the UI element with text '{target_text}'. If found, return ONLY the center [X, Y] coordinates in pixels. Format: [X, Y]. If not found, reply exactly with 'NOT_FOUND'."
    analysis = vision_engine.analyze(img_path, prompt)
    
    # 3. Simple Coordinate Parser (Hardened)
    try:
        if "NOT_FOUND" in analysis:
             return f"Vision module reported '{target_text}' is not visible on screen."
             
        import re
        coords = re.findall(r'\[(\d+),\s*(\d+)\]', analysis)
        if coords:
            x, y = map(int, coords[0])
            # Safety Check: Sanitize and Click
            w, h = pyautogui.size()
            if x > w or y > h: 
                return f"❌ [SCALE ERROR]: Coords ({x}, {y}) exceed resolution {w}x{h}."
            return click_screen(x, y)
        else:
            return f"OCR parsing failed. Moondream returned: {analysis[:100]}..."
    except Exception as e:
        return f"Coordinate extraction failed: {e}. Raw analysis: {analysis}"

@agent_tool
def take_screenshot(**kwargs) -> str:
    """
    Captures a full screenshot of all monitors.
    Returns: Path to the saved image file.
    """
    logger.info("os.screenshot")
    try:
        path = vision_engine.capture_screen()
        return f"Successfully captured screen: {path}"
    except Exception as e:
        return f"Screenshot Failed: {e}"

EXPORTED_TOOLS = [click_screen, type_text, press_hotkey, get_screen_resolution, find_and_click_text, get_active_window, take_screenshot]
