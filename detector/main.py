import cv2
import time
from camera_manager import CameraManager
from gesture_detector import GestureStateMachine
from alert_sender import send_alert

def main():
    cam = CameraManager(source=0, fps=10)
    detector = GestureStateMachine(on_alert=send_alert)

    print("[Ankurah Detector] Starting... Press Q to quit.")

    frame_interval = 1.0 / 10  # 10 FPS
    last_frame_time = 0

    while True:
        ret, frame = cam.cap.read()
        if not ret:
            print("[ERROR] Cannot read from camera")
            break

        now = time.time()
        if now - last_frame_time < frame_interval:
            continue
        last_frame_time = now

        landmarks, handedness = cam.get_landmarks(frame)
        state = detector.update(landmarks, handedness) if landmarks else "IDLE"

        frame = cam.draw_landmarks(frame, landmarks)
        
        # Debug overlay — remove before final demo
        if landmarks:
            palm = detector._palm_open(landmarks)
            thumb = detector._thumb_tucked(landmarks)
            fist = detector._fist_closed(landmarks)
            
            cv2.putText(frame, f"Palm open: {palm}", (10, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0,255,0) if palm else (0,0,255), 2)
            cv2.putText(frame, f"Thumb tucked: {thumb}", (10, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0,255,0) if thumb else (0,0,255), 2)
            cv2.putText(frame, f"Fist closed: {fist}", (10, 130),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0,255,0) if fist else (0,0,255), 2)

        cv2.putText(frame, f"State: {state}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (0, 255, 0) if state == "IDLE" else (0, 0, 255), 2)
        cv2.imshow("Ankurah — Detector", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.release()

if __name__ == "__main__":
    main()
