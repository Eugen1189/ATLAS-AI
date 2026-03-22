import pyautogui
import os
import time

# Give some time for the window to render
time.sleep(2)

screenshot_path = "mascot_proof.png"
try:
    screenshot = pyautogui.screenshot()
    screenshot.save(screenshot_path)
    print(f"Screenshot saved to {screenshot_path}")
except Exception as e:
    print(f"Screenshot failed: {e}")
