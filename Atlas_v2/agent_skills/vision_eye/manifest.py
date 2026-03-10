import os
import threading
from .logic import VisionManager
from core.vision_engine import vision_engine
from core.i18n import lang
from core.skills.wrapper import agent_tool

# Unified Vision Manifest (v2.7.8)
# All capture operations delegated to core/vision_engine.py

@agent_tool
def toggle_gestures(active: bool) -> str:
    """
    Enables/disables hands-free computer control using gesture recognition.
    """
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
def capture_visual_context() -> str:
    """Takes a photo from the webcam. Useful for 'what am I doing' or 'who is here'."""
    result = vision_engine.capture_camera()
    return lang.get("vision.photo_taken", path=result) if "Error" not in result else result

@agent_tool
def take_screenshot() -> str:
    """
    Робить знімок екрана. ВИКОРИСТОВУЙ ЦЕ, коли користувач просить 'зроби скріншот' або 'подивись на екран'. Повертає шлях до файлу.
    """
    result = vision_engine.capture_screen()
    return result if "Error" not in result else f"Failed: {result}"

@agent_tool
def capture_screen_context() -> str:
    """Takes a screenshot and returns a description for the brain."""
    result = vision_engine.capture_screen()
    return f"Screenshot saved at: {result}" if "Error" not in result else result

@agent_tool
def analyze_visual_context(prompt: str = None) -> str:
    """Captures camera image and analyzes it using Moondream2 logic."""
    path = vision_engine.capture_camera()
    if "Error" in path: return path
    return vision_engine.analyze(path, prompt)

@agent_tool
def analyze_screen_region(target_text: str, top: int, left: int, bottom: int, right: int) -> str:
    """
    Standard 2026 Focused Vision.
    Zooms into a specific area [top, left, bottom, right] in percentages (0-100) 
    to analyze blurry text or UI details at high resolution.
    """
    path = vision_engine.capture_screen()
    if "Error" in path: return path
    prompt = f"What is written in this region? Looking for: {target_text}"
    return vision_engine.analyze(path, prompt, region=[top, left, bottom, right])

EXPORTED_TOOLS = [
    toggle_gestures, 
    capture_visual_context, 
    take_screenshot,
    capture_screen_context,
    analyze_visual_context, 
    analyze_screen_region
]
