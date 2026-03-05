import sys
import os
import time
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Add project path
sys.path.insert(0, os.path.abspath("Atlas_v2"))
from core.ui.hud import AxisHUD
from core.logger import logger

def simulate_logs(hud):
    """Simulates AXIS events to test the HUD streamer."""
    events = [
        "system.brain_active | model=llama3.2",
        "vision.gesture_detected | type=HAND_OPEN",
        "skill.executing | action=weather_check",
        "memory.retrieving | key=user_location",
        "system.response_generated | length=142 chars",
        "guardian.monitoring | status=SAFE"
    ]
    
    counter = 0
    def send_next():
        nonlocal counter
        if counter < len(events):
            # Using standard logger which is hooked by HUDLogHandler
            logger.info(events[counter])
            counter += 1
        else:
            logger.info("test.finished | all events streamed")
            # No exit here so user can see it
            
    timer = QTimer()
    timer.timeout.connect(send_next)
    timer.start(1500) # Every 1.5 seconds
    return timer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    hud = AxisHUD()
    hud.show()
    
    # Start simulation
    t = simulate_logs(hud)
    
    print("HUD is running as a transparent overlay.")
    print("You should see green logs appearing at the bottom-left.")
    
    sys.exit(app.exec())
