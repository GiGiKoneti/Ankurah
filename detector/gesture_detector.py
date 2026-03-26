import time
import math

class GestureStateMachine:
    HOLD_SECONDS = 0.8  # Responsive hold
    COOLDOWN = 10.0
    POSE_TIMEOUT = 3.0

    def __init__(self, on_alert):
        self.state = "IDLE"
        self.step_start = None
        self.last_alert = 0
        self.on_alert = on_alert

    def update(self, landmarks, handedness):
        now = time.time()

        if now - self.last_alert < self.COOLDOWN:
            return self.state

        if landmarks is None:
            if self.state != "IDLE" and self.step_start and (now - self.step_start > self.POSE_TIMEOUT):
                self._transition("IDLE", now)
            return self.state

        # State Machine Logic
        if self.state == "IDLE":
            if self._palm_open(landmarks):
                self._transition("STEP1", now)

        elif self.state == "STEP1":
            if self._thumb_tucked(landmarks):
                if now - self.step_start >= self.HOLD_SECONDS:
                    self._transition("STEP2", now)
            elif not self._palm_open(landmarks):
                if now - self.step_start > 1.0:
                    self._transition("IDLE", now)

        elif self.state == "STEP2":
            if self._fist_closed(landmarks):
                if now - self.step_start >= self.HOLD_SECONDS:
                    self.last_alert = now
                    self._transition("IDLE", now)
                    self.on_alert(confidence=0.98)
            elif self._palm_open(landmarks) and not self._thumb_tucked(landmarks):
                self._transition("STEP1", now)
            elif not self._palm_open(landmarks) and not self._fist_closed(landmarks):
                if now - self.step_start > self.POSE_TIMEOUT:
                    self._transition("IDLE", now)

        return self.state

    def _transition(self, new_state, now):
        if self.state != new_state:
            print(f"[STATE] {self.state} → {new_state}")
            self.state = new_state
            self.step_start = now

    def _palm_open(self, lm):
        """All 4 fingers extended — tip far from wrist"""
        wrist = lm.landmark[0]
        tips = [8, 12, 16, 20]
        mcps = [5, 9, 13, 17]
        
        extended = 0
        for tip_i, mcp_i in zip(tips, mcps):
            tip_dist = self._dist(lm.landmark[tip_i], wrist)
            mcp_dist = self._dist(lm.landmark[mcp_i], wrist)
            if tip_dist > mcp_dist * 1.5:
                extended += 1
        return extended >= 3

    def _thumb_tucked(self, lm):
        """Thumb tip is close to index/middle knuckle — tucked across palm"""
        thumb_tip = lm.landmark[4]
        index_mcp = lm.landmark[5]
        middle_mcp = lm.landmark[9]
        
        dist_to_index = self._dist(thumb_tip, index_mcp)
        dist_to_middle = self._dist(thumb_tip, middle_mcp)
        palm_width = self._dist(lm.landmark[5], lm.landmark[17])
        
        return (dist_to_index < palm_width * 0.6 or 
                dist_to_middle < palm_width * 0.6)

    def _fist_closed(self, lm):
        """All fingers curled — tips close to palm center"""
        mcps = [lm.landmark[5], lm.landmark[9], lm.landmark[13], lm.landmark[17]]
        palm_cx = sum(m.x for m in mcps) / 4
        palm_cy = sum(m.y for m in mcps) / 4
        
        class FakeLm:
            def __init__(self, x, y): self.x = x; self.y = y
        palm_center = FakeLm(palm_cx, palm_cy)
        
        tips = [8, 12, 16, 20]
        palm_width = self._dist(lm.landmark[5], lm.landmark[17])
        
        curled = 0
        for tip_i in tips:
            dist = self._dist(lm.landmark[tip_i], palm_center)
            if dist < palm_width * 0.9:
                curled += 1
        return curled >= 3

    def _dist(self, a, b):
        return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)
