import sys
import os
import time
import math
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QThread

# Add project path
sys.path.insert(0, os.path.abspath("Atlas_v2"))
from core.ui.hud import AxisHUD
from agent_skills.vision_eye.logic import VisionManager
from core.logger import logger

if __name__ == "__main__":
    app = QApplication(sys.argv)
    hud = AxisHUD()
    hud.show()
    
    logger.info("system.integration_test | HUD + Vision")
    
    # Initialize Vision with the HUD bridge
    # Passing the bridge allows Vision to emit signals that HUD hears
    vision = VisionManager(hud_bridge=hud.bridge)
    
    # Start Vision in a separate thread to keep UI responsive
    vision_thread = QThread()
    vision.moveToThread(vision_thread) # Note: Need to check if VisionManager inherited from QObject. 
    # Actually, VisionManager uses its own threading.Thread internally. 
    # Let's just run it.
    
    vision.start()
    
    print("AXIS Vision HUD Integration Active.")
    print("Move your hand in front of the camera to see the Cyber-Aura.")
    print("Logs will appear in the corner. Press 'q' in the OpenCV window to stop.")
    
    sys.exit(app.exec())
