import os
import sys
import json
import socket
import logging
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                             QLineEdit, QDialog, QFrame, QHBoxLayout)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QPoint, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QPixmap, QFont, QColor, QPainter

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.logger import logger

class CommandDialog(QDialog):
    """Mini-terminal for the robot."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setStyleSheet("background: #121212; border: 2px solid #00F2FF; border-radius: 10px;")
        self.layout = QVBoxLayout(self)
        self.input = QLineEdit()
        self.input.setPlaceholderText("How can I help, Commander?")
        self.input.setStyleSheet("color: #00F2FF; background: #000; border: none; font: 10pt 'Consolas';")
        self.input.returnPressed.connect(self.accept)
        self.layout.addWidget(self.input)
        self.setFixedSize(300, 50)

class LogBridge(QObject):
    new_log = pyqtSignal(str)

class TelemetryListener(QThread):
    data_received = pyqtSignal(dict)
    def run(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("127.0.0.1", 5005))
            while True:
                data, _ = sock.recvfrom(4096)
                self.data_received.emit(json.loads(data.decode('utf-8')))
        except Exception: pass

class AxisMascot(QWidget):
    """
    AXIS Companion Robot (v3.8.0).
    A floating, interactive mascot that moves and reacts to tasks.
    """
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(200, 200)
        
        # 1. UI Components
        self.layout = QVBoxLayout(self)
        self.label = QLabel(self)
        # Fix path (project_root is already Atlas_v2 based on the 2nd level up)
        asset_path = os.path.join(project_root, "assets", "mascot.png")
        self.pixmap = QPixmap(asset_path)
        if self.pixmap.isNull():
            print(f"❌ [STATUS]: Image failed to load at {asset_path}")
        self.label.setPixmap(self.pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)
        
        # Speech Bubble (Hidden by default)
        self.bubble = QLabel("AXIS ONLINE", self)
        self.bubble.setStyleSheet("background: rgba(0, 242, 255, 180); color: black; border-radius: 10px; padding: 5px; font: 8pt 'Consolas';")
        self.bubble.setGeometry(20, 0, 160, 40)
        self.bubble.hide()
        
        # 2. Animations
        self.bob_anim = QPropertyAnimation(self.label, b"pos")
        self.bob_anim.setDuration(2000)
        self.bob_anim.setStartValue(QPoint(0, 20))
        self.bob_anim.setEndValue(QPoint(0, 0))
        self.bob_anim.setLoopCount(-1)
        self.bob_anim.start()
        
        # 3. State & Logging
        self.bridge = LogBridge()
        self.bridge.new_log.connect(self.on_event)
        
        # 4. Drag Logic
        self.old_pos = None

        self.move_to_corner()
        self.show()

    def move_to_corner(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - 220, screen.height() - 250)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseDoubleClickEvent(self, _event):
        """Open command dialog on double click."""
        dialog = CommandDialog(self)
        if dialog.exec():
            cmd = dialog.input.text()
            self.send_to_axis(cmd)

    def send_to_axis(self, command):
        """Send command to the main listener via local file or UDP if needed."""
        # For now, just show a speech bubble
        self.speak(f"Executing: {command}")
        # In a real setup, we'd send this to the orchestrator or main loop

    def speak(self, text):
        self.bubble.setText(text[:50] + "..." if len(text) > 50 else text)
        self.bubble.show()
        QTimer.singleShot(4000, self.bubble.hide)

    def on_event(self, message):
        """React to logs."""
        if "rag." in message.lower() or "search" in message.lower():
            self.speak("Searching memory...")
        elif "write" in message.lower() or "file" in message.lower():
            self.speak("Modifying files!")
        elif "error" in message.lower():
            self.speak("⚠️ Security Alert!")

def launch_mascot():
    print(f"[UI] Mascot process started. Asset path: {os.path.join(project_root, 'Atlas_v2', 'assets', 'mascot.png')}")
    if not os.path.exists(os.path.join(project_root, "Atlas_v2", "assets", "mascot.png")):
        print(f"❌ [ERROR]: mascot.png not found at {os.path.join(project_root, 'Atlas_v2', 'assets')}")
    
    app = QApplication(sys.argv)
    try:
        mascot = AxisMascot()
        print("[UI] Mascot window (v3.8.1) deployed. Watching for Commander's input...")
    except Exception as e:
        print(f"❌ [UI ERROR]: Failed to create Mascot window: {e}")
        return

    # Bridge to logging
    class Handler(logging.Handler):
        def emit(self, record):
            mascot.bridge.new_log.emit(record.getMessage())
    
    handler = Handler()
    logging.getLogger().addHandler(handler)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    launch_mascot()
