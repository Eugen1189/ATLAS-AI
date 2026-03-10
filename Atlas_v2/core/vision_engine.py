"""
AXIS Unified Vision Engine (v2.7)
Centralized singleton for all visual operations (Webcam, Screen, Analysis).
Prevents descriptor conflicts and optimizes VRAM usage via Lazy Loading.
"""
import cv2
import os
import requests
import base64
from datetime import datetime
from PIL import ImageGrab
from core.logger import logger

class VisionEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VisionEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        
        # Absolute storage path (Universal)
        self.storage_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "memories", "visual_snapshots"
        ))
        os.makedirs(self.storage_root, exist_ok=True)
        self._initialized = True
        logger.info("vision.engine_initialized", storage=self.storage_root)

    def capture_screen(self) -> str:
        """Universal Screen Capture via Pillow (Thread-safe)"""
        try:
            screenshot = ImageGrab.grab(all_screens=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(self.storage_root, f"screen_{timestamp}.png")
            screenshot.save(file_path)
            logger.info("vision.screen_captured", path=file_path)
            return file_path
        except Exception as e:
            logger.error("vision.screen_capture_error", error=str(e))
            return f"Error: {e}"

    def capture_camera(self, camera_index=0) -> str:
        """Universal Camera Capture via DirectShow (Windows) / Default (Linux)"""
        # Lazy initialization of VideoCapture to prevent 'Access Denied'
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY)
        if not cap.isOpened():
            logger.error("vision.camera_failed", index=camera_index)
            return "Error: Camera unavailable."
        
        ret, frame = cap.read()
        if ret:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(self.storage_root, f"cam_{timestamp}.jpg")
            cv2.imwrite(file_path, frame)
            cap.release()
            logger.info("vision.camera_captured", path=file_path)
            return file_path
        
        cap.release()
        return "Error: Failed to grab frame."

    def analyze(self, image_path: str, prompt: str = None, region: list = None) -> str:
        """
        Unified Moondream2 logic with optional regional cropping.
        'region': [top, left, bottom, right] percentages (0-100).
        """
        if not os.path.exists(image_path):
            return "Error: Path not found."

        if not prompt:
            prompt = "Describe this image. Focus on technical details and text."

        try:
            # 1. Handle Optional Cropping (Advanced 2026 Skill)
            from PIL import Image
            img = Image.open(image_path)
            
            if region and len(region) == 4:
                w, h = img.size
                t, l, b, r = region
                # Percentage to Pixel
                crop_box = (l * w / 100, t * h / 100, r * w / 100, b * h / 100)
                img = img.crop(crop_box)
                # Save temp crop
                image_path = image_path.replace(".", "_crop.")
                img.save(image_path)
                logger.debug("vision.region_cropped", region=region)

            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
            
            payload = {
                "model": "moondream",
                "prompt": prompt,
                "images": [b64],
                "stream": False
            }
            
            # Dynamic timeout (120s for VRAM swapping)
            url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            response = requests.post(f"{url}/api/generate", json=payload, timeout=120)
            
            if response.status_code == 200:
                res = response.json().get("response", "No result.")
                logger.info("vision.analysis_success", result=res[:50])
                return res
            return f"Ollama Error: {response.status_code}"
            
        except requests.exceptions.Timeout:
            return "Vision Timeout: Model is swapping in VRAM. Retry in 60s."
        except Exception as e:
            return f"Analysis Exception: {e}"

# Global instance for easy access
vision_engine = VisionEngine()
