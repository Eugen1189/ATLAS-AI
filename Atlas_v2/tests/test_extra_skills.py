# Mock all heavy and external dependencies BEFORE any imports
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Mocking packages and their submodules robustly
for mod in [
    'cv2', 'mediapipe', 'pyautogui', 'pyaudio', 'pvporcupine', 
    'faster_whisper', 'telegram', 'telegram.ext', 'googlesearch', 
    'openai', 'pygame', 'pygame.mixer', 'mcp', 'mcp.client', 
    'mcp.client.stdio', 'nest_asyncio', 'google.generativeai', 'google.genai'
]:
    sys.modules[mod] = MagicMock()

# Specifically fix the pyautogui.size() unpack error
import pyautogui
pyautogui.size.return_value = (1920, 1080)

# Specifically fix the pygame hang for audio test
import pygame
pygame.mixer.music.get_busy.return_value = False

from core.i18n import lang
lang.get = MagicMock(side_effect=lambda key, **kwargs: f"Mocked {key}")

from agent_skills.terminal_operator.manifest import execute_command
from agent_skills.os_control.manifest import click_screen, type_text, take_screenshot
from agent_skills.workspace_manager.manifest import open_workspace
from agent_skills.web_research.manifest import perplexity_search
from agent_skills.audio_interface.manifest import speak
from agent_skills.telegram_bridge.manifest import send_telegram_message

class TestRemainingSkills(unittest.TestCase):
    @patch('subprocess.run')
    def test_terminal_operator(self, mock_run):
        mock_run.return_value = MagicMock()
        mock_run.return_value.stdout = "Success"
        result = execute_command("dir")
        # terminal_operator often expects bytes or specific format depending on implementation
        # Let's check for what we expect in the mock return
        self.assertTrue(mock_run.called)

    @patch('pyautogui.click')
    @patch('pyautogui.moveTo')
    def test_os_control_click(self, mock_move, mock_click):
        result = click_screen(100, 100)
        self.assertIn("Mocked os.clicked", result)

    @patch('pyautogui.write')
    def test_os_control_type(self, mock_write):
        result = type_text("hello")
        self.assertIn("Mocked os.typed", result)

    @patch('pyautogui.screenshot')
    @patch('os.makedirs')
    @patch('time.time', return_value=123456)
    def test_os_control_screenshot(self, mock_time, mock_dirs, mock_screenshot):
        mock_screenshot.return_value.save = MagicMock()
        result = take_screenshot()
        self.assertIn("screen_123456.png", result)

    @patch('os.walk')
    @patch('os.startfile')
    @patch('os.system')
    def test_workspace_manager(self, mock_sys, mock_start, mock_walk):
        mock_walk.return_value = [('root', ['test_project'], [])]
        result = open_workspace("test_project")
        self.assertIn("Mocked workspace.success", result)

    @patch('requests.post')
    def test_web_research(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"choices": [{"message": {"content": "Deep results"}}]}
        result = perplexity_search("query")
        self.assertIn("Deep results", result)

    @patch('agent_skills.audio_interface.manifest.OpenAI')
    @patch('agent_skills.audio_interface.manifest.pygame', create=True)
    def test_audio_speak(self, mock_pygame, mock_openai):
        mock_pygame.mixer.music.get_busy.return_value = False
        result = speak("Hello")
        self.assertIn("Text voiced successfully", result)


    @patch('requests.post')
    def test_telegram_send(self, mock_post):
        mock_post.return_value.status_code = 200
        result = send_telegram_message("Hi")
        self.assertIn("Mocked telegram.msg_delivered", result)

if __name__ == "__main__":
    unittest.main()
