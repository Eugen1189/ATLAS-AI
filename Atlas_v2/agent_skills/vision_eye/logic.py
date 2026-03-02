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

# Приховуємо технічні попередження від MediaPipe / Protobuf
warnings.filterwarnings("ignore", category=UserWarning, module='google.protobuf.symbol_database')

class VisionManager:
    """
    Atlas V2 Vision Manager (Clean Architecture)
    - Dynamic EMA Smoothing
    - Fist Pause Gesture
    - Action Dead-Zones
    - Visual HUD
    """
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.is_running = False
        
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
                max_num_hands=1,
                min_detection_confidence=0.8,
                min_tracking_confidence=0.7
            )
            self.mp_draw = mp.solutions.drawing_utils
            return True
        except Exception as e:
            print(f"[VISION] Failed to load MediaPipe: {e}")
            return False

    def start(self):
        print("[VISION] Спроба запуску камери (VisionManager.start)...")
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
        print(f"[VISION] Спроба підключення до камери (index={self.camera_index})...")
        # Використовуємо MSMF (Media Foundation) замість DSHOW для Windows 10/11
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_MSMF)
        if not cap.isOpened():
             # Fallback якщо не працює MSMF, пробуємо просто індекс без бекенда
             for idx in [0, 1, 2]:
                 cap = cv2.VideoCapture(idx)
                 if cap.isOpened(): break
        
        if not cap.isOpened():
            print("[VISION] No camera found.")
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
        """Повертає стан 5 пальців (True - випрямлений, False - зігнутий)."""
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
            
            # Палець випрямлений, якщо кінчик далі від зап'ястя, ніж середній суглоб
            states.append(dist_tip > dist_pip)
            
        return states

    def _is_fist(self, lm_list):
        """Перевіряє чи рука стиснута в кулак (всі 4 пальці зігнуті)."""
        states = self._get_finger_states(lm_list)
        return states[1:] == [False, False, False, False]

    def _is_l_shape(self, lm_list):
        """Перевіряє чи рука показує жест 'L' (скріншот)"""
        states = self._get_finger_states(lm_list)
        return states == [True, True, False, False, False]

    def _processing_worker(self):
        cv2.namedWindow("Atlas Vision V2", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Atlas Vision V2", 640, 360)
        
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
                    
                    lm_list = []
                    for id, lm in enumerate(hand_lms.landmark):
                         cx, cy = int(lm.x * w), int(lm.y * h)
                         lm_list.append([id, cx, cy])
                    
                    if lm_list:
                        # Перевірка на кулак (Пауза)
                        if self._is_fist(lm_list):
                            self.state = "PAUSED"
                        elif self._is_l_shape(lm_list):
                            self.state = "SCREENSHOT"
                            if time.time() - self.last_screenshot_time > 3.0:
                                self._queue_action("SCREENSHOT", None)
                                self.last_screenshot_time = time.time()
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
                            
                            # Перевірка віртуальних зон (Virtual Zones 2.0)
                            if self.smooth_y < h * 0.20: # Верхня зона гучності
                                self.state = "VOLUME_CONTROL"
                                if time.time() - self.last_screenshot_time > 0.1: # Невеликий кулдаун
                                    if self.smooth_x > self.prev_x + 5: 
                                        self._queue_action("KEY_PRESS", 'volumeup')
                                        self.last_screenshot_time = time.time()
                                    elif self.smooth_x < self.prev_x - 5:
                                        self._queue_action("KEY_PRESS", 'volumedown')
                                        self.last_screenshot_time = time.time()
                                    
                            elif self.smooth_y > h * 0.80: # Нижня зона медіа
                                self.state = "MEDIA_CONTROL"
                                if dist_pinch < 40 and time.time() - self.last_screenshot_time > 1.0: # Pinch = Play/Pause
                                    self._queue_action("KEY_PRESS", 'playpause')
                                    self.last_screenshot_time = time.time() 
                                elif time.time() - self.last_screenshot_time > 0.5:
                                    if self.smooth_x > self.prev_x + 15: # Свайп вправо
                                        self._queue_action("KEY_PRESS", 'nexttrack')
                                        self.last_screenshot_time = time.time()
                                    elif self.smooth_x < self.prev_x - 15: # Свайп вліво
                                        self._queue_action("KEY_PRESS", 'prevtrack')
                                        self.last_screenshot_time = time.time()
                                    
                            else: # Центральна зона (Керування мишею)
                                self.state = "CLICK" if dist_pinch < 40 else "ACTIVE"
                                self._queue_action("UPDATE_CURSOR", (screen_x, screen_y, self.state == "CLICK"))
                            
                            self.prev_x, self.prev_y = self.smooth_x, self.smooth_y
                            
                            # Намалюємо курсор
                            cv2.circle(img, (self.smooth_x, self.smooth_y), 15, (0, 255, 0) if self.state == "ACTIVE" else (0, 0, 255), cv2.FILLED)
            else:
                self.state = "IDLE"

            self._draw_hud(img)
            
            # Preview
            img_small = cv2.resize(img, (640, 360))
            cv2.imshow("Atlas Vision V2", img_small)
            if cv2.waitKey(1) & 0xFF == ord('q'): break

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
        
        # HUD Panel
        cv2.rectangle(img, (10, 10), (250, 60), (0, 0, 0), cv2.FILLED)
        cv2.putText(img, f"STATE: {self.state}", (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)

    def _queue_action(self, type, data=None):
        try:
            if self.action_queue.full(): self.action_queue.get_nowait()
            self.action_queue.put_nowait((type, data))
        except: pass

    def _action_worker(self):
        # Налаштування PyAutoGUI
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
                    print("[VISION] Жест 'L' розпізнано! Роблю скріншот...")
                    
                    # 1. Зберігаємо файл
                    screenshot_img = pyautogui.screenshot()
                    memories_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "memories", "screenshots")
                    os.makedirs(memories_dir, exist_ok=True)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    file_name = f"vision_{timestamp}.png"
                    file_path = os.path.join(memories_dir, file_name)
                    screenshot_img.save(file_path)
                    print(f"✅ Скріншот збережено: {file_path}")
                    
                    # 2. Smart Logging (MCP-логіка збереження логу)
                    log_data = {
                        "action": "screenshot_taken",
                        "timestamp": timestamp,
                        "trigger": "visual_gesture_L",
                        "file": file_name,
                        "description": "Скріншот зроблено за візуальною командою користувача."
                    }
                    log_path = os.path.join(memories_dir, "last_action.json")
                    with open(log_path, 'w', encoding='utf-8') as f:
                        json.dump(log_data, f, ensure_ascii=False, indent=2)
                    print(f"📝 Лог збережено в: last_action.json")
                    
                    # 3. Відправляємо в Telegram
                    try:
                        import sys
                        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
                        if root_path not in sys.path:
                            sys.path.append(root_path)
                        from Atlas_v2.agent_skills.telegram_bridge.manifest import send_telegram_file
                        
                        caption = f"📸 ATLAS: Скріншот екрана (Gesture 'L')\n\nJSON Лог:\n{json.dumps(log_data, ensure_ascii=False, indent=2)}"
                        send_telegram_file(file_path, caption=caption)
                    except Exception as ex:
                        print(f"⚠️ Не вдалося відправити скріншот в Telegram: {ex}")
            except Exception as e:
                print(f"⚠️ [ActionWorker Error]: {e}")

if __name__ == "__main__":
    print("[VISION] Спроба запуску: logic.py напряму...")
    vision = VisionManager()
    vision.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Зупиняю VisionManager...")
        vision.stop()
