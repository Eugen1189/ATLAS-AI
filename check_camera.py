import cv2

def list_cameras():
    print("🔍 Scanning for cameras...")
    available_cameras = []
    for i in range(10):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"✅ Camera Index {i}: Working (Resolution: {int(cap.get(3))}x{int(cap.get(4))})")
                available_cameras.append(i)
            else:
                print(f"⚠️ Camera Index {i}: Opened but failed to read frame")
            cap.release()
        else:
            print(f"❌ Camera Index {i}: Not found or unavailable")
    
    print("\n📋 Summary:")
    if available_cameras:
        print(f"Available Camera Indices: {available_cameras}")
        print("Try changing 'self.cap = cv2.VideoCapture(INDEX)' in core/vision_manager.py to one of these.")
    else:
        print("❌ No cameras found!")

if __name__ == "__main__":
    list_cameras()
