import time
import sys
import os
import socket
import json
import logging
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                             QHBoxLayout, QWidget, QFrame, QScrollArea)
from PyQt6.QtCore import (Qt, pyqtSignal, QObject, QThread, QPropertyAnimation, 
                          QTimer, QPointF)
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QRadialGradient

# Setup Paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.logger import logger

class LogBridge(QObject):
    new_log = pyqtSignal(str)
    telemetry_update = pyqtSignal(dict)

class TelemetryListener(QThread):
    data_received = pyqtSignal(dict)
    def run(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("127.0.0.1", 5005))
            while True:
                data, addr = sock.recvfrom(4096)
                self.data_received.emit(json.loads(data.decode('utf-8')))
        except Exception: pass

class HUDLogHandler(logging.Handler):
    def __init__(self, bridge: LogBridge):
        super().__init__()
        self.bridge = bridge
    def emit(self, record):
        try:
            msg = self.format(record)
            self.bridge.new_log.emit(msg)
        except Exception: pass

# --- ADVANCED UI COMPONENTS (v3.7.5 Obsidian Hub) ---

class BrainOrb(QWidget):
    """Pulsing core of AXIS consciousness."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(120, 120)
        self.pulse = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_pulse)
        self.timer.start(50)

    def update_pulse(self):
        self.pulse = (self.pulse + 2) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        center = rect.center()
        import math
        
        # Scaling pulse
        scale = 0.8 + 0.1 * math.sin(math.radians(self.pulse))
        radius = min(rect.width(), rect.height()) / 2.5 * scale
        
        # Outer Glow
        grad = QRadialGradient(QPointF(center), radius * 1.5)
        grad.setColorAt(0, QColor(0, 242, 255, 60))
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(center), radius * 1.5, radius * 1.5)
        
        # Core Orb
        painter.setPen(QPen(QColor(0, 242, 255, 200), 2))
        painter.setBrush(QColor(10, 10, 10, 255))
        painter.drawEllipse(QPointF(center), radius, radius)
        
        # Topographic Waves
        painter.setPen(QPen(QColor(0, 242, 255, 100), 1))
        for i in range(1, 4):
            wave_r = radius * (0.3 + 0.2 * i) * (0.9 + 0.1 * math.sin(math.radians(self.pulse + i*45)))
            painter.drawEllipse(QPointF(center), wave_r, wave_r)

class ModularCard(QFrame):
    """Deep Matte Black card with Neon border."""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            ModularCard {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, 
                                          stop:0 #121212, stop:1 #0A0A0A);
                border: 1px solid #1A1A1A;
                border-top: 2px solid #00F2FF;
                border-radius: 4px;
            }
        """)
        self.layout = QVBoxLayout(self)
        
        # Header
        self.header = QLabel(title.upper())
        self.header.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self.header.setStyleSheet("color: #00F2FF; letter-spacing: 2px;")
        self.layout.addWidget(self.header)
        self.layout.addSpacing(5)

class AxisHUD(QMainWindow):
    """
    AXIS Command Center (v3.7.5 - Obsidian Standard).
    New Modular architecture replaces the transparent overlay.
    """
    def __init__(self, bridge=None):
        super().__init__()
        logger.info("ui.hud_obsidian_init", mode="modular_control_2026")
        
        # 1. State
        self.bridge = bridge if bridge else LogBridge()
        self.bridge.new_log.connect(self.update_log_stream)
        self.bridge.telemetry_update.connect(self.process_telemetry)
        
        # 2. Window Setup (Non-Transparent Solid Hub)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(450, 700)
        self.setStyleSheet("background: #0D0D0D; border: 1px solid #1A1A1A;")
        
        # 3. Main UI Layout
        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.layout = QVBoxLayout(self.central)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(15)
        
        # --- Top Section: Status & Mission ---
        self.top_card = ModularCard("Mission Control")
        self.status = QLabel("AXIS ONLINE | STANDBY")
        self.status.setFont(QFont("Consolas", 10))
        self.status.setStyleSheet("color: #00FF00;")
        self.top_card.layout.addWidget(self.status)
        
        self.telemetry = QLabel("HW: --- | RAG: 0 CHUNKS")
        self.telemetry.setFont(QFont("Consolas", 8))
        self.telemetry.setStyleSheet("color: #666666;")
        self.top_card.layout.addWidget(self.telemetry)
        self.layout.addWidget(self.top_card)
        
        # --- Middle Section: Brain & Focus ---
        self.mid_row = QHBoxLayout()
        
        # Brain Core Card
        self.brain_card = ModularCard("Internal State")
        self.brain_orb = BrainOrb()
        self.brain_card.layout.addWidget(self.brain_orb, alignment=Qt.AlignmentFlag.AlignCenter)
        self.mid_row.addWidget(self.brain_card, 2)
        
        # Anatomy Card (File focus)
        self.file_card = ModularCard("Active Focus")
        self.focus_list = QLabel("No file in focus")
        self.focus_list.setWordWrap(True)
        self.focus_list.setFont(QFont("Consolas", 8))
        self.focus_list.setStyleSheet("color: #AAA;")
        self.file_card.layout.addWidget(self.focus_list)
        self.mid_row.addWidget(self.file_card, 1)
        
        self.layout.addLayout(self.mid_row)
        
        # --- Bottom Section: Log Stream ---
        self.log_card = ModularCard("Command Stream")
        self.log_area = QScrollArea()
        self.log_area.setWidgetResizable(True)
        self.log_area.setStyleSheet("background: transparent; border: none;")
        self.log_widget = QWidget()
        self.log_layout = QVBoxLayout(self.log_widget)
        self.log_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.log_area.setWidget(self.log_widget)
        self.log_card.layout.addWidget(self.log_area)
        self.layout.addWidget(self.log_card, 3)
        
        # 4. IPC (UDP Telemetry)
        self.telemetry_thread = TelemetryListener()
        self.telemetry_thread.data_received.connect(self.process_telemetry)
        self.telemetry_thread.start()
        
        # 5. Global Logging Integration
        handler = HUDLogHandler(self.bridge)
        handler.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger().addHandler(handler)
        
        # Finalize
        self.move_to_corner()
        self.show()

    def move_to_corner(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - self.width() - 20, 40)

    def process_telemetry(self, data):
        hw = data.get("hardware", {})
        rag = data.get("rag_stats", {}).get("chunks_total", "0")
        self.telemetry.setText(f"GPU: {hw.get('gpu', '---')} | RAG: {rag} CHUNKS")
        
    def update_log_stream(self, message):
        msg_clean = message[:120] + "..." if len(message) > 120 else message
        label = QLabel(f"> {msg_clean}")
        label.setFont(QFont("Consolas", 9))
        
        # Style based on content
        color = "#00FF00" # Normal
        if "error" in message.lower() or "fail" in message.lower(): color = "#FF0000"
        if "rag." in message.lower(): 
            color = "#00F2FF"
            self.brain_orb.timer.setInterval(20) # Faster pulse for RAG
            QTimer.singleShot(2000, lambda: self.brain_orb.timer.setInterval(50))
            
        label.setStyleSheet(f"color: {color}; border-left: 1px solid {color}; padding-left: 5px;")
        self.log_layout.insertWidget(0, label)
        
        # Auto-focus detection
        if "/" in message and ("." in message or "src" in message):
            self.focus_list.setText(message.split(" ")[-1])

def launch_hud():
    app = QApplication(sys.argv)
    hud = AxisHUD()
    sys.exit(app.exec())

if __name__ == "__main__":
    launch_hud()
