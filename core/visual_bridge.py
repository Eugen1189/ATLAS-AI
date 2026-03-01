"""
Visual Bridge — зв'язок Atlas (Мозок) ↔ Візуальний рушій (Голограма).

Протоколи:
- OSC (UDP): для TouchDesigner, Unity, Unreal, Max/MSP — мінімальна затримка.
- WebSocket: для веб-клієнтів (Three.js, Flet) — постійне двостороннє з'єднання.

Адреси OSC (узгоджені з клієнтом):
  /atlas/hand/gesture  s  — "idle" | "ready" | "action" | "scroll" | "raised_hand"
  /atlas/hand/x        f   — нормалізована X [0..1]
  /atlas/hand/y        f   — нормалізована Y [0..1]
  /atlas/visual/color  s   — колір для PoC: "red" | "yellow" | "green" | "blue"
  /atlas/zone/clicked  s   — id зони, коли курсор у зоні і жест action (Крок 3)
"""

import threading
import asyncio
import json

# OSC (optional)
try:
    from pythonosc.udp_client import SimpleUDPClient
    HAS_OSC = True
except ImportError:
    HAS_OSC = False

# WebSocket (optional)
try:
    import websockets
    HAS_WS = True
except ImportError:
    HAS_WS = False


# Маппінг стан рук → колір для PoC (крок 1)
GESTURE_TO_COLOR = {
    "idle": "red",
    "ready": "yellow",
    "action": "green",
    "scroll": "blue",
    "raised_hand": "cyan",
}


class VisualBridge:
    """
    Відправляє жести та координати руки в візуальний рушій по OSC та/або WebSocket.
    Потокобезпечно: виклики send_* можна робити з будь-якого потоку.
    """

    def __init__(self, osc_host="127.0.0.1", osc_port=9000, ws_port=8766, enabled=True):
        self.osc_host = osc_host
        self.osc_port = osc_port
        self.ws_port = ws_port
        self.enabled = enabled and (HAS_OSC or HAS_WS)

        self._osc_client = None
        self._ws_clients = set()
        self._ws_server = None
        self._ws_loop = None
        self._ws_thread = None
        self._lock = threading.Lock()
        # Інтерактивні зони (Крок 3): один "клік" за один жест action у зоні
        self._zones = []
        self._zones_path = None
        self._action_zone_fired = None  # id зони, для якої вже надіслано клік цієї "action"-сесії
        self._zone_click_callback = None

        if self.enabled and HAS_OSC:
            try:
                self._osc_client = SimpleUDPClient(self.osc_host, self.osc_port)
                print(f"📡 [VISUAL] OSC client: {self.osc_host}:{self.osc_port}")
            except Exception as e:
                print(f"⚠️ [VISUAL] OSC init failed: {e}")
                self._osc_client = None

        if self.enabled and HAS_WS and self.ws_port:
            self._start_ws_server()
        else:
            if not HAS_WS:
                print("⚠️ [VISUAL] WebSocket skipped: 'websockets' not installed.")

    def _start_ws_server(self):
        def run_ws():
            self._ws_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._ws_loop)
            self._ws_loop.run_until_complete(self._serve_ws())

        self._ws_thread = threading.Thread(target=run_ws, daemon=True)
        self._ws_thread.start()
        print(f"📡 [VISUAL] WebSocket server: 0.0.0.0:{self.ws_port}")

    async def _serve_ws(self):
        async def handler(websocket):
            self._ws_clients.add(websocket)
            try:
                await websocket.wait_closed()
            finally:
                self._ws_clients.discard(websocket)

        try:
            async with websockets.serve(handler, "0.0.0.0", self.ws_port, ping_interval=20, ping_timeout=10):
                await asyncio.Future()
        except Exception as e:
            print(f"⚠️ [VISUAL] WebSocket server error: {e}")

    def send_gesture(self, gesture: str):
        """Відправити поточний жест (idle, ready, action, scroll, raised_hand)."""
        if not self.enabled:
            return
        gesture = (gesture or "idle").lower()
        color = GESTURE_TO_COLOR.get(gesture, "red")

        if self._osc_client:
            try:
                self._osc_client.send_message("/atlas/hand/gesture", gesture)
                self._osc_client.send_message("/atlas/visual/color", color)
            except Exception as e:
                pass  # не засмічувати лог при вимкненому приймачі

        self._broadcast_ws({"type": "gesture", "gesture": gesture, "color": color})

    def send_hand_position(self, x_norm: float, y_norm: float):
        """Нормалізовані координати руки [0..1]. X — горизонталь, Y — вертикаль."""
        if not self.enabled:
            return
        x_norm = max(0.0, min(1.0, float(x_norm)))
        y_norm = max(0.0, min(1.0, float(y_norm)))

        if self._osc_client:
            try:
                self._osc_client.send_message("/atlas/hand/x", x_norm)
                self._osc_client.send_message("/atlas/hand/y", y_norm)
            except Exception:
                pass

        self._broadcast_ws({"type": "hand", "x": x_norm, "y": y_norm})

    def send_system_event(self, event_type: str, data: any = None):
        """
        Відправити загальну системну подію (напр. 'app_launch', 'task_done', 'error').
        
        Args:
            event_type: Тип події
            data: Додаткові дані або опис
        """
        if not self.enabled:
            return
            
        if self._osc_client:
            try:
                self._osc_client.send_message(f"/atlas/system/{event_type}", str(data) if data else "")
            except Exception:
                pass
                
        self._broadcast_ws({"type": "system", "event": event_type, "data": data})

    def set_zone_click_callback(self, callback):
        """Callback(zone_id) викликається при кліку по зоні (жест action у межах зони)."""
        self._zone_click_callback = callback

    def _load_zones(self):
        try:
            import config
            path = getattr(config, "VISUAL_ZONES_PATH", None)
            if path and path.exists():
                if path != self._zones_path:
                    self._zones_path = path
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._zones = data.get("zones") or []
        except Exception:
            self._zones = []

    def _point_in_zone(self, x: float, y: float, zone: dict) -> bool:
        return (
            zone["xmin"] <= x <= zone["xmax"]
            and zone["ymin"] <= y <= zone["ymax"]
        )

    def check_zones_and_click(self, x_norm: float, y_norm: float, gesture: str):
        """
        Крок 3: якщо жест = action і курсор у інтерактивній зоні — один раз за сесію
        надсилаємо /atlas/zone/clicked <zone_id> та викликаємо zone_click_callback.
        """
        if not self.enabled:
            return
        x_norm = max(0.0, min(1.0, float(x_norm)))
        y_norm = max(0.0, min(1.0, float(y_norm)))
        gesture = (gesture or "idle").lower()

        if gesture != "action":
            self._action_zone_fired = None
            return

        self._load_zones()
        if not self._zones:
            return

        for zone in self._zones:
            if not self._point_in_zone(x_norm, y_norm, zone):
                continue
            zone_id = zone.get("id", "")
            if zone_id == self._action_zone_fired:
                return
            self._action_zone_fired = zone_id
            if self._osc_client:
                try:
                    self._osc_client.send_message("/atlas/zone/clicked", zone_id)
                except Exception:
                    pass
            self._broadcast_ws({"type": "zone_clicked", "zone_id": zone_id})
            if self._zone_click_callback:
                try:
                    self._zone_click_callback(zone_id)
                except Exception:
                    pass
            return

    def send_raw(self, address: str, *values):
        """Відправити довільне OSC-повідомлення (для розширення)."""
        if not self.enabled or not self._osc_client:
            return
        try:
            self._osc_client.send_message(address, list(values) if len(values) != 1 else values[0])
        except Exception:
            pass

    async def _do_broadcast(self, msg: str):
        for ws in list(self._ws_clients):
            try:
                await ws.send(msg)
            except Exception:
                pass

    def _broadcast_ws(self, payload: dict):
        if not HAS_WS or not self._ws_loop:
            return
        msg = json.dumps(payload)
        try:
            asyncio.run_coroutine_threadsafe(self._do_broadcast(msg), self._ws_loop)
        except Exception:
            pass

    def close(self):
        """Зупинити WebSocket-сервер (OSC клієнт не потребує закриття)."""
        if self._ws_loop and self._ws_server:
            self._ws_loop.call_soon_thread_safe(self._ws_server.close)


# Глобальний екземпляр (ініціалізується з config при першому використанні)
_bridge_instance = None


def get_visual_bridge():
    global _bridge_instance
    if _bridge_instance is None:
        try:
            import config
            enabled = getattr(config, "VISUAL_BRIDGE_ENABLED", True)
            osc_host = getattr(config, "VISUAL_OSC_HOST", "127.0.0.1")
            osc_port = getattr(config, "VISUAL_OSC_PORT", 9000)
            ws_port = getattr(config, "VISUAL_WS_PORT", 8766)
            _bridge_instance = VisualBridge(
                osc_host=osc_host,
                osc_port=osc_port,
                ws_port=ws_port,
                enabled=enabled,
            )
        except Exception as e:
            print(f"⚠️ [VISUAL] Bridge init failed: {e}")
            _bridge_instance = VisualBridge(enabled=False)
    return _bridge_instance
