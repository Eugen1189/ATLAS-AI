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
        self.ema_alpha = 0.2 # Smoothing factor
        
        # Threads
        self.capture_thread = None
        self.process_thread = None
        self.action_thread = None
        
        # Queues for Thread Communication
        self.frame_queue = queue.Queue(maxsize=1) # Keep only latest frame
        self.action_queue = queue.Queue(maxsize=24) # Буфер для дій
        
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

        # Клік vs перетягування
        self.pinch_start_time = 0.0
        self.pinch_start_x = 0
        self.pinch_start_y = 0
        self.pinch_is_drag = False
        self.last_click_time = 0.0
        self.last_click_x = 0
        self.last_click_y = 0
        self.CLICK_MIN_DURATION = 0.05
        self.CLICK_MAX_DURATION = 0.42
        self.CLICK_MAX_MOVE = 45
        self.DOUBLE_CLICK_INTERVAL = 0.5
        self.DOUBLE_CLICK_MAX_DIST = 60
        self.PINCH_ENTER = 68
        self.PINCH_LEAVE = 85

        # Шорткати-жести
        self._gesture_hold_start = {}
        self._shortcut_cooldown = 2.5
        self._hold_sec = 1.2
        self._enable_screenshot = False
        self._enable_media = False
        self._enable_show_desktop = False
        self._enable_lock_pc = False

        # Super Powers & VFX 
        self.last_screenshot_time = 0
        self.last_media_time = 0
        self.last_snap_time = 0
        self.last_shield_time = 0
        self.particles = []
        self.scan_start_time = 0
        self.last_scan_pos = (0, 0)
        
        # Preview State
        self.show_preview = True
        self.visual_bridge = None
        self._last_bridge_gesture = None
        self._quiet_ui = True

        # Віртуальні зони
        self._zone_dwell_sec = 1.2
        self._zone_enter_time = None
        self._current_zone = None
        self._zone_fired_at_enter_time = None
        self._zone_cooldown = 2.5
        self.is_active = False
        self._no_hand_frames = 0
        
        self._gesture_history = deque(maxlen=20)
        self._gesture_frame_counter = 0 
        self._last_verified_gesture = None
        self._gesture_confidence = 0.0

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
        if not self._init_resources(): return
        self.is_running = True
        
        self.capture_thread = threading.Thread(target=self._capture_worker, daemon=True)
        self.process_thread = threading.Thread(target=self._processing_worker, daemon=True)
        self.action_thread = threading.Thread(target=self._action_worker, daemon=True)
        
        self.capture_thread.start()
        self.process_thread.start()
        self.action_thread.start()

    def stop(self):
        self.is_running = False
        if self.capture_thread: self.capture_thread.join(timeout=1)
        if self.process_thread: self.process_thread.join(timeout=1)
        if self.action_thread: self.action_thread.join(timeout=1)
        if self.hands: self.hands.close()
        cv2.destroyAllWindows()

    def _capture_worker(self):
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
             for idx in [1, 2, 0]:
                 cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                 if cap.isOpened(): break
        
        if not cap.isOpened():
            self.is_running = False
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cam_w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cam_h)
        
        while self.is_running:
            success, frame = cap.read()
            if success:
                if self.frame_queue.full():
                    try: self.frame_queue.get_nowait() 
                    except queue.Empty: pass
                self.frame_queue.put(frame)
            else: time.sleep(0.1)
        cap.release()

    def get_latest_frame(self):
        if hasattr(self, 'current_processed_frame') and self.current_processed_frame is not None:
             from PIL import Image
             img_rgb = cv2.cvtColor(self.current_processed_frame, cv2.COLOR_BGR2RGB)
             return Image.fromarray(img_rgb)
        return None

    def _processing_worker(self):
        cv2.namedWindow("Atlas Vision", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Atlas Vision", 640, 360)
        
        while self.is_running:
            try: frame = self.frame_queue.get(timeout=1)
            except queue.Empty: continue
                
            img = cv2.flip(frame, 1)
            self.current_processed_frame = img.copy() 
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = self.hands.process(img_rgb)
            
            lm_list = []
            if results.multi_hand_landmarks:
                self._no_hand_frames = 0
                for hand_lms in results.multi_hand_landmarks:
                    current_lm_list = []
                    h, w, c = img.shape
                    for id, lm in enumerate(hand_lms.landmark):
                         cx, cy = int(lm.x * w), int(lm.y * h)
                         current_lm_list.append([id, cx, cy])
                    
                    if not self.prev_lm_list or len(self.prev_lm_list) != len(current_lm_list):
                        self.prev_lm_list = current_lm_list
                    
                    smoothed_list = []
                    for i in range(len(current_lm_list)):
                        prev_cx, prev_cy = self.prev_lm_list[i][1], self.prev_lm_list[i][2]
                        curr_cx, curr_cy = current_lm_list[i][1], current_lm_list[i][2]
                        smooth_cx = int(self.ema_alpha * curr_cx + (1 - self.ema_alpha) * prev_cx)
                        smooth_cy = int(self.ema_alpha * curr_cy + (1 - self.ema_alpha) * prev_cy)
                        smoothed_list.append([i, smooth_cx, smooth_cy])
                    
                    self.prev_lm_list = smoothed_list
                    lm_list = smoothed_list 

                    h, w = img.shape[:2]
                    ix, iy = lm_list[8][1], lm_list[8][2]
                    self.smooth_x = int(self.ema_alpha * ix + (1 - self.ema_alpha) * self.smooth_x)
                    self.smooth_y = int(self.ema_alpha * iy + (1 - self.ema_alpha) * self.smooth_y)
                    lm_list[8] = (8, self.smooth_x, self.smooth_y)
                    
                    # Zone Logic
                    left_bound, right_bound = w / 3, 2 * w / 3
                    if self.smooth_x < left_bound: zone = 0
                    elif self.smooth_x < right_bound: zone = 1
                    else: zone = 2

                    now = time.time()
                    if zone != self._current_zone:
                        self._current_zone = zone
                        self._zone_enter_time = now
                    
                    if lm_list:
                         self._process_visuals(img, lm_list)
                         self._process_logic(lm_list)
                         break 
            else:
                self._current_zone = None
                self._no_hand_frames += 1
            
            if self._no_hand_frames > 150: time.sleep(0.2)
            h, w = img.shape[:2]
            self._draw_zone_overlay(img, h, w, lm_list if lm_list else None)

            if self.show_preview:
                img_small = cv2.resize(img, (640, 360))
                cv2.imshow("Atlas Vision", img_small)
            if cv2.waitKey(1) & 0xFF == ord('q'): break

        cv2.destroyAllWindows()

    def _process_visuals(self, img, lm_list):
        ix, iy = lm_list[8][1], lm_list[8][2]
        cv2.circle(img, (ix, iy), 15, (0, 255, 255), 2)
        
    def _process_logic(self, lm_list):
        x1, y1 = lm_list[8][1:]
        x0, y0 = lm_list[4][1:]
        dist_pinch = math.hypot(x1 - x0, y1 - y0)
        
        if dist_pinch < 40: self.state = "ACTION"
        else: self.state = "READY"
        
        # Simple cursor update
        self._queue_action("UPDATE_CURSOR", (x1, y1, self.state == "ACTION"))

    def _draw_zone_overlay(self, img, h, w, lm_list=None):
        x1, x2 = w // 3, 2 * w // 3
        cv2.line(img, (x1, 0), (x1, h), (0, 255, 255), 1)
        cv2.line(img, (x2, 0), (x2, h), (0, 255, 255), 1)

    def _queue_action(self, type, data=None):
        try:
            if self.action_queue.full(): self.action_queue.get_nowait()
            self.action_queue.put_nowait((type, data))
        except: pass

    def _action_worker(self):
        while self.is_running:
            try: type, data = self.action_queue.get(timeout=0.1)
            except queue.Empty: continue
            try:
                if type == "UPDATE_CURSOR":
                    tx, ty, pinch = data
                    # Scaling logic would go here
                    pyautogui.moveTo(tx, ty, _pause=False)
                    if pinch: pyautogui.click()
            except: pass
