import os
import importlib
import sys
from unittest.mock import MagicMock

# Mock all heavy and external dependencies BEFORE any imports
for mod in [
    'cv2', 'mediapipe', 'pyautogui', 'pyaudio', 'pvporcupine', 
    'faster_whisper', 'telegram', 'telegram.ext', 'googlesearch', 
    'openai', 'pygame', 'pygame.mixer', 'mcp', 'mcp.client', 
    'mcp.client.stdio', 'nest_asyncio', 'google.generativeai', 'google.genai',
    'flet', 'pystray'
]:
    sys.modules[mod] = MagicMock()


def test_import_all_manifests():
    skills_dir = "Atlas_v2/agent_skills"
    for folder in os.listdir(skills_dir):
        manifest_path = os.path.join(skills_dir, folder, "manifest.py")
        if os.path.exists(manifest_path):
            module_name = f"agent_skills.{folder}.manifest"
            try:
                importlib.import_module(module_name)
                print(f"Successfully imported {module_name}")
            except Exception as e:
                print(f"Failed to import {module_name}: {e}")

if __name__ == "__main__":
    test_import_all_manifests()
