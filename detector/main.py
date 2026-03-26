import cv2
import time
from camera_manager import CameraManager
from gesture_detector import GestureStateMachine
from alert_sender import send_alert

def main():
    cam = CameraManager(source=0, fps=10)
    detector = GestureStateMachine(on_alert=send_alert)

    print("[Ankurah Detector] Starting... Press Ctrl+C to stop.")

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
        
        if landmarks:
            state, debug = detector.update(landmarks, handedness=handedness)
        else:
            state = detector.state
            debug = detector.get_empty_debug()

        frame = cam.draw_landmarks(frame, landmarks)
        
        # State display
        color = (0, 255, 0) if state == "IDLE" else (0, 0, 255)
        cv2.putText(frame, f"State: {state}", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)

        # Debug Overlay
        y0, dy = 80, 25
        
        p_color = (0,255,0) if debug['palm_open'] else (0,0,255)
        cv2.putText(frame, f"PALM OPEN: {debug['palm_open']}", (10, y0),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, p_color, 2)
        
        t_color = (0,255,0) if debug['thumb_tucked'] else (0,0,255)
        cv2.putText(frame, f"THUMB TUCKED: {debug['thumb_tucked']}", (10, y0 + dy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, t_color, 2)
        cv2.putText(frame, f"  > IP Angle: {debug['thumb_ip_angle']:.1f}", (10, y0 + 2*dy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
        cv2.putText(frame, f"  > Plane Dist: {debug['thumb_signed_dist']:.3f}", (10, y0 + 3*dy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
        cv2.putText(frame, f"  > Lateral T: {debug['thumb_lateral_t']:.3f}", (10, y0 + 4*dy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

        f_color = (0,255,0) if debug['fist_closed'] else (0,0,255)
        cv2.putText(frame, f"FIST CLOSED: {debug['fist_closed']}", (10, y0 + 6*dy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, f_color, 2)
        cv2.putText(frame, f"  > Curled: {debug['fist_curled_count']}/4", (10, y0 + 7*dy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
        cv2.putText(frame, f"  > Depth: {debug['fist_depth_count']}/2", (10, y0 + 8*dy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

        cv2.imshow("Ankurah — Detector", frame)
        cv2.waitKey(1)

    cam.release()

if __name__ == "__main__":
    main()
