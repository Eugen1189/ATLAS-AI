import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from core.logger import logger

class AxisHUD(QMainWindow):
    """
    Main HUD (Heads-Up Display) for AXIS v2.5.
    
    This window is a transparent overlay that stays on top of all other windows
    and does not interact with mouse inputs, allowing the user to work normally
    while seeing system telemetry.
    """

    def __init__(self):
        """
        Initializes the HUD window with specific flags for transparency and overlay behavior.
        """
        super().__init__()
        logger.info("ui.hud_initializing", version="2.5.0")
        
        # 1. Window Flags: Frameless, Always on Top, No Taskbar icon (optional)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # No taskbar icon
        )
        
        # 2. Transparency & Mouse Transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.set_mouse_transparent()
        
        # 3. Layout and Widgets
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        
        # 4. Telemetry Label
        self.status_label = QLabel("AXIS v2.5 | LOCAL BRAIN")
        self.status_label.setFont(QFont("Consolas", 12))
        self.status_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 150);
                border-radius: 5px;
                padding: 10px;
                border: 1px solid rgba(255, 255, 255, 50);
            }
        """)
        
        self.layout.addWidget(self.status_label)
        
        # Set full screen size but keep it transparent
        self.showFullScreen()
        logger.info("ui.hud_started", mode="transparent_overlay")

    def set_mouse_transparent(self):
        """
        Enables the WindowTransparentForInput flag to ensure mouse clicks 
        pass through the HUD to underlying windows.
        """
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput)

    def update_telemetry(self, text: str):
        """
        Updates the telemetry text displayed on the HUD.
        
        Args:
            text (str): The new telemetry or status string to display.
        """
        self.status_label.setText(text)

def launch_hud():
    """
    Utility function to launch the HUD in a separate application loop if needed.
    (Note: Typically, AXIS would manage this in its main loop or a thread).
    """
    app = QApplication(sys.argv)
    hud = AxisHUD()
    hud.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    launch_hud()
