import cv2
import time
from camera_manager import CameraManager
from gesture_detector import GestureStateMachine
from alert_sender import send_alert, send_live_snapshot

def main():
    cam = CameraManager(source=0, fps=10)
    detectors = {} # Map of hand_id -> {detector, last_seen, last_pos}
    next_id = 0
    last_live_send = 0

    print("[Ankurah Detector] Starting Multi-Hand Mode... Press Ctrl+C to stop.")

    while True:
        ret, frame = cam.cap.read()
        if not ret: break

        now = time.time()
        
        # Periodic Live Heartbeat (every 1.5 seconds)
        if now - last_live_send > 1.5:
            send_live_snapshot(frame)
            last_live_send = now

        hands_data = cam.get_landmarks(frame)
        
        current_frame_ids = []
        
        for hand in hands_data:
            lm = hand['landmarks']
            h_type = hand['handedness']
            # Use wrist (landmark 0) for tracking
            pos = (lm.landmark[0].x, lm.landmark[0].y)
            
            # 1. Match to existing detector
            best_match_id = None
            min_dist = 0.15 # Max distance to consider a match
            
            for d_id, d_info in detectors.items():
                if d_info['handedness'] == h_type:
                    dist = ((pos[0] - d_info['pos'][0])**2 + (pos[1] - d_info['pos'][1])**2)**0.5
                    if dist < min_dist:
                        min_dist = dist
                        best_match_id = d_id
            
            # 2. Update or Create
            if best_match_id is not None:
                d_id = best_match_id
                detectors[d_id]['pos'] = pos
                detectors[d_id]['last_seen'] = now
            else:
                d_id = next_id
                next_id += 1
                detectors[d_id] = {
                    'detector': GestureStateMachine(on_alert=lambda confidence: send_alert(confidence, frame)),
                    'pos': pos,
                    'last_seen': now,
                    'handedness': h_type
                }
            
            current_frame_ids.append(d_id)
            state, debug = detectors[d_id]['detector'].update(lm, handedness=h_type)
            
            # 3. UI Overlay for this hand
            cam.draw_landmarks(frame, lm)
            
            # Draw status text near the hand
            h, w, _ = frame.shape
            px, py = int(pos[0] * w), int(pos[1] * h)
            color = (0, 255, 0) if state == "IDLE" else (0, 0, 255)
            cv2.putText(frame, f"ID:{d_id} {state}", (px, py - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            if debug['palm_open']:
                cv2.circle(frame, (px, py - 45), 5, (0, 255, 0), -1)

        # 4. Cleanup old detectors (stale > 2s)
        to_delete = [d_id for d_id, info in detectors.items() if now - info['last_seen'] > 2.0]
        for d_id in to_delete:
            del detectors[d_id]

        # Global Status
        cv2.putText(frame, f"Active Hands: {len(detectors)}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow("Ankurah — Multi-Hand Detector", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cam.release()

if __name__ == "__main__":
    main()
