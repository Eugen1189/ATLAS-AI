import cv2
import numpy as np
import mediapipe as mp
import pyautogui
import threading
import time
import math
import queue
import warnings
from PIL import Image
from core.i18n import lang
from core.logger import logger
import os

# Hide technical warnings from MediaPipe / Protobuf
warnings.filterwarnings("ignore", category=UserWarning, module='google.protobuf.symbol_database')

class VisionManager:
    """
    AXIS V2.5 Vision Manager (Clean Architecture)
    - Dynamic EMA Smoothing
    - Fist Pause Gesture
    - Action Dead-Zones
    - Visual HUD Integration (PyQt6 Signals)
    """
    def __init__(self, camera_index=0, hud_bridge=None):
        self.camera_index = camera_index
        self.is_running = False
        self.hud_bridge = hud_bridge # Bridge for UI updates
        
        # Threads & Queues
        self.capture_thread = None
        self.process_thread = None
        self.action_thread = None
        
        self.frame_queue = queue.Queue(maxsize=1)
        self.action_queue = queue.Queue(maxsize=24)
        
        # Screen & Camera Metrics
        self.screen_w, self.screen_h = pyautogui.size()
        self.cam_w, self.cam_h = 1280, 720
        # Dead Zones (Active Area Margins)
        self.margin_x = int(self.cam_w * 0.15)
        self.margin_y = int(self.cam_h * 0.15)
        
        # Smoothing State
        self.prev_x, self.prev_y = 0, 0
        self.smooth_x, self.smooth_y = 0, 0
        
        # System State
        self.state = "IDLE"  # IDLE, ACTIVE, CLICK, PAUSED, SCREENSHOT
        self.current_processed_frame = None
        self.last_screenshot_time = 0

    def _init_resources(self):
        try:
            self.mp_hands = mp.solutions.hands
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=0.8,
                min_tracking_confidence=0.7
            )
            self.mp_draw = mp.solutions.drawing_utils
            return True
        except Exception as e:
            print(lang.get("vision.mp_load_error", error=e))
            return False

    def start(self):
        print(lang.get("vision.starting"))
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
        if hasattr(self, 'hands') and self.hands: self.hands.close()
        cv2.destroyAllWindows()

    def get_latest_frame(self):
        if self.current_processed_frame is not None:
             img_rgb = cv2.cvtColor(self.current_processed_frame, cv2.COLOR_BGR2RGB)
             return Image.fromarray(img_rgb)
        return None

    def _capture_worker(self):
        print(lang.get("vision.connecting", index=self.camera_index))
        # Use MSMF (Media Foundation) instead of DSHOW for Windows 10/11
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_MSMF)
        if not cap.isOpened():
             # Fallback if MSMF doesn't work, try just index without backend
             for idx in [0, 1, 2]:
                 cap = cv2.VideoCapture(idx)
                 if cap.isOpened(): break
        
        if not cap.isOpened():
            print(lang.get("vision.no_camera"))
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

    def _get_finger_states(self, lm_list):
        """Returns the state of 5 fingers (True - straight, False - bent)."""
        states = []
        if not lm_list: return [False]*5
        
        x0, y0 = lm_list[0][1:]
        
        # 0: Thumb, 1: Index, 2: Middle, 3: Ring, 4: Pinky
        tip_ids = [4, 8, 12, 16, 20]
        pip_ids = [2, 6, 10, 14, 18] 
        
        for i in range(5):
            tip_x, tip_y = lm_list[tip_ids[i]][1:]
            pip_x, pip_y = lm_list[pip_ids[i]][1:]
            
            dist_tip = math.hypot(tip_x - x0, tip_y - y0)
            dist_pip = math.hypot(pip_x - x0, pip_y - y0)
            
            # Finger is straight if the tip is further from the wrist than the middle joint
            states.append(dist_tip > dist_pip)
            
        return states

    def _is_fist(self, lm_list):
        """Checks if the hand is clenched into a fist (all 4 fingers bent)."""
        states = self._get_finger_states(lm_list)
        return states[1:] == [False, False, False, False]

    def _is_l_shape(self, lm_list):
        """Checks if the hand is showing an 'L' gesture (screenshot)"""
        states = self._get_finger_states(lm_list)
        return states == [True, True, False, False, False]

    def _is_palm(self, lm_list):
        """Checks if all 5 fingers are straight (Stop gesture)."""
        states = self._get_finger_states(lm_list)
        return states == [True, True, True, True, True]

    def _is_thumbs_up(self, lm_list):
        """Checks if only the thumb is straight (Confirm gesture)."""
        states = self._get_finger_states(lm_list)
        return states == [True, False, False, False, False]

    def _processing_worker(self):
        cv2.namedWindow("AXIS Vision V2.5", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("AXIS Vision V2.5", 640, 360)
        
        cross_counter = 0
        
        while self.is_running:
            try: frame = self.frame_queue.get(timeout=1)
            except queue.Empty: continue
                
            img = cv2.flip(frame, 1)
            self.current_processed_frame = img.copy() 
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = self.hands.process(img_rgb)
            
            h, w, c = img.shape
            self.cam_h, self.cam_w = h, w
            
            if results.multi_hand_landmarks:
                for hand_lms in results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(img, hand_lms, self.mp_hands.HAND_CONNECTIONS)
                    
                # ---------------- SLEEP GESTURE (CROSSED ARMS) ----------------
                if len(results.multi_hand_landmarks) == 2 and results.multi_handedness:
                    hand1_x = results.multi_hand_landmarks[0].landmark[0].x
                    hand2_x = results.multi_hand_landmarks[1].landmark[0].x
                    
                    hand1_label = results.multi_handedness[0].classification[0].label
                    hand2_label = results.multi_handedness[1].classification[0].label
                    
                    # Check if arms are crossed. 
                    if (hand1_label == "Left" and hand1_x > hand2_x) or (hand2_label == "Left" and hand2_x > hand1_x):
                        cross_counter += 1
                        print(lang.get("vision.crossed_arms", counter=cross_counter))
                    else:
                        cross_counter = max(0, cross_counter - 2) # Smooth decay
                        
                    if cross_counter > 45:
                        print(lang.get("vision.sleep_detected"))
                        # Наступний цикл не виконається, потоки завершаться
                        self.is_running = False
                        break
                else:
                    cross_counter = max(0, cross_counter - 1)
                # -------------------------------------------------------------
                
                # Process the first detected hand for mouse gestures / clicks
                hand_lms = results.multi_hand_landmarks[0]
                lm_list = []
                for id, lm in enumerate(hand_lms.landmark):
                     cx, cy = int(lm.x * w), int(lm.y * h)
                     lm_list.append([id, cx, cy])
                
                if lm_list:
                    # Check for fist (Pause)
                        if self._is_fist(lm_list):
                            self.state = "PAUSED"
                        elif self._is_l_shape(lm_list):
                            self.state = "SCREENSHOT"
                            if time.time() - self.last_screenshot_time > 3.0:
                                self._queue_action("SCREENSHOT", None)
                                self.last_screenshot_time = time.time()
                        elif self._is_palm(lm_list):
                            self.state = "STOP"
                            # Trigger interruption logic here
                            logger.critical("vision.interruption_detected")
                            # We can send a signal to AxisCore to abort thinking
                            if self.hud_bridge:
                                self.hud_bridge.vision_update.emit({"state": "STOP"})
                                
                            # Forcefully terminate any subprocesses or block thinking
                            # In a real app, this might set a global StopEvent
                            os.environ["AXIS_INTERRUPT"] = "TRUE" 
                        elif self._is_thumbs_up(lm_list):
                            self.state = "CONFIRM"
                            logger.info("vision.confirm_detected")
                            if self.hud_bridge:
                                self.hud_bridge.vision_update.emit({"state": "CONFIRM"})
                            os.environ["AXIS_CONFIRM"] = "TRUE"
                        else:
                            x4, y4 = lm_list[4][1:]
                            x8, y8 = lm_list[8][1:]
                            dist_pinch = math.hypot(x8 - x4, y8 - y4)
                            
                            dist_move = math.hypot(x8 - self.prev_x, y8 - self.prev_y)
                            dynamic_alpha = np.interp(dist_move, [0, 100], [0.1, 0.7])
                            
                            self.smooth_x = int(dynamic_alpha * x8 + (1 - dynamic_alpha) * self.smooth_x)
                            self.smooth_y = int(dynamic_alpha * y8 + (1 - dynamic_alpha) * self.smooth_y)
                            
                            screen_x = np.interp(self.smooth_x, (self.margin_x, w - self.margin_x), (0, self.screen_w))
                            screen_y = np.interp(self.smooth_y, (self.margin_y, h - self.margin_y), (0, self.screen_h))
                            
                            # Check virtual zones (Virtual Zones 2.0)
                            if self.smooth_y < h * 0.20: # Top volume zone
                                self.state = "VOLUME_CONTROL"
                                if time.time() - self.last_screenshot_time > 0.1: # Small cooldown
                                    if self.smooth_x > self.prev_x + 5: 
                                        self._queue_action("KEY_PRESS", 'volumeup')
                                        self.last_screenshot_time = time.time()
                                    elif self.smooth_x < self.prev_x - 5:
                                        self._queue_action("KEY_PRESS", 'volumedown')
                                        self.last_screenshot_time = time.time()
                                    
                            elif self.smooth_y > h * 0.80: # Bottom media zone
                                self.state = "MEDIA_CONTROL"
                                if dist_pinch < 40 and time.time() - self.last_screenshot_time > 1.0: # Pinch = Play/Pause
                                    self._queue_action("KEY_PRESS", 'playpause')
                                    self.last_screenshot_time = time.time() 
                                elif time.time() - self.last_screenshot_time > 0.5:
                                    if self.smooth_x > self.prev_x + 15: # Swipe right
                                        self._queue_action("KEY_PRESS", 'nexttrack')
                                        self.last_screenshot_time = time.time()
                                    elif self.smooth_x < self.prev_x - 15: # Swipe left
                                        self._queue_action("KEY_PRESS", 'prevtrack')
                                        self.last_screenshot_time = time.time()
                                    
                            else: # Central zone (Mouse Control)
                                self.state = "CLICK" if dist_pinch < 40 else "ACTIVE"
                                self._queue_action("UPDATE_CURSOR", (screen_x, screen_y, self.state == "CLICK"))
                            
                            self.prev_x, self.prev_y = self.smooth_x, self.smooth_y
                            
                            # Draw cursor and Notify HUD
                            if self.hud_bridge:
                                self.hud_bridge.vision_update.emit({
                                    "x": screen_x,
                                    "y": screen_y,
                                    "state": self.state,
                                    "cam_x": self.smooth_x / w, # Normalized
                                    "cam_y": self.smooth_y / h
                                })

                            cv2.circle(img, (self.smooth_x, self.smooth_y), 15, (0, 255, 0) if self.state == "ACTIVE" else (0, 0, 255), cv2.FILLED)
            else:
                self.state = "IDLE"
                if self.hud_bridge:
                    self.hud_bridge.vision_update.emit({"state": "IDLE"})

            self._draw_hud(img)
            
            # Preview
            img_small = cv2.resize(img, (640, 360))
            cv2.imshow("AXIS Vision V2.5", img_small)
            if cv2.waitKey(1) & 0xFF == ord('q'): 
                self.is_running = False
                break

        cv2.destroyAllWindows()

    def _draw_hud(self, img):
        h, w = img.shape[:2]
        
        # Draw Dead Zone (Active Box)
        cv2.rectangle(img, (self.margin_x, self.margin_y), (w - self.margin_x, h - self.margin_y), (255, 255, 255), 1)
        
        # Draw Virtual Zones Guides
        top_y = int(self.cam_h * 0.20)
        bottom_y = int(self.cam_h * 0.80)
        
        # Volume Zone (Top)
        v_color = (255,0,0) if self.state == "VOLUME_CONTROL" else (50,50,50)
        cv2.rectangle(img, (0, 0), (self.cam_w, top_y), v_color, 2)
        cv2.putText(img, "VOLUME", (10, top_y - 10), cv2.FONT_HERSHEY_PLAIN, 1, v_color, 1)

        # Media Zone (Bottom)
        m_color = (0,165,255) if self.state == "MEDIA_CONTROL" else (50,50,50)
        cv2.rectangle(img, (0, bottom_y), (self.cam_w, self.cam_h), m_color, 2)
        cv2.putText(img, "MEDIA", (10, bottom_y + 20), cv2.FONT_HERSHEY_PLAIN, 1, m_color, 1)
        
        # Draw Status HUD
        status_color = (150, 150, 150) # Gray
        if self.state == "ACTIVE": status_color = (0, 255, 0)
        elif self.state == "CLICK": status_color = (0, 0, 255)
        elif self.state == "PAUSED": status_color = (0, 255, 255) # Yellow
        elif self.state == "SCREENSHOT": status_color = (255, 0, 255) # Magenta
        elif self.state == "VOLUME_CONTROL": status_color = (255, 0, 0) # Blue
        elif self.state == "MEDIA_CONTROL": status_color = (0, 165, 255) # Orange
        elif self.state == "STOP": status_color = (0, 0, 255) # Bright Red
        elif self.state == "CONFIRM": status_color = (0, 255, 255) # Yellow
        
        # Status Panel (Bottom Left)
        cv2.rectangle(img, (10, h - 70), (250, h - 20), (0, 0, 0), cv2.FILLED)
        cv2.putText(img, f"STATE: {self.state}", (20, h - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
        
        # Camera Indicator (Top Right - Privacy/Security Feature)
        indicator_text = lang.get("vision.live_status") if self.state != "IDLE" else lang.get("vision.idle_status")
        indicator_color = (0, 255, 0) if self.state != "IDLE" else (100, 100, 100)
        
        # Calculate text width for right alignment
        (text_w, text_h), _ = cv2.getTextSize(indicator_text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)
        padding_x = 20
        padding_y = 10
        top_right_x = w - text_w - (padding_x * 2) - 10
        top_right_y = 10
        
        # Draw indicator background
        cv2.rectangle(img, 
            (top_right_x, top_right_y), 
            (top_right_x + text_w + (padding_x * 2), top_right_y + text_h + (padding_y * 2)), 
            (0, 0, 0), cv2.FILLED)
            
        # Draw colored indicator dot
        dot_radius = 8
        dot_center = (top_right_x + padding_x + dot_radius, top_right_y + padding_y + text_h // 2)
        cv2.circle(img, dot_center, dot_radius, indicator_color, cv2.FILLED)
        
        # Draw text
        text_start_x = top_right_x + padding_x + (dot_radius * 2) + 10
        text_start_y = top_right_y + padding_y + text_h
        cv2.putText(img, indicator_text, (text_start_x, text_start_y), cv2.FONT_HERSHEY_SIMPLEX, 1.5, indicator_color, 3)

    def _queue_action(self, type, data=None):
        try:
            if self.action_queue.full(): self.action_queue.get_nowait()
            self.action_queue.put_nowait((type, data))
        except: pass

    def _action_worker(self):
        # Configure PyAutoGUI
        pyautogui.FAILSAFE = False
        click_cooldown = 0
        
        while self.is_running:
            try: type, data = self.action_queue.get(timeout=0.1)
            except queue.Empty: continue
            
            try:
                if type == "UPDATE_CURSOR":
                    tx, ty, is_click = data
                    pyautogui.moveTo(tx, ty, _pause=False)
                    
                    if is_click and time.time() - click_cooldown > 0.3:
                        pyautogui.click()
                        click_cooldown = time.time()
                elif type == "KEY_PRESS":
                    pyautogui.press(data)
                elif type == "SCREENSHOT":
                    import os
                    from datetime import datetime
                    import json
                    print(lang.get("vision.l_gesture"))
                    
                    # 1. Save file
                    screenshot_img = pyautogui.screenshot()
                    memories_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "memories", "screenshots")
                    os.makedirs(memories_dir, exist_ok=True)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    file_name = f"vision_{timestamp}.png"
                    file_path = os.path.join(memories_dir, file_name)
                    screenshot_img.save(file_path)
                    print(lang.get("vision.screenshot_saved", path=file_path))
                    
                    # 2. Smart Logging (MCP-logic for saving log)
                    log_data = {
                        "action": "screenshot_taken",
                        "timestamp": timestamp,
                        "trigger": "visual_gesture_L",
                        "file": file_name,
                        "description": "Screenshot taken by user's visual command."
                    }
                    log_path = os.path.join(memories_dir, "last_action.json")
                    with open(log_path, 'w', encoding='utf-8') as f:
                        json.dump(log_data, f, ensure_ascii=False, indent=2)
                    print(lang.get("vision.log_saved"))
                    
                    # 3. Send to Telegram
                    try:
                        import sys
                        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
                        if root_path not in sys.path:
                            sys.path.append(root_path)
                        from agent_skills.telegram_bridge.manifest import send_telegram_photo
                        
                        caption = lang.get("vision.tg_caption") + f"\n\nJSON Log:\n{json.dumps(log_data, ensure_ascii=False, indent=2)}"
                        send_telegram_photo(file_path, caption=caption)
                    except Exception as ex:
                        print(lang.get("vision.tg_error", error=ex))
            except Exception as e:
                print(lang.get("vision.action_error", error=e))

if __name__ == "__main__":
    print(lang.get("vision.start_direct"))
    vision = VisionManager()
    vision.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(lang.get("vision.stopping"))
        vision.stop()
