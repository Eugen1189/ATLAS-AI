"""
AXIS Lightweight Vision Module (v2.6 Hotfix)
Provides direct screen/camera capture and local model analysis.
"""
import cv2
import numpy as np
from PIL import ImageGrab
import os
import base64
import requests
from datetime import datetime
from core.logger import logger
from core.i18n import lang

class VisionLocal:
    def __init__(self):
        self.last_screenshot = None
        # Use absolute path for storage to avoid process-isolation issues
        self.storage_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "memories", "visual_snapshots"
        ))
        os.makedirs(self.storage_path, exist_ok=True)

    def capture_screen(self):
        """Пряме захоплення екрана без використання MediaPipe/DirectX сервісів"""
        try:
            # Використовуємо Pillow для швидкого знімка без конфліктів з GPU
            screenshot = ImageGrab.grab(all_screens=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(self.storage_path, f"screen_{timestamp}.png")
            screenshot.save(file_path)
            self.last_screenshot = file_path
            logger.info("vision.screen_captured", path=file_path)
            return file_path
        except Exception as e:
            logger.error("vision.screen_capture_error", error=str(e))
            return f"Error capturing screen: {str(e)}"

    def capture_camera(self):
        """Захоплення з камери через DirectShow (мінімізує конфлікти на Windows)"""
        # CAP_DSHOW вирішує проблему 'Access is denied' в ізольованих процесах
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            logger.error("vision.camera_access_denied")
            return "Error: Camera access denied or busy."
        
        ret, frame = cap.read()
        if ret:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(self.storage_path, f"cam_{timestamp}.jpg")
            cv2.imwrite(file_path, frame)
            cap.release()
            logger.info("vision.camera_captured", path=file_path)
            return file_path
        cap.release()
        logger.error("vision.camera_frame_failed")
        return "Error: Failed to grab frame."

    def analyze_with_moondream(self, image_path: str, prompt: str = None) -> str:
        """Інтеграція з локальною Ollama (Moondream2)"""
        if not os.path.exists(image_path):
            return f"Error: Image file not found at {image_path}"
            
        logger.info("vision.local_analysis_started", path=image_path)
        
        if not prompt:
            prompt = "Describe this image in detail. Identify any text, people, or screen content."
        
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                
            payload = {
                "model": "moondream",
                "prompt": prompt,
                "images": [base64_image],
                "stream": False
            }
            
            # Using a longer timeout (120s) as vision models require VRAM swapping
            response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=120)
            
            if response.status_code == 200:
                result = response.json().get("response", "No description generated.")
                logger.info("vision.local_analysis_complete")
                return result
            else:
                return f"Error from Ollama: {response.status_code}. (Is Moondream model pulled?)"
                
        except requests.exceptions.Timeout:
            logger.error("vision.local_timeout")
            return "Local Vision Error: Timeout (120s exceeded). The model is swaping in VRAM. Please try again in a moment."
        except Exception as e:
            logger.error("vision.local_exception", error=str(e))
            return f"Local Vision Exception: {str(e)}"

# Compatibility helper for existing manifest.py
def describe_image_local(image_path: str, prompt: str = None) -> str:
    return VisionLocal().analyze_with_moondream(image_path, prompt)
