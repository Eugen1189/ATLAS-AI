from .logic import VisionManager
from core.vision_engine import vision_engine
from core.i18n import lang
from core.skills.wrapper import agent_tool

# Unified Vision Manifest (v2.7.8)
# All capture operations delegated to core/vision_engine.py

@agent_tool
def analyze_screen(text: str = "Опиши детально, що ти зараз бачиш на екрані. Які програми відкриті?", **kwargs) -> str:
    """Captures and analyzes the screen. Use for 'what's on screen' queries."""
    # Delegate to Unified Engine
    analysis = vision_engine.capture_and_analyze(source="screen", prompt=text, model="llama3.2-vision")
    
    if "Error" in analysis:
        return f"❌ Збій системи зору: {analysis}"
        
    return f"👁️ [Аналіз Екрану]:\n{analysis}"


@agent_tool
def toggle_gestures(active: bool, **kwargs) -> str:
    """Toggles hands-free computer control using gesture recognition."""
    global _vision_instance
    if active:
        if '_vision_instance' in globals() and _vision_instance and _vision_instance.is_running:
            return lang.get("vision.already_active")
        _vision_instance = VisionManager(camera_index=0)
        threading.Thread(target=_vision_instance._processing_worker, daemon=True).start()
        return lang.get("vision.activated")
    else:
        if '_vision_instance' in globals() and _vision_instance:
            _vision_instance.stop()
            return lang.get("vision.disabled")
        return lang.get("vision.already_disabled")

@agent_tool
def capture_visual_context(**kwargs) -> str:
    """Takes a photo from the webcam. Useful for 'what am I doing' or 'who is here'."""
    result = vision_engine.capture_camera()
    return lang.get("vision.photo_taken", path=result) if "Error" not in result else result

@agent_tool
def capture_screen_snapshot(**kwargs) -> str:
    """
    [LEGACY/ALIAS]: Captures a screenshot of the current screen. 
    NOTE: For standard OS control, 'take_screenshot' from os_control is preferred.
    """
    return vision_engine.capture_screen()

@agent_tool
def analyze_visual_context(text: str = None, **kwargs) -> str:
    """Captures camera image and analyzes it using Moondream2 logic."""
    path = vision_engine.capture_camera()
    if "Error" in path: return path
    return vision_engine.analyze(path, text)

@agent_tool
def analyze_screen_region(target_text: str, top: int, left: int, bottom: int, right: int, **kwargs) -> str:
    """Zooms into a specific screen area (0-100%) to analyze text or UI details."""
    path = vision_engine.capture_screen()
    if "Error" in path: return path
    prompt = f"What is written in this region? Looking for: {target_text}"
    return vision_engine.analyze(path, prompt, region=[top, left, bottom, right])

EXPORTED_TOOLS = [
    analyze_screen,
    toggle_gestures, 
    capture_visual_context, 
    capture_screen_snapshot,
    analyze_visual_context, 
    analyze_screen_region
]
