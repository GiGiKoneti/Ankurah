import cv2
import mediapipe as mp

class CameraManager:
    def __init__(self, source=0, fps=10):
        self.cap = cv2.VideoCapture(source)
        self.fps = fps
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils

    def get_landmarks(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb)
        if result.multi_hand_landmarks:
            landmarks = result.multi_hand_landmarks[0]
            # Extract handedness (label is 'Left' or 'Right')
            handedness = result.multi_handedness[0].classification[0].label
            return landmarks, handedness
        return None, None

    def draw_landmarks(self, frame, landmarks):
        if landmarks:
            self.mp_draw.draw_landmarks(
                frame,
                landmarks,
                self.mp_hands.HAND_CONNECTIONS
            )
        return frame

    def release(self):
        self.cap.release()
        cv2.destroyAllWindows()
