import time
import math
import numpy as np

class GestureStateMachine:
    # Tunable constants
    FINGER_EXTENDED_ANGLE  = 150   # lowered from 160 for better tolerance
    FINGER_CURLED_ANGLE    = 100   
    THUMB_IP_BENT_ANGLE    = 155   
    THUMB_PLANE_DIST       = 0.20  # increased from 0.08 — video analysis showed thumb at -0.12 to -0.17
    THUMB_LATERAL_MIN      = 0.1   
    THUMB_LATERAL_MAX      = 1.1   
    
    HOLD_SECONDS           = 1.0   
    STEP_TIMEOUT           = 8.0   
    COOLDOWN               = 4.0  
    MIN_CONFIDENCE         = 0.70  
    RESET_GRACE            = 0.4   # seconds of "bad data" before we actually reset

    def __init__(self, on_alert):
        self.state = "IDLE"
        self.step_start = None
        self.last_step_time = None
        self.last_alert = 0
        self.on_alert = on_alert
        self._step_history = []
        self.last_valid_time = time.time() # Tracker for stabilization

    # ─────────────────────────────────────────────
    # Main update — call every frame with raw landmarks
    # ─────────────────────────────────────────────
    def update(self, raw_landmarks, hand_confidence=1.0, handedness="Right"):
        now = time.time()

        # Global cooldown and confidence gate
        if now - self.last_alert < self.COOLDOWN or hand_confidence < self.MIN_CONFIDENCE:
            return self.state, self.get_empty_debug()

        if raw_landmarks is None:
            if self.state != "IDLE" and self.last_step_time and now - self.last_step_time > self.STEP_TIMEOUT:
                self._reset(now)
            return self.state, self.get_empty_debug()

        # Step timeout
        if (self.state != "IDLE" and 
            self.last_step_time and 
            now - self.last_step_time > self.STEP_TIMEOUT):
            self._reset(now)
            return self.state, self.get_empty_debug()

        # STEP 0: Preprocessing/Normalization
        lm = self._normalize(raw_landmarks)

        # STEP 1: Evaluate gestures using math framework
        palm_open, palm_dbg       = self._palm_open(lm)
        thumb_tucked, thumb_dbg   = self._thumb_tucked(lm, handedness)
        fist_closed, fist_dbg     = self._fist_closed(lm)

        # ── State transitions with Hysteresis ──────
        if self.state == "IDLE":
            if palm_open and not thumb_tucked:
                self._transition("STEP1", now)
            self.last_valid_time = now

        elif self.state == "STEP1":
            held_enough = (now - self.step_start) >= self.HOLD_SECONDS
            
            # Valid patterns for STEP1: stay in palm open or start tucking
            if palm_open or thumb_tucked:
                self.last_valid_time = now
            
            # Reset only if hand is completely idle/fist for too long
            if not palm_open and not thumb_tucked:
                if now - self.last_valid_time > self.RESET_GRACE:
                    self._reset(now)
            
            # Advance to STEP2
            if held_enough and thumb_tucked:
                self.last_step_time = now
                self._step_history.append("STEP1")
                self._transition("STEP2", now)

        elif self.state == "STEP2":
            held_enough = (now - self.step_start) >= self.HOLD_SECONDS
            
            # Valid patterns for STEP2: thumb remains tucked or fist starts closing
            if thumb_tucked or fist_closed:
                self.last_valid_time = now
            
            # Jump back to STEP1 if they re-open palm
            if palm_open and not thumb_tucked:
                if now - self.last_valid_time > self.RESET_GRACE:
                    self._transition("STEP1", now)
            
            # Reset if hand leaves sequence pattern for too long
            elif not thumb_tucked and not fist_closed:
                if now - self.last_valid_time > self.RESET_GRACE:
                    self._reset(now)
            
            # Final Alert
            if held_enough and fist_closed:
                if self._validate_sequence():
                    self.last_step_time = now
                    self._step_history.append("STEP2")
                    self.last_alert = now
                    self._reset(now)
                    self.on_alert(confidence=0.95)
                    print("[ALERT] Valid Signal for Help confirmed")
                else:
                    self._reset(now)

        # Build merged debug dict for main.py
        debug_dict = {
            "palm_open": palm_open,
            "palm_angles": palm_dbg["angles"],
            "thumb_tucked": thumb_tucked,
            "thumb_ip_angle": thumb_dbg["ip_angle"],
            "thumb_signed_dist": thumb_dbg["signed_dist"],
            "thumb_lateral_t": thumb_dbg["lateral_t"],
            "fist_closed": fist_closed,
            "fist_angles": fist_dbg["angles"],
            "fist_curled_count": fist_dbg["curled_count"],
            "fist_depth_count": fist_dbg["depth_count"]
        }

        return self.state, debug_dict

    # ─────────────────────────────────────────────
    # Mathematical Framework Methods
    # ─────────────────────────────────────────────

    def _normalize(self, landmarks):
        """Converts raw landmarks to scaled, wrist-centered numpy array (21, 3)"""
        # landmarks is expected to be a list/object with .x, .y, .z
        # If it's the raw Mediapipe NormalizedLandmarkList, we access .landmark
        pts = np.array([[l.x, l.y, l.z] for l in (landmarks.landmark if hasattr(landmarks, 'landmark') else landmarks)])
        origin = pts[0]
        pts = pts - origin
        # Scale by distance from wrist (0) to middle MCP (9)
        scale = np.linalg.norm(pts[9]) + 1e-6
        return pts / scale

    def calculate_angle(self, a, b, c):
        """Angle in degrees at joint B in chain A-B-C"""
        ba = a - b
        bc = c - b
        dot = np.dot(ba, bc)
        denom = np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6
        cos_angle = np.clip(dot / denom, -1.0, 1.0)
        return math.degrees(math.acos(cos_angle))

    def _palm_open(self, lm):
        """At least 3 fingers extended > 160°, thumb not tucked"""
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        mcps = [5, 9, 13, 17]
        
        angles = []
        for t, p, m in zip(tips, pips, mcps):
            angles.append(self.calculate_angle(lm[m], lm[p], lm[t]))
            
        extended_count = sum(1 for a in angles if a > self.FINGER_EXTENDED_ANGLE)
        
        thumb_tucked, _ = self._thumb_tucked(lm)
        # DECISION: We no longer invalidate palm_open based on thumb_tucked.
        # This allows entering STEP1 reliably. STEP2 will still require a tuck.
        is_open = (extended_count >= 3)
        return is_open, {"angles": angles, "extended": extended_count, "thumb_tucked": thumb_tucked}

    def _thumb_tucked(self, lm, handedness="Right"):
        """Thumb IP bent + close to palm plane + middle of palm laterally"""
        # Condition A: IP Joint bent (<155)
        ip_angle = self.calculate_angle(lm[2], lm[3], lm[4])
        cond_a = ip_angle < self.FINGER_EXTENDED_ANGLE # User requested <155 but noted straight as ~180
        # Actually user explicitly said: bent = angle < 155
        cond_a = ip_angle < self.THUMB_IP_BENT_ANGLE

        # Condition B: Near palm plane
        # Wrist(0), IndexMCP(5), PinkyMCP(17)
        v1 = lm[5] - lm[0]
        v2 = lm[17] - lm[0]
        n = np.cross(v1, v2)
        n_hat = n / (np.linalg.norm(n) + 1e-6)
        
        signed_dist = np.dot(n_hat, lm[4] - lm[0])
        if handedness == "Left":
            signed_dist = -signed_dist
            
        cond_b = abs(signed_dist) < self.THUMB_PLANE_DIST

        # Condition C: Mid-palm laterally
        # Project tip(4) onto IndexMCP(5) -> PinkyMCP(17) axis
        axis = lm[17] - lm[5]
        t = np.dot(lm[4] - lm[5], axis) / (np.linalg.norm(axis)**2 + 1e-6)
        cond_c = self.THUMB_LATERAL_MIN < t < self.THUMB_LATERAL_MAX

        is_tucked = cond_a and cond_b and cond_c
        return is_tucked, {
            "ip_angle": ip_angle, 
            "signed_dist": signed_dist, 
            "lateral_t": t,
            "cond_A": cond_a, "cond_B": cond_b, "cond_C": cond_c
        }

    def _fist_closed(self, lm):
        """3+ fingers curled < 100° + depth confirmation (tip deeper than MCP)"""
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        mcps = [5, 9, 13, 17]
        
        angles = []
        for t, p, m in zip(tips, pips, mcps):
            angles.append(self.calculate_angle(lm[m], lm[p], lm[t]))
            
        curled_count = sum(1 for a in angles if a < self.FINGER_CURLED_ANGLE)
        # Depth check: curled tips should be significantly different in Z than MCPs
        # We check for absolute difference to handle both palm-forward and back-of-hand-forward
        depth_count = sum(1 for t, m in zip(tips, mcps) if abs(lm[t][2] - lm[m][2]) > 0.01)
        
        is_fist = (curled_count >= 3) and (depth_count >= 2)
        return is_fist, {
            "angles": angles, 
            "curled_count": curled_count, 
            "depth_count": depth_count
        }

    # ─────────────────────────────────────────────
    # Helpers & State
    # ─────────────────────────────────────────────

    def _validate_sequence(self):
        return "STEP1" in self._step_history

    def _transition(self, new_state, now):
        print(f"[STATE] {self.state} → {new_state}")
        self.state = new_state
        self.step_start = now

    def _reset(self, now):
        self.state = "IDLE"
        self.step_start = None
        self._step_history = []
        self.last_step_time = None

    def get_empty_debug(self):
        return {
            "palm_open": False, "palm_angles": [0]*4,
            "thumb_tucked": False, "thumb_ip_angle": 0, "thumb_signed_dist": 0, "thumb_lateral_t": 0,
            "fist_closed": False, "fist_angles": [0]*4, "fist_curled_count": 0, "fist_depth_count": 0
        }
