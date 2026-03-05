import os
import threading
from .logic import VisionManager
from core.i18n import lang

# Global variable for driver control
_vision_instance = None

def toggle_gestures(active: bool) -> str:
    """
    Enables or disables the mode for controlling the computer using hand gestures via webcam.
    Use this when the user wants to control the cursor, scroll pages, or
    interact with the interface "hands-free".
    
    Args:
        active: True to enable, False to disable.
    """
    global _vision_instance
    if active:
        if _vision_instance and _vision_instance.is_running:
            return lang.get("vision.already_active")
        
        # Create driver instance
        _vision_instance = VisionManager(camera_index=0)
        # Start in a separate thread to avoid blocking Atlas
        threading.Thread(target=_vision_instance.start, daemon=True).start()
        return lang.get("vision.activated")
    else:
        if _vision_instance:
            _vision_instance.stop()
            _vision_instance = None
            return lang.get("vision.disabled")
        return lang.get("vision.already_disabled")

def capture_visual_context() -> str:
    """
    Takes an instant snapshot from the webcam and analyzes it.
    Use this to 'see' the user, recognize an object in their hands,
    or understand the surrounding environment.
    """
    global _vision_instance
    # If the manager is not running, start it temporarily
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
        return lang.get("vision.photo_taken", path=save_path)
    
    return lang.get("vision.camera_failed")

EXPORTED_TOOLS = [toggle_gestures, capture_visual_context]
