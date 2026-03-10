import time
import sys
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont, QColor, QPainter, QPen
import socket
import json

# Додаємо шлях до Atlas_v2 для роботи як окремий процес
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.logger import logger
import logging

class LogBridge(QObject):
    """
    Bridge to safely emit logs and vision data from background threads to the UI thread.
    """
    new_log = pyqtSignal(str)
    vision_update = pyqtSignal(dict) # To pass coordinates and gesture state
    telemetry_update = pyqtSignal(dict) # To pass discovery results

class TelemetryListener(QThread):
    """Listens for UDP packets on port 5005 and sends them to the HUD bridge."""
    data_received = pyqtSignal(dict)

    def run(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("127.0.0.1", 5005))
            while True:
                try:
                    data, addr = sock.recvfrom(4096)
                    telemetry = json.loads(data.decode('utf-8'))
                    self.data_received.emit(telemetry)
                except Exception as e:
                    print(f"HUD Telemetry Receive Error: {e}")
                    time.sleep(1)
        except OSError as e:
            if e.errno == 10048:
                print("⚠️ HUD Telemetry: Port 5005 busy (another HUD instance likely running).")
            else:
                print(f"HUD Telemetry Socket Error: {e}")
        except Exception as e:
            print(f"HUD Telemetry Thread Fatal Error: {e}")

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
    
    Includes:
    - Real-time Log Streamer (Pulse of AXIS)
    - Cyber-Vision Overlay (Aura Mapping)
    """

    def __init__(self, bridge=None):
        """
        Initializes the HUD window with specific flags and log streaming bridge.
        """
        super().__init__()
        logger.info("ui.hud_initializing", version="2.5.0")
        
        # 1. State and Bridge
        self.max_logs = 5
        self.log_labels = []
        self.hand_pos = None # Stores normalized coords (dict)
        self.bridge = bridge if bridge else LogBridge()
        self.bridge.new_log.connect(self.update_log)
        self.bridge.vision_update.connect(self.update_vision)
        self.bridge.telemetry_update.connect(self.update_telemetry_from_dict)
        
        # 2. Window Flags
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool 
        )
        
        # New: Discovery Telemetry State
        self.discovery_data = {
            "ide": "Searching...",
            "gpu": "Detecting...",
            "ram": "---"
        }
        
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
        
        # Main Title
        self.status_label = QLabel("AXIS v2.5 | LOCAL BRAIN")
        self.status_label.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #00BFFF; background: rgba(0,0,0,180); padding: 5px 15px; border-top-left-radius: 10px; border: 1px solid #00BFFF;")
        
        # Discovery Bar
        self.discovery_bar = QLabel("IDE: --- | GPU: --- | RAM: ---")
        self.discovery_bar.setFont(QFont("Consolas", 10))
        self.discovery_bar.setStyleSheet("color: #AAAAAA; background: rgba(0,0,0,150); padding: 5px 15px; border-bottom-left-radius: 10px; border-left: 1px solid #00BFFF; border-bottom: 1px solid #00BFFF;")
        
        self.top_layout.addWidget(self.status_label)
        self.top_layout.addWidget(self.discovery_bar)
        
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
        
        # 6. Start Telemetry Listener (IPC)
        self.telemetry_thread = TelemetryListener()
        self.telemetry_thread.data_received.connect(self.update_telemetry_from_dict)
        self.telemetry_thread.start()
        
        self.showFullScreen()
        logger.info("ui.hud_started", mode="cyber_vision_ready")

    def set_mouse_transparent(self):
        """Pass mouse inputs through the window."""
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput)

    def paintEvent(self, _event):
        """Draws the Cyber-Vision Aura around the detected hand position."""
        if not self.hand_pos or self.hand_pos.get("state") == "IDLE":
            return

        from PyQt6.QtGui import QPainter, QColor, QPen
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Map screen coordinates
        x = int(self.hand_pos["x"])
        y = int(self.hand_pos["y"])
        state = self.hand_pos["state"]

        # Determine Aura Color
        color = QColor(0, 191, 255, 100) # DeepSkyBlue
        if state == "CLICK": color = QColor(255, 0, 0, 150) # Red
        elif state == "PAUSED": color = QColor(255, 255, 0, 150) # Yellow
        elif state == "ACTIVE": color = QColor(0, 255, 0, 150) # Green

        # Draw pulsing circle
        painter.setPen(QPen(color, 2, Qt.PenStyle.SolidLine))
        painter.setBrush(QColor(color.red(), color.green(), color.blue(), 30))
        
        radius = 30 + (int(time.time() * 10) % 10) # Simple pulse
        painter.drawEllipse(x - radius, y - radius, radius * 2, radius * 2)

        # Draw Label
        painter.setPen(QPen(color, 2))
        painter.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        painter.drawText(x + radius + 10, y, f"[{state}]")

    def update_vision(self, data: dict):
        """Receives new vision data and triggers a repaint."""
        self.hand_pos = data
        self.update() # Triggers paintEvent

    def update_telemetry_from_dict(self, data: dict):
        """Receives discovery dictionary and updates HUD labels."""
        ides = data.get("ides", {})
        ide = list(ides.keys())[0] if ides else "None"
        hw = data.get("hardware", {})
        self.update_telemetry(ide=ide, gpu=hw.get("gpu"), ram=hw.get("ram_gb"))

    def update_telemetry(self, ide=None, gpu=None, ram=None):
        """Updates the discovery telemetry bar."""
        if ide: self.discovery_data["ide"] = ide
        if gpu: self.discovery_data["gpu"] = gpu.split(" ")[-1] if " " in gpu else gpu # Shorten name
        if ram: self.discovery_data["ram"] = f"{ram}GB"
        
        text = f"IDE: {self.discovery_data['ide']} | GPU: {self.discovery_data['gpu']} | RAM: {self.discovery_data['ram']}"
        self.discovery_bar.setText(text)

    def update_log(self, message: str):
        """
        Adds a new log entry. If message contains RAG info, uses special styling.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Detect RAG citations for "Iron Man" effect
        is_rag = "rag." in message or "recalled" in message or ".py:" in message
        
        log_entry = f"[{timestamp}] > {message}"
        
        label = QLabel(log_entry)
        label.setFont(QFont("Consolas", 10))
        
        if is_rag:
            label.setStyleSheet("color: #00FFFF; background: rgba(0,255,255,40); padding: 4px; border-left: 3px solid #00FFFF;")
        else:
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
