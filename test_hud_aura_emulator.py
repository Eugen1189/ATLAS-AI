import sys
import os
import time
import math
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Add project path
sys.path.insert(0, os.path.abspath("Atlas_v2"))
from core.ui.hud import AxisHUD
from core.logger import logger

def simulate_cyber_vision(hud):
    """
    Simulates hand tracking data to test the HUD's Cyber-Aura logic
    without requiring a physical camera.
    """
    start_time = time.time()
    
    # Get screen size from HUD
    screen_w = hud.width()
    screen_h = hud.height()
    
    def emit_fake_vision():
        elapsed = time.time() - start_time
        
        # 1. Calculate a circular path for the 'hand'
        center_x, center_y = screen_w // 2, screen_h // 2
        radius = 200
        angle = elapsed * 2 # Speed of rotation
        
        target_x = center_x + int(radius * math.cos(angle))
        target_y = center_y + int(radius * math.sin(angle))
        
        # 2. Determine a cycling state
        cycle = int(elapsed % 8)
        if cycle < 3:
            state = "ACTIVE"
        elif cycle < 5:
            state = "CLICK"
        elif cycle < 7:
            state = "PAUSED"
        else:
            state = "IDLE"
            
        # 3. Emit the signal via the HUD's bridge
        hud.bridge.vision_update.emit({
            "x": target_x,
            "y": target_y,
            "state": state
        })
        
        # 4. Occasionally log to the HUD streamer
        if int(elapsed * 10) % 30 == 0:
            logger.info(f"vision.sim_detected | state={state} pos=({target_x},{target_y})")

    timer = QTimer()
    timer.timeout.connect(emit_fake_vision)
    timer.start(30) # 33 FPS simulation
    return timer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Create HUD
    hud = AxisHUD()
    hud.show()
    
    logger.info("system.emulator_start | CYBER-VISION MODE")
    
    try:
        # Start the simulation instead of real VisionManager
        t = simulate_cyber_vision(hud)
        
        print("--- AXIS HUD EMULATOR ACTIVE ---")
        print("Simulating hand movement and gestures...")
        print("You should see the pulsing Cyber-Aura on your screen.")
        print("Exit by closing the terminal or Ctrl+C.")
        
        sys.exit(app.exec())
    except Exception as e:
        print(f"CRITICAL EMULATOR ERROR: {e}")
        import traceback
        traceback.print_exc()
