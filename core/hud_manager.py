import sys
import time
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame
from PyQt6.QtCore import Qt, QTimer, QPoint, QSize, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen

class HUDSignals(QObject):
    """Signals for updating HUD from other threads."""
    status_changed = pyqtSignal(str, str) # status_text, color_hex
    zone_changed = pyqtSignal(int, bool)   # zone_index (0,1,2), is_active
    log_added = pyqtSignal(str)          # log_text
    thinking_state_changed = pyqtSignal(bool) # is_thinking
    confidence_changed = pyqtSignal(float) # gesture confidence (0.0 to 1.0)

class AtlasHUD(QWidget):
    def __init__(self):
        super().__init__()
        self.signals = HUDSignals()
        
        # Window Setup
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        # Screen Size
        screen = QApplication.primaryScreen().size()
        self.setGeometry(0, 0, screen.width(), screen.height())
        
        # State
        self.current_zone = 1
        self.is_active = False
        self.is_thinking = False
        self.gesture_confidence = 0.0
        self.logs = [] # Oстанні 3 дії
        self.pulse_alpha = 0
        self.pulse_direction = 1
        
        # Font Setup
        self.main_font = QFont("Outfit", 14, QFont.Weight.Bold)
        if not self.main_font.exactMatch():
            self.main_font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        
        self.small_font = QFont("Outfit", 10)
        if not self.small_font.exactMatch():
            self.small_font = QFont("Segoe UI", 10)
        
        # Pulse Timer (Smooth)
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self.update_pulse)
        self.pulse_timer.start(33) # ~30 FPS for animation
        
        # Connect Signals
        self.signals.status_changed.connect(self._update_status_ui)
        self.signals.zone_changed.connect(self._update_zone_ui)
        self.signals.log_added.connect(self._update_logs_ui)
        self.signals.thinking_state_changed.connect(self._update_thinking_ui)
        self.signals.confidence_changed.connect(self._update_confidence_ui)
        
        self.init_ui()
        self.show()

    def init_ui(self):
        self.status_text = "SYSTEM IDLE"
        self.status_color = "#00FFFF"
        
    def update_pulse(self):
        if self.is_thinking:
            self.pulse_alpha += 15 * self.pulse_direction
            if self.pulse_alpha >= 255:
                self.pulse_alpha = 255
                self.pulse_direction = -1
            elif self.pulse_alpha <= 50:
                self.pulse_alpha = 50
                self.pulse_direction = 1
            self.update()
        elif self.pulse_alpha > 0:
            self.pulse_alpha = max(0, self.pulse_alpha - 20)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # -- 1. Status Indicator (Top Left) --
        # Glass backing for text (subtle)
        painter.setBrush(QBrush(QColor(0, 0, 0, 40)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(30, 30, 320, 60, 10, 10)
        
        painter.setPen(QPen(QColor(self.status_color), 2))
        painter.setFont(self.main_font)
        painter.drawText(45, 62, f"ATLAS // {self.status_text}")
        
        painter.setPen(QPen(QColor(255, 255, 255, 120), 1))
        painter.setFont(QFont(self.small_font.family(), 8))
        painter.drawText(45, 78, f"CORE KERNEL V2.4 // {time.strftime('%H:%M:%S')}")

        # -- 2. Log Stream (Top Right) --
        log_x = w - 350
        painter.setBrush(QBrush(QColor(0, 0, 0, 40)))
        painter.drawRoundedRect(log_x - 10, 30, 320, 100, 10, 10)
        
        painter.setFont(self.small_font)
        for i, log in enumerate(reversed(self.logs)):
            alpha = 255 - (i * 70)
            painter.setPen(QPen(QColor(200, 255, 255, max(0, alpha))))
            painter.drawText(log_x, 60 + (i * 25), f"▶ {log}")

        # -- 3. Thinking Indicator (Center Top) --
        if self.is_thinking or self.pulse_alpha > 0:
            center_x = int(w / 2)
            # Pulse Point
            painter.setBrush(QBrush(QColor(0, 255, 255, self.pulse_alpha)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(center_x, 40), 5, 5)
            
            # Radial Glow
            for r in range(1, 4):
                painter.setPen(QPen(QColor(0, 255, 255, int(self.pulse_alpha / (r*3))), 1))
                painter.drawEllipse(QPoint(center_x, 40), 5 + r*5, 5 + r*5)

        # -- 4. Zone Visualizer (Bottom) --
        bar_w = 450
        bar_h = 6
        bar_x = int((w - bar_w) / 2)
        bar_y = h - 50
        
        # Main Bar Background
        painter.setBrush(QBrush(QColor(255, 255, 255, 20)))
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 3, 3)
        
        # Zone Highlight (L, C, R)
        if self.current_zone is not None:
            zone_w = int(bar_w / 3)
            # Smooth transition x could be added, but for now fixed
            highlight_x = bar_x + (self.current_zone * zone_w)
            
            color = QColor(0, 255, 255, 255 if self.is_active else 100)
            painter.setBrush(QBrush(color))
            # Neon Glow for Active
            if self.is_active:
                for glow in range(1, 5):
                    painter.setPen(QPen(QColor(0, 255, 255, int(150 / glow)), 1))
                    painter.drawRoundedRect(highlight_x - glow, bar_y - glow, zone_w + glow*2, bar_h + glow*2, 3, 3)
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(highlight_x, bar_y, zone_w, bar_h, 3, 3)
            
            # Zone Text
            zones = ["BROWSER", "GESTURES", "MEDIA"]
            painter.setFont(QFont(self.small_font.family(), 9, QFont.Weight.Bold))
            painter.setPen(QPen(color))
            painter.drawText(highlight_x + int(zone_w/2) - 30, bar_y - 12, zones[self.current_zone])

        # -- 5. Gesture Confidence Bar --
        if self.gesture_confidence > 0:
            conf_w = 200
            conf_h = 4
            conf_x = int((w - conf_w) / 2)
            conf_y = bar_y - 40
            
            # BG
            painter.setBrush(QBrush(QColor(255, 255, 255, 30)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(conf_x, conf_y, conf_w, conf_h, 2, 2)
            
            # Progress
            fill_w = int(conf_w * self.gesture_confidence)
            painter.setBrush(QBrush(QColor(0, 255, 255, 200)))
            painter.drawRoundedRect(conf_x, conf_y, fill_w, conf_h, 2, 2)
            
            # Text
            painter.setFont(self.small_font)
            painter.setPen(QColor(0, 255, 255))
            painter.drawText(conf_x + conf_w + 10, conf_y + 5, f"{int(self.gesture_confidence * 100)}%")

    def _update_status_ui(self, text, color_hex):
        self.status_text = text.upper()
        self.status_color = color_hex
        self.update()
        
    def _update_zone_ui(self, zone_index, is_active):
        self.current_zone = zone_index
        self.is_active = is_active
        self.update()
        
    def _update_logs_ui(self, text):
        self.logs.append(text)
        if len(self.logs) > 3:
            self.logs.pop(0)
        self.update()
        
    def _update_thinking_ui(self, state):
        self.is_thinking = state
        self.update()

    def _update_confidence_ui(self, value):
        self.gesture_confidence = value
        self.update()

def run_hud(core_instance=None):
    """Entry point to run HUD in a thread-safe way."""
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    hud = AtlasHUD()
    
    # Store reference in core if provided
    if core_instance:
        core_instance.hud_window = hud
        
    app.exec()

if __name__ == "__main__":
    run_hud()
