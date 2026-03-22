"""
AXIS Unified Vision Engine (v2.7)
Centralized singleton for all visual operations (Webcam, Screen, Analysis).
Prevents descriptor conflicts and optimizes VRAM usage via Lazy Loading.
"""
import os
import requests
import base64
import json
from datetime import datetime
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
        from PIL import ImageGrab
        try:
            # Consistent v2.8+ behavior: capture all screens
            screenshot = ImageGrab.grab(all_screens=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(self.storage_root, f"screen_{timestamp}.png")
            screenshot.save(file_path)
            logger.info("vision.screen_captured", path=file_path)
            return file_path
        except Exception as e:
            logger.error("vision.screen_capture_error", error=str(e))
            return f"Error: {e}"


    def analyze(self, image_path: str, prompt: str = None, region: list = None, model: str = None) -> str:
        """
        Unified Analysis logic with model selection and regional cropping.
        'region': [top, left, bottom, right] percentages (0-100).
        'model': name of the model in Ollama (e.g., 'moondream', 'llama3.2-vision').
        """
        if not os.path.exists(image_path):
            return "Error: Path not found."

        if not prompt:
            prompt = "Describe this image. Focus on technical details and text."
            
        if not model:
            # Fallback to moondream for general lightness
            model = "moondream"

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
                "model": model,
                "prompt": prompt,
                "images": [b64],
                "stream": False
            }
            
            # Dynamic timeout (120s for VRAM swapping)
            url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            logger.info("vision.requesting_analysis", model=model)
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

    def capture_and_analyze(self, prompt: str = None, model: str = "llama3.2-vision") -> str:
        """Convenience method to capture a frame and analyze it in one go (Unified v2.9)."""
        path = self.capture_screen()
        if "Error" in path: return path
        return self.analyze(path, prompt, model=model)

    def draw_tree_diagram(self, tree_text: str, title: str = "Folder Structure") -> str:
        """Draws a monospaced text-based file tree as an image using Pillow."""
        from PIL import Image, ImageDraw, ImageFont
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(self.storage_root, f"tree_diagram_{timestamp}.png")
            
            lines = [title, "=" * len(title), ""] + tree_text.strip().split('\n')
            # Limit to max 100 lines for visual sanity
            if len(lines) > 100:
                lines = lines[:100] + ["... (truncated)"]
                
            # Try to load a monospace font, fallback to default
            try:
                # Windows standard monospace
                font = ImageFont.truetype("consola.ttf", 14)
            except:
                try:
                    font = ImageFont.truetype("cour.ttf", 14)
                except:
                    font = ImageFont.load_default()
                
            dummy_img = Image.new('RGB', (1, 1))
            draw = ImageDraw.Draw(dummy_img)
            
            # Simple line height estimation
            try:
                bbox = draw.textbbox((0, 0), "A", font=font)
                line_spacing = (bbox[3] - bbox[1]) + 6
                # find max width
                max_w = max(draw.textbbox((0, 0), line, font=font)[2] for line in lines)
            except AttributeError:
                line_spacing = 16
                max_w = max(len(line) * 8 for line in lines)
                
            img_width = max(600, int(max_w) + 40)
            img_height = (len(lines) * int(line_spacing)) + 40
            
            img = Image.new('RGB', (img_width, img_height), color=(30, 30, 40)) # Dark theme background
            draw = ImageDraw.Draw(img)
            
            y_text = 20
            # Colors
            title_color = (100, 200, 255)
            text_color = (200, 220, 220)
            
            for i, line in enumerate(lines):
                c = title_color if i < 2 else text_color
                draw.text((20, y_text), line, font=font, fill=c)
                y_text += line_spacing
                
            img.save(file_path)
            logger.info("vision.tree_diagram_created", path=file_path)
            return file_path
        except Exception as e:
            logger.error("vision.diagram_failed", error=str(e))
            return ""

# Global instance for easy access
vision_engine = VisionEngine()
