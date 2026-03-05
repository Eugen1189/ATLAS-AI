import sys
import logging
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont
from core.logger import logger

class LogBridge(QObject):
    """
    Bridge to safely emit log signals from background threads to the UI thread.
    """
    new_log = pyqtSignal(str)

class HUDLogHandler(logging.Handler):
    """
    Custom logging handler that redirects logs to the HUD via a LogBridge.
    """
    def __init__(self, bridge: LogBridge):
        super().__init__()
        self.bridge = bridge

    def emit(self, record):
        try:
            msg = self.format(record)
            self.bridge.new_log.emit(msg)
        except Exception:
            self.handleError(record)

class AxisHUD(QMainWindow):
    """
    Main HUD (Heads-Up Display) for AXIS v2.5.
    
    Now includes a real-time Log Streamer (Pulse of AXIS).
    """

    def __init__(self):
        """
        Initializes the HUD window with specific flags and log streaming bridge.
        """
        super().__init__()
        logger.info("ui.hud_initializing", version="2.5.0")
        
        # 1. State and Bridge
        self.max_logs = 5
        self.log_labels = []
        self.bridge = LogBridge()
        self.bridge.new_log.connect(self.update_log)
        
        # 2. Window Flags
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool 
        )
        
        # 3. Transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.set_mouse_transparent()
        
        # 4. UI Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Top Container (Telemetry)
        self.top_layout = QVBoxLayout()
        self.top_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self.status_label = QLabel("AXIS v2.5 | LOCAL BRAIN")
        self.status_label.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #00BFFF; background: rgba(0,0,0,150); padding: 10px; border-radius: 5px;")
        self.top_layout.addWidget(self.status_label)
        
        # Bottom Container (Log Streamer)
        self.log_layout = QVBoxLayout()
        self.log_layout.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)
        
        # Assemble Main Layout
        self.main_layout.addLayout(self.top_layout)
        self.main_layout.addStretch()
        self.main_layout.addLayout(self.log_layout)
        
        # 5. Connect to standard logging
        hud_handler = HUDLogHandler(self.bridge)
        hud_handler.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger().addHandler(hud_handler)
        
        self.showFullScreen()
        logger.info("ui.hud_started", streamer="connected")

    def set_mouse_transparent(self):
        """Pass mouse inputs through the window."""
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput)

    def update_telemetry(self, text: str):
        """Updates the status title."""
        self.status_label.setText(text)

    def update_log(self, message: str):
        """
        Adds a new log entry to the bottom streamer. 
        Evicts old entries if max_logs is reached.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] > {message}"
        
        label = QLabel(log_entry)
        label.setFont(QFont("Consolas", 10))
        label.setStyleSheet("color: #00FF00; background: rgba(0,0,0,100); padding: 2px;")
        
        self.log_layout.addWidget(label)
        self.log_labels.append(label)
        
        if len(self.log_labels) > self.max_logs:
            old_label = self.log_labels.pop(0)
            self.log_layout.removeWidget(old_label)
            old_label.deleteLater()

def launch_hud():
    app = QApplication(sys.argv)
    hud = AxisHUD()
    hud.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    launch_hud()
