import cv2
import numpy as np
import mediapipe as mp
import pyautogui
import threading
import time
import math
import random
import queue
from collections import deque

class VisionManager:
    """
    VisionManager - Керування комп'ютером за допомогою жестів.
    
    Архітектура (Thread Decoupling):
    1. Capture Thread: Зчитування кадрів з камери (Max FPS).
    2. Processing Thread: MediaPipe + Логіка жестів + FSM.
    3. Action Thread: Виконання команд (PyAutoGUI).
    """
    
    def __init__(self, camera_index=0, ui_callback=None, router_callback=None, hud_callback=None):
        self.camera_index = camera_index
        self.ui_callback = ui_callback
        self.router_callback = router_callback  # callable(intent: str) for zone intents
        self.hud_callback = hud_callback        # callable(zone: int, is_active: bool)
        self.is_running = False
        
        # Helper for EMA
        self.prev_lm_list = []
        self.ema_alpha = 0.2 # Smoothing factor (Requested alpha=0.2)
        
        # Threads
        self.capture_thread = None
        self.process_thread = None
        self.action_thread = None
        
        # Queues for Thread Communication
        self.frame_queue = queue.Queue(maxsize=1) # Keep only latest frame
        self.action_queue = queue.Queue(maxsize=24) # Буфер для дій (CLICK не губити при навантаженні)
        
        # MediaPipe Hands
        self.mp_hands = None
        self.hands = None
        self.mp_draw = None
        
        # Screen config
        self.screen_w, self.screen_h = pyautogui.size()
        self.cam_w, self.cam_h = 1280, 720
        
        # Smoothing (Moving Average)
        self.prev_x, self.prev_y = 0, 0
        self.smooth_x, self.smooth_y = 0, 0
        self.last_cursor_x, self.last_cursor_y = 0, 0
        self.last_pinch_state = False
        
        # State
        self.state = "IDLE" # IDLE, READY, ACTION, SCROLL
        self.is_dragging = False
        self.last_zoom_dist = 0
        
        # Logic Helpers
        self.prev_index_x = 0
        self.prev_index_y = 0
        self._grabbed_announced = False

        # Клік vs перетягування: короткий pinch = клік, довгий/з рухом = drag
        self.pinch_start_time = 0.0
        self.pinch_start_x = 0
        self.pinch_start_y = 0
        self.pinch_is_drag = False
        self.last_click_time = 0.0
        self.last_click_x = 0
        self.last_click_y = 0
        self.CLICK_MIN_DURATION = 0.05   # мін. тривалість pinch для кліку (відсікає випадкові спайки)
        self.CLICK_MAX_DURATION = 0.42   # макс. тривалість pinch = клік (довше = drag)
        self.CLICK_MAX_MOVE = 45         # макс. рух у пікселях для кліку (більше = drag)
        self.DOUBLE_CLICK_INTERVAL = 0.5
        self.DOUBLE_CLICK_MAX_DIST = 60
        self.PINCH_ENTER = 68            # dist_pinch < це → входимо в ACTION (pinch)
        self.PINCH_LEAVE = 85            # у ACTION: dist_pinch > це → виходимо в READY (гістерезис)

        # Шорткати-жести: тільки при утриманні пози HOLD_SEC (за замовчуванням вимкнені)
        self._gesture_hold_start = {}    # id жесту -> time входу в пози
        self._shortcut_cooldown = 2.5
        try:
            import config
            self._hold_sec = getattr(config, "VISUAL_GESTURE_HOLD_SEC", 1.2)
            self._enable_screenshot = getattr(config, "VISUAL_GESTURE_SCREENSHOT", False)
            self._enable_media = getattr(config, "VISUAL_GESTURE_MEDIA", False)
            self._enable_show_desktop = getattr(config, "VISUAL_GESTURE_SHOW_DESKTOP", False)
            self._enable_lock_pc = getattr(config, "VISUAL_GESTURE_LOCK_PC", False)
        except Exception:
            self._hold_sec = 1.2
            self._enable_screenshot = self._enable_media = self._enable_show_desktop = self._enable_lock_pc = False

        # Super Powers & VFX (cooldown після спрацювання шорткатів)
        self.last_screenshot_time = 0
        self.last_media_time = 0
        self.last_snap_time = 0
        self.last_shield_time = 0
        self.particles = []
        self.scan_start_time = 0
        self.last_scan_pos = (0, 0)
        
        # Preview State
        self.show_preview = True

        # Visual Bridge (Atlas → OSC/WebSocket для голограми)
        self.visual_bridge = None
        self._last_bridge_gesture = None

        # Режим "тихий UI" — не оновлювати статус з жестів (усуває мерехтіння під час руху)
        try:
            import config
            self._quiet_ui = getattr(config, "VISUAL_QUIET_UI", True)
        except Exception:
            self._quiet_ui = True

        # Віртуальні зони (0–33%, 33–66%, 66–100% ширини кадру)
        try:
            import config as _cfg
            self._zone_dwell_sec = getattr(_cfg, "VISUAL_GESTURE_HOLD_SEC", 1.2)
        except Exception:
            self._zone_dwell_sec = 1.2
        self._zone_enter_time = None
        self._current_zone = None
        self._zone_fired_at_enter_time = None
        self._zone_cooldown = 2.5
        self.is_active = False
        self._no_hand_frames = 0
        
        # Deques for gesture stability (20 frames for smoother voting)
        self._gesture_history = deque(maxlen=20)
        self._gesture_frame_counter = 0 # For 15-frame hold verification
        self._last_verified_gesture = None
        self._gesture_confidence = 0.0

        print("👁️ [VISION] VisionManager Initialized (Multi-threaded)")

    def _init_resources(self):
        try:
            self.mp_hands = mp.solutions.hands
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.8,
                min_tracking_confidence=0.7
            )
            self.mp_draw = mp.solutions.drawing_utils
            return True
        except Exception as e:
            print(f"❌ [VISION] Failed to load MediaPipe: {e}")
            return False

    def start(self):
        if self.is_running: return

        try:
            from core.visual_bridge import get_visual_bridge
            self.visual_bridge = get_visual_bridge()
        except Exception as e:
            print(f"⚠️ [VISION] Visual bridge unavailable: {e}")
            self.visual_bridge = None

        if not self._init_resources():
            return

        self.is_running = True
        
        # Start Threads
        self.capture_thread = threading.Thread(target=self._capture_worker, daemon=True)
        self.process_thread = threading.Thread(target=self._processing_worker, daemon=True)
        self.action_thread = threading.Thread(target=self._action_worker, daemon=True)
        
        self.capture_thread.start()
        self.process_thread.start()
        self.action_thread.start()
        
        print("👁️ [VISION] Threads started: Capture, Processing, Action")

    def stop(self):
        self.is_running = False
        
        # Wait for threads to finish (optional, usually daemon threads die)
        if self.capture_thread: self.capture_thread.join(timeout=1)
        if self.process_thread: self.process_thread.join(timeout=1)
        if self.action_thread: self.action_thread.join(timeout=1)
            
        if self.hands:
             self.hands.close()
        cv2.destroyAllWindows()
        print("🛑 [VISION] Camera stopped")

    # --- THREAD 1: CAPTURE ---
    def _capture_worker(self):
        print(f"📷 [CAPTURE] Connecting to camera index: {self.camera_index}...")
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        
        # Fallback Logic
        if not cap.isOpened():
             fallbacks = [0, 1, 2]
             if self.camera_index in fallbacks: fallbacks.remove(self.camera_index)
             for idx in fallbacks:
                 cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                 if cap.isOpened():
                     print(f"✅ [CAPTURE] Connected to fallback: {idx}")
                     break
        
        if not cap.isOpened():
            print("❌ [CAPTURE] No camera found")
            self.is_running = False
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cam_w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cam_h)
        
        while self.is_running:
            success, frame = cap.read()
            if success:
                # Drop old frame if queue is full (keep fresh)
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait() 
                    except queue.Empty:
                        pass
                
                self.frame_queue.put(frame)
            else:
                time.sleep(0.1)
                
        cap.release()
        cap.release()
        print("📷 [CAPTURE] Thread stopped")

    def get_latest_frame(self):
        """Returns the current frame as a PIL Image (RGB) for analysis."""
        if not self.frame_queue.empty():
            try:
                # Peek at the queue without removing if we want to share it,
                # but queue.Queue doesn't support peek easily.
                # However, since processing removes it, we might need a separate 'latest_frame' variable.
                # Let's rely on a thread-safe variable updated by processing worker.
                if hasattr(self, 'current_processed_frame') and self.current_processed_frame is not None:
                     # Convert BGR (OpenCV) to RGB (PIL)
                     import cv2
                     from PIL import Image
                     img_rgb = cv2.cvtColor(self.current_processed_frame, cv2.COLOR_BGR2RGB)
                     return Image.fromarray(img_rgb)
            except Exception as e:
                print(f"❌ [VISION] Error getting frame: {e}")
        return None

    # --- THREAD 2: PROCESSING (BRAIN) ---
    def _processing_worker(self):
        cv2.namedWindow("Atlas Vision", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Atlas Vision", 640, 360)
        
        while self.is_running:
            try:
                frame = self.frame_queue.get(timeout=1)
            except queue.Empty:
                continue
                
            # Mirror & Color
            img = cv2.flip(frame, 1)
            # Store for external access (thread-safe assignment)
            self.current_processed_frame = img.copy() 
            
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # MediaPipe
            results = self.hands.process(img_rgb)
            
            lm_list = []
            if results.multi_hand_landmarks:
                self._no_hand_frames = 0 # Скидаємо лічильник кадрів без рук
                for hand_lms in results.multi_hand_landmarks:
                    # --- EMA SMOOTHING ---
                    current_lm_list = []
                    h, w, c = img.shape
                    for id, lm in enumerate(hand_lms.landmark):
                         cx, cy = int(lm.x * w), int(lm.y * h)
                         current_lm_list.append([id, cx, cy])
                    
                    if not self.prev_lm_list:
                        self.prev_lm_list = current_lm_list
                    
                    # Apply Smooth
                    smoothed_list = []
                    for i in range(len(current_lm_list)):
                        prev_cx, prev_cy = self.prev_lm_list[i][1], self.prev_lm_list[i][2]
                        curr_cx, curr_cy = current_lm_list[i][1], current_lm_list[i][2]
                        
                        smooth_cx = int(self.ema_alpha * curr_cx + (1 - self.ema_alpha) * prev_cx)
                        smooth_cy = int(self.ema_alpha * curr_cy + (1 - self.ema_alpha) * prev_cy)
                        smoothed_list.append([i, smooth_cx, smooth_cy])
                    
                    self.prev_lm_list = smoothed_list
                    lm_list = smoothed_list # Use smoothed for logic

                    # --- ВІРТУАЛЬНІ ЗОНИ (3 Рівні Зони: 0-33%, 33-66%, 66-100%) ---
                    h, w = img.shape[:2]
                    raw_ix = lm_list[8][1]
                    raw_iy = lm_list[8][2]
                    
                    # 1. EMA Smoothing for Coordinates (alpha=0.2)
                    self.smooth_x = int(self.ema_alpha * raw_ix + (1 - self.ema_alpha) * self.smooth_x)
                    self.smooth_y = int(self.ema_alpha * raw_iy + (1 - self.ema_alpha) * self.smooth_y)
                    ix, iy = self.smooth_x, self.smooth_y
                    
                    # Update landmarks for following logic to use smoothed values
                    lm_list[8] = (8, ix, iy)
                    
                    # 2. Hysteresis for Virtual Zones (+/- 20px)
                    # Boundaries: w/3 (~0.33) and 2*w/3 (~0.66)
                    left_bound = w / 3
                    right_bound = 2 * w / 3
                    hysteresis = 20
                    
                    if self._current_zone == 0: # Already Left
                        if ix > left_bound + hysteresis:
                            zone = 1 if ix < right_bound else 2
                        else:
                            zone = 0
                    elif self._current_zone == 1: # Already Center
                        if ix < left_bound - hysteresis:
                            zone = 0
                        elif ix > right_bound + hysteresis:
                            zone = 2
                        else:
                            zone = 1
                    elif self._current_zone == 2: # Already Right
                        if ix < right_bound - hysteresis:
                            zone = 0 if ix < left_bound else 1
                        else:
                            zone = 2
                    else: # Initial
                        if ix < left_bound: zone = 0
                        elif ix < right_bound: zone = 1
                        else: zone = 2

                    now = time.time()
                    if zone != self._current_zone:
                        self._current_zone = zone
                        self._zone_enter_time = now
                        self._zone_fired_at_enter_time = None
                    
                    dwell = (now - self._zone_enter_time) if self._zone_enter_time else 0
                    
                    # Activation logic
                    if zone == 1 and dwell >= 0.5 and not self.is_active:
                        self.is_active = True
                        if self.hud_callback:
                            self.hud_callback(zone, True, self._gesture_confidence)
                        if not self._quiet_ui and self.ui_callback:
                            self.ui_callback("🔓 System Active")

                    # HUD Update for zone changes (now includes confidence)
                    if self.hud_callback:
                        self.hud_callback(zone, self.is_active, self._gesture_confidence)

                    # Активуємо команди тільки для лівої та правої зон при утримуманні > 1.2с
                    if zone in (0, 2) and dwell >= self._zone_dwell_sec:
                        if self._zone_fired_at_enter_time != self._zone_enter_time and self.router_callback:
                            intent = "open_browser" if zone == 0 else "toggle_media"
                            # Викликаємо роутер (він сам обробить async/threading)
                            self.router_callback(intent)
                            self._zone_fired_at_enter_time = self._zone_enter_time
                            
                            if not self._quiet_ui and self.ui_callback:
                                self.ui_callback("🌐 Open Browser" if zone == 0 else "⏯️ Media Toggle")

                    # --- CYBER GLOVE RENDER ---
                    # 1. Palm Overlay (Energy Shield)
                    palm_indices = [0, 1, 5, 9, 13, 17]
                    palm_points = np.array([[lm_list[i][1], lm_list[i][2]] for i in palm_indices], np.int32)
                    
                    overlay = img.copy()
                    cv2.fillPoly(overlay, [palm_points], (0, 255, 255)) # Cyan fill
                    cv2.addWeighted(overlay, 0.15, img, 0.85, 0, img)
                    
                    # 2. Energy Connections (Wrist to Fingertips)
                    fingertips = [4, 8, 12, 16, 20]
                    wrist = (lm_list[0][1], lm_list[0][2])
                    
                    for tip in fingertips:
                        pt = (lm_list[tip][1], lm_list[tip][2])
                        cv2.line(img, wrist, pt, (0, 100, 255), 1) # Orange thin lines
                        cv2.circle(img, pt, 4, (0, 255, 255), -1) # Yellow joints

                    if lm_list:
                         # VFX & Core Logic
                         self._process_visuals(img, lm_list)
                         self._process_logic(lm_list)
                         break # First hand only
            else:
                self.prev_lm_list = [] # Reset if hand lost
                self._current_zone = None
                self._zone_fired_at_enter_time = None
                if self.is_active:
                    self.is_active = False # Reset activation on loss
                    if self.hud_callback:
                        self.hud_callback(1, False) # Back to center idle
                self._no_hand_frames += 1
            
            # Енергозбереження: якщо руки немає довго, уповільнюємо цикл
            if self._no_hand_frames > 150:
                time.sleep(0.2)

            # Віртуальні зони: малюємо межі та таймер затримки (на кожному кадрі)
            h, w = img.shape[:2]
            self._draw_zone_overlay(img, h, w, lm_list if lm_list else None)

            # Preview
            if self.show_preview:
                img_small = cv2.resize(img, (640, 360))
                cv2.imshow("Atlas Vision", img_small)
                
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.stop()
                break
            elif key == ord('h'):
                self.show_preview = not self.show_preview
                if not self.show_preview: cv2.destroyWindow("Atlas Vision")
                else: 
                    cv2.namedWindow("Atlas Vision", cv2.WINDOW_NORMAL)
                    cv2.resizeWindow("Atlas Vision", 640, 360)

        cv2.destroyAllWindows()
        print("🧠 [PROCESSING] Thread stopped")

    def _process_visuals(self, img, lm_list):
        # Helper to draw VFX (extracted from original loop)
        if len(lm_list) > 8:
            ix, iy = lm_list[8][1], lm_list[8][2]
            
            # Scanning Aura
            dist_move = math.hypot(ix - self.last_scan_pos[0], iy - self.last_scan_pos[1])
            if dist_move < 15:
                if self.scan_start_time == 0: self.scan_start_time = time.time()
            else:
                self.scan_start_time = 0
                self.last_scan_pos = (ix, iy)
            
            # Determine Color
            aura_color = (0, 255, 0) # Green (Idle)
            if self.scan_start_time > 0:
                duration = time.time() - self.scan_start_time
                if duration > 2.0:
                    aura_color = (0, 0, 255) # Red (Active)
                    if duration < 2.1 and not getattr(self, "_quiet_ui", True) and self.ui_callback:
                        self.ui_callback("🔍 SCANNING...")
                elif duration > 0.5:
                    ratio = min(1.0, (duration - 0.5) / 1.5)
                    aura_color = (0, int(255 * (1-ratio)), int(255 * ratio))
            
            # --- GLOW EFFECT (Augmented Reality) ---
            # Create a soft glow around the index finger
            overlay = img.copy()
            cv2.circle(overlay, (ix, iy), 25, aura_color, -1)
            cv2.addWeighted(overlay, 0.3, img, 0.7, 0, img)
            
            # Core bright dot
            cv2.circle(img, (ix, iy), 5, (255, 255, 255), -1)
            
            # --- DYNAMIC ANCHOR (Index Finger HUD) ---
            # Pulse Ring
            pulse_radius = 20 + int(math.sin(time.time() * 5) * 5)
            cv2.circle(img, (ix, iy), pulse_radius, (0, 255, 255), 1)
            cv2.circle(img, (ix, iy), 3, (255, 255, 255), -1) # Core
            
            # Particles
            for _ in range(5):
                self.particles.append({
                    "pos": [ix, iy],
                    "vel": [random.uniform(-3, 3), random.uniform(-3, 3)],
                    "life": random.randint(10, 25),
                    "color": aura_color
                })
            
            for p in self.particles[:]:
                p["pos"][0] += p["vel"][0]
                p["pos"][1] += p["vel"][1]
                p["life"] -= 1
                if p["life"] > 0:
                    overlay = img.copy()
                    cv2.circle(overlay, (int(p["pos"][0]), int(p["pos"][1])), 3, p["color"], -1)
                    cv2.addWeighted(overlay, 0.4, img, 0.6, 0, img)
                else:
                    self.particles.remove(p)

    def _process_logic(self, lm_list):
        """
        Жести (за замовчуванням тільки ядро — без випадкових шорткатів):

        ЗАВЖДИ УВІМКНЕНІ (ядро):
        - Один вказівний палець → рух курсора (READY).
        - Великий + вказівний зведені (pinch) → клік / подвійний клік / перетягування (ACTION).
        - Два пальці (вказівний + середній) розправлені → скрол (SCROLL).

        ШОРТКАТИ (увімкнені тільки через config, потрібно утримати пози ~1.2 с):
        - VISUAL_GESTURE_SCREENSHOT: великий+вказівний вгору, середній вниз → Win+Prtsc.
        - VISUAL_GESTURE_MEDIA: три пальці + pinch → Play/Pause.
        - VISUAL_GESTURE_SHOW_DESKTOP: вказівник вниз + pinch великий-середній → Win+D.
        - VISUAL_GESTURE_LOCK_PC: вказівник+мізинець вгору, середній+безіменний вниз → Win+L.
        """
        # 1. Coordinates
        x1, y1 = lm_list[8][1:]   # Index
        x2, y2 = lm_list[12][1:]  # Middle
        x0, y0 = lm_list[4][1:]   # Thumb
        
        # 2. Check Fingers
        fingers = []
        fingers.append(1 if lm_list[4][1] < lm_list[3][1] else 0) # Thumb
        for id in [8, 12, 16, 20]:
            fingers.append(1 if lm_list[id][2] < lm_list[id - 2][2] else 0)
            
        # --- ШОРТКАТИ-ЖЕСТИ (тільки якщо увімкнені в config, і після утримання пози _hold_sec) ---
        now_sec = time.time()
        dist_pinch_short = math.hypot(x1 - x0, y1 - y0)
        dist_snap = math.hypot(lm_list[12][1] - x0, lm_list[12][2] - y0)

        def _try_shortcut(gesture_id, pose_ok, last_attr, fire_fn, status_msg=None):
            if not pose_ok:
                self._gesture_hold_start.pop(gesture_id, None)
                return
            if gesture_id not in self._gesture_hold_start:
                self._gesture_hold_start[gesture_id] = now_sec
            hold_elapsed = now_sec - self._gesture_hold_start[gesture_id]
            last_fire = getattr(self, last_attr, 0) or 0
            if hold_elapsed >= self._hold_sec and (now_sec - last_fire) >= self._shortcut_cooldown:
                fire_fn()
                setattr(self, last_attr, now_sec)
                self._gesture_hold_start.pop(gesture_id, None)
                if status_msg and not self._quiet_ui and self.ui_callback:
                    self.ui_callback(status_msg)

        if self._enable_screenshot:
            _try_shortcut(
                "screenshot",
                fingers[0] == 1 and fingers[1] == 1 and fingers[2] == 0,
                "last_screenshot_time",
                lambda: self._queue_action("HOTKEY", ["win", "prtsc"]),
                "📸 Скріншот",
            )
        if self._enable_media:
            _try_shortcut(
                "media",
                fingers[2] == 1 and fingers[3] == 1 and fingers[4] == 1 and dist_pinch_short < 40,
                "last_media_time",
                lambda: self._queue_action("PRESS", "playpause"),
                "⏯️ Медіа",
            )
        if self._enable_show_desktop:
            _try_shortcut(
                "show_desktop",
                fingers[1] == 0 and dist_snap < 40,
                "last_snap_time",
                lambda: self._queue_action("HOTKEY", ["win", "d"]),
                "🖥️ Робочий стіл",
            )
        if self._enable_lock_pc:
            _try_shortcut(
                "lock_pc",
                fingers[1] == 1 and fingers[4] == 1 and fingers[2] == 0 and fingers[3] == 0,
                "last_shield_time",
                lambda: self._queue_action("HOTKEY", ["win", "l"]),
                "🔒 Блокування",
            )

        # --- FSM FOR MOTION (курсор, клік, скрол — завжди активні, без шорткатів) ---
        intent = "IDLE"
        dist_pinch = math.hypot(x1 - x0, y1 - y0)

        if fingers[1] == 1 and fingers[2] == 1:
            if fingers[3] == 0 and fingers[4] == 0:
                intent = "VICTORY"
            else:
                intent = "SCROLL"
        elif all(f == 0 for f in fingers[1:]):
            intent = "FIST"
        elif fingers[1] == 1 and fingers[2] == 0:
            if self.state == "ACTION" and dist_pinch <= self.PINCH_LEAVE:
                intent = "ACTION"
            elif dist_pinch < self.PINCH_ENTER:
                intent = "ACTION"
            else:
                intent = "READY"
        else:
            intent = "IDLE"

        # --- GESTURE STABILIZATION (15 consecutive frames for Command Intents) ---
        if intent in ["VICTORY", "FIST"] and intent == self._last_verified_gesture:
            self._gesture_frame_counter += 1
        else:
            self._gesture_frame_counter = 0
            self._last_verified_gesture = intent if intent in ["VICTORY", "FIST"] else None
        
        # Calculate confidence for HUD (0.0 to 1.0)
        self._gesture_confidence = min(1.0, self._gesture_frame_counter / 15.0) if self._last_verified_gesture else 0.0

        # Transitions & Gesture Actions
        self._gesture_action_text = None # Reset every frame
        
        if self._gesture_frame_counter >= 15:
            # Trigger once per hold
            if self._last_verified_gesture == "VICTORY":
                self.state = "VICTORY"
                if self.is_active and self._current_zone == 2: # Right Zone
                    if self._zone_fired_at_enter_time != self._zone_enter_time and self.router_callback:
                        self.router_callback("switch_window")
                        self._zone_fired_at_enter_time = self._zone_enter_time
                        self._gesture_action_text = "Action: Switch Window"
                        if not self._quiet_ui and self.ui_callback:
                            self.ui_callback("🔲 Switch Window")
            elif self._last_verified_gesture == "FIST":
                self.state = "FIST"
                if self.is_active and self._current_zone == 0: # Left Zone
                    if self._zone_fired_at_enter_time != self._zone_enter_time and self.router_callback:
                        self.router_callback("show_desktop")
                        self._zone_fired_at_enter_time = self._zone_enter_time
                        self._gesture_action_text = "Action: Show Desktop"
                        if not self._quiet_ui and self.ui_callback:
                            self.ui_callback("🖥️ Show Desktop")
        elif intent == "SCROLL":
            self.state = "SCROLL"
        elif intent == "ACTION":
            if self.state in ["READY", "ACTION"]:
                self.state = "ACTION"
            else:
                self.state = "READY"
        elif intent == "READY":
            self.state = "READY"
        else:
            self.state = "IDLE"

        # State Execution
        if self.state == "SCROLL":
             self.pinch_is_drag = False
             self.prev_index_x, self.prev_index_y = 0, 0
             if self.is_dragging:
                 self.is_dragging = False
                 self._queue_action("MOUSE_UP")
             
             dist_fingers = math.hypot(x2 - x1, y2 - y1)
             if self.last_zoom_dist == 0: self.last_zoom_dist = dist_fingers
             
             delta = dist_fingers - self.last_zoom_dist
             if abs(delta) > 10:
                  scroll_amount = 30 if delta > 0 else -30
                  self._queue_action("SCROLL", scroll_amount)
                  self.last_zoom_dist = dist_fingers
                  if not self._quiet_ui and self.ui_callback:
                      self.ui_callback("✌️ ZOOM")
        
        elif self.state in ["READY", "ACTION"]:
             self.last_zoom_dist = 0
             
             # Coordinates logic
             frame_r = 150
             x3 = (max(frame_r, min(x1, self.cam_w - frame_r)) - frame_r) / (self.cam_w - 2 * frame_r) * self.screen_w
             y3 = (max(frame_r, min(y1, self.cam_h - frame_r)) - frame_r) / (self.cam_h - 2 * frame_r) * self.screen_h
             
             dist_move = math.hypot(x3 - self.prev_x, y3 - self.prev_y)
             adaptive_smooth = 2 + (200 / (dist_move + 10))
             
             self.smooth_x = self.prev_x + (x3 - self.prev_x) / adaptive_smooth
             self.smooth_y = self.prev_y + (y3 - self.prev_y) / adaptive_smooth
             
             final_x = max(0, min(self.screen_w - 1, int(self.smooth_x)))
             final_y = max(0, min(self.screen_h - 1, int(self.smooth_y)))
             
             is_pinch = (self.state == "ACTION")

             # Початок pinch: запам'ятовуємо час і позицію для розрізнення клік / drag
             if is_pinch and not self.last_pinch_state:
                 self.pinch_start_time = time.time()
                 self.pinch_start_x = final_x
                 self.pinch_start_y = final_y
                 self.pinch_is_drag = False

             if is_pinch:
                 # Перевірка: вже drag (довго тримаємо або рухали)? Рух рахуємо після 0.08 с, щоб тремтіння не вмикало drag
                 if not self.pinch_is_drag:
                     dur = time.time() - self.pinch_start_time
                     dist = math.hypot(final_x - self.pinch_start_x, final_y - self.pinch_start_y)
                     time_over = dur > self.CLICK_MAX_DURATION
                     move_over = dist > self.CLICK_MAX_MOVE and dur > 0.08
                     if time_over or move_over:
                         self.pinch_is_drag = True
                         self.last_cursor_x, self.last_cursor_y = final_x, final_y
                         self._queue_action("UPDATE_CURSOR", (final_x, final_y, True))

             # Відпустили pinch (перехід ACTION → READY)
             if self.last_pinch_state and not is_pinch:
                 if self.pinch_is_drag:
                     self._queue_action("UPDATE_CURSOR", (final_x, final_y, False))
                 else:
                     dur = time.time() - self.pinch_start_time
                     # Клік тільки якщо pinch був достатньо довгим (не випадковий спайк)
                     if dur >= self.CLICK_MIN_DURATION:
                         now = time.time()
                         if (now - self.last_click_time) <= self.DOUBLE_CLICK_INTERVAL and \
                            math.hypot(final_x - self.last_click_x, final_y - self.last_click_y) <= self.DOUBLE_CLICK_MAX_DIST:
                             self._queue_action("CLICK_DOUBLE", (final_x, final_y))
                             self.last_click_time = 0.0
                             if not self._quiet_ui and self.ui_callback:
                                 self.ui_callback("🖱️ Подвійний клік")
                         else:
                             self._queue_action("CLICK", (final_x, final_y))
                             self.last_click_time = now
                             self.last_click_x = final_x
                             self.last_click_y = final_y
                             if not self._quiet_ui and self.ui_callback:
                                 self.ui_callback("🖱️ Клік")

             # Рух курсора та/або drag: надсилаємо тільки якщо це drag, або просто рух
             if is_pinch and self.pinch_is_drag:
                 if (abs(final_x - self.last_cursor_x) > 2) or (abs(final_y - self.last_cursor_y) > 2) or (is_pinch != self.last_pinch_state):
                     self.last_cursor_x, self.last_cursor_y = final_x, final_y
                     self.last_pinch_state = is_pinch
                     self._queue_action("UPDATE_CURSOR", (final_x, final_y, True))
             else:
                 if (abs(final_x - self.last_cursor_x) > 2) or (abs(final_y - self.last_cursor_y) > 2) or (is_pinch != self.last_pinch_state):
                     self.last_cursor_x, self.last_cursor_y = final_x, final_y
                     self.last_pinch_state = is_pinch
                     # Під час короткого pinch лише рухаємо курсор, без mouseDown
                     self._queue_action("UPDATE_CURSOR", (final_x, final_y, False))

             if not is_pinch:
                 # Не оновлюємо статус "POINTER" кожен кадр — це викликало мерехтіння екрана
                 # Check scroll swipe
                 diff_y = self.smooth_y - self.prev_y
                 if abs(diff_y) > 40:
                    self._queue_action("SCROLL", 150 if diff_y < 0 else -150)
             else:
                 if not self._quiet_ui and self.ui_callback and not getattr(self, "_grabbed_announced", False):
                     self._grabbed_announced = True
                     self.ui_callback("✊ GRAB")
             if not is_pinch:
                 self._grabbed_announced = False

             self.prev_x, self.prev_y = self.smooth_x, self.smooth_y

        else: # IDLE
            self.last_zoom_dist = 0
            self._grabbed_announced = False
            self.pinch_is_drag = False
            if self.is_dragging:
                self.is_dragging = False
                self._queue_action("MOUSE_UP")

        # --- Visual Bridge: жести та координати для голограми (OSC/WebSocket) ---
        if self.visual_bridge and self.visual_bridge.enabled:
            gesture_out = self.state.lower()
            # Детекція "піднята рука": всі пальці розправлені, рука вище за зап'ясток
            if len(lm_list) >= 9:
                wrist_y = lm_list[0][2]
                mid_y = lm_list[9][2]
                all_extended = all(
                    lm_list[i][2] < lm_list[i - 2][2]
                    for i in [8, 12, 16, 20]
                    if i - 2 >= 0
                ) and lm_list[4][1] > lm_list[3][1]
                if all_extended and wrist_y > mid_y:
                    gesture_out = "raised_hand"
            if gesture_out != self._last_bridge_gesture:
                self._last_bridge_gesture = gesture_out
                self.visual_bridge.send_gesture(gesture_out)
            # Нормалізовані координати (0..1) — індекс
            norm_x = lm_list[8][1] / max(1, self.cam_w)
            norm_y = lm_list[8][2] / max(1, self.cam_h)
            self.visual_bridge.send_hand_position(norm_x, norm_y)
            # Крок 3: клік по інтерактивних зонах (config/visual_zones.json)
            self.visual_bridge.check_zones_and_click(norm_x, norm_y, gesture_out)

    def _draw_zone_overlay(self, img, h, w, lm_list=None):
        """Малює напівпрозорі межі зон (0–33%, 33–66%, 66–100%) та таймер затримки."""
        overlay = img.copy()
        x1, x2 = w // 3, 2 * w // 3
        
        # Кольори для зон
        left_color = (150, 50, 50)  # Blue-ish
        center_color = (50, 150, 50) # Green-ish
        right_color = (50, 50, 150) # Red-ish
        
        # Малюємо напівпрозорі прямокутники для зон
        cv2.rectangle(overlay, (0, 0), (x1, h), left_color, -1)
        cv2.rectangle(overlay, (x1, 0), (x2, h), center_color, -1)
        cv2.rectangle(overlay, (x2, 0), (w, h), right_color, -1)
        
        # Додаємо прозорість (Glassmorphism effect)
        cv2.addWeighted(overlay, 0.15, img, 0.85, 0, img)
        
        # Малюємо чіткі межі
        cv2.line(img, (x1, 0), (x1, h), (0, 255, 255), 1)
        cv2.line(img, (x2, 0), (x2, h), (0, 255, 255), 1)
        
        # Підписи зон зверху
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(img, "BROWSER", (x1 // 2 - 40, 30), font, 0.5, (255, 255, 255), 1)
        cv2.putText(img, "GESTURES", (x1 + (x2 - x1) // 2 - 40, 30), font, 0.5, (255, 255, 255), 1)
        cv2.putText(img, "MEDIA", (x2 + (w - x2) // 2 - 30, 30), font, 0.5, (255, 255, 255), 1)
        
        # Активна зона та таймер
        if lm_list is not None and self._current_zone is not None and self._zone_enter_time is not None:
            dwell = time.time() - self._zone_enter_time
            
            # Підсвічуємо активну зону
            if self._current_zone == 0:
                zx1, zx2 = 0, x1
                active_color = (255, 200, 0)
            elif self._current_zone == 1:
                zx1, zx2 = x1, x2
                active_color = (0, 255, 0)
            else:
                zx1, zx2 = x2, w
                active_color = (0, 100, 255)
            
            # Progress bar dwell timer
            if self._current_zone in (0, 2):
                progress = min(1.0, dwell / self._zone_dwell_sec)
                bar_w = int((zx2 - zx1) * progress)
                cv2.rectangle(img, (zx1, h - 5), (zx1 + bar_w, h), active_color, -1)
                
                # Текст таймера
                timer_text = f"{dwell:.1f}s / {self._zone_dwell_sec}s"
                cv2.putText(img, timer_text, (zx1 + 10, h - 15), font, 0.4, (255, 255, 255), 1)
                
                if dwell >= self._zone_dwell_sec:
                    cv2.putText(img, "TRIGGERED", (zx1 + (zx2-zx1)//2 - 40, h // 2), font, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(img, "ACTIVE MODE", (zx1 + 10, h - 15), font, 0.4, (0, 255, 0), 1)

        # Action Feedback Text
        if hasattr(self, "_gesture_action_text") and self._gesture_action_text:
             cv2.putText(img, self._gesture_action_text, (w // 2 - 100, h - 50), font, 0.7, (0, 255, 255), 2)

    def _queue_action(self, type, data=None):
        # Helper to push to action queue without blocking
        try:
            # If queue full, pop one to make space (prioritize new actions)
            if self.action_queue.full():
                self.action_queue.get_nowait()
            self.action_queue.put_nowait((type, data))
        except:
            pass

    # --- THREAD 3: ACTION EXECUTOR ---
    def _action_worker(self):
        # Local state to track drag
        is_dragging_internal = False
        
        while self.is_running:
            try:
                type, data = self.action_queue.get(timeout=0.1)
            except queue.Empty:
                continue
                
            try:
                if type == "HOTKEY":
                    pyautogui.hotkey(*data)
                elif type == "PRESS":
                    pyautogui.press(data)
                elif type == "SCROLL":
                    pyautogui.scroll(data)
                elif type == "MOUSE_UP":
                    if is_dragging_internal:
                        pyautogui.mouseUp()
                        is_dragging_internal = False
                        print("📂 [ACTION] Mouse Up")

                elif type == "CLICK":
                    tx, ty = data
                    pyautogui.moveTo(tx, ty, _pause=False)
                    pyautogui.click(tx, ty, button='left')

                elif type == "CLICK_DOUBLE":
                    tx, ty = data
                    pyautogui.moveTo(tx, ty, _pause=False)
                    pyautogui.doubleClick(tx, ty, button='left')
                
                elif type == "UPDATE_CURSOR":
                    # data = (x, y, is_pinch)
                    tx, ty, pinch = data
                    
                    if pinch and not is_dragging_internal:
                        # Start Drag
                        pyautogui.mouseDown(tx, ty, button='left')
                        is_dragging_internal = True
                        time.sleep(0.05) # Small delay for OS
                    
                    elif pinch and is_dragging_internal:
                        # Continue Drag
                        pyautogui.moveTo(tx, ty, _pause=False)
                        
                    elif not pinch:
                        if is_dragging_internal:
                             # Release
                             pyautogui.mouseUp(tx, ty, button='left')
                             is_dragging_internal = False
                        
                        # Just Move (with deadzone check internal logic or pre-checked?)
                        # We can just move. Pre-check was in logic.
                        # Wait, logic didn't do deadzone check fully before queueing? 
                        # Logic calculated `final_x`.
                        # Let's trust logic's coordinates.
                        pyautogui.moveTo(tx, ty, _pause=False)
            
            except Exception as e:
                print(f"⚠️ [ACTION] Error: {e}")

        print("⚡ [ACTION] Thread stopped")

if __name__ == "__main__":
    vm = VisionManager()
    vm.start()
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            vm.stop()
            break
