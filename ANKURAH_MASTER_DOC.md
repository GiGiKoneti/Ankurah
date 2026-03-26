
# Ankurah — Master Project Documentation
### Team: TLE_cursed | Hackathon: Build-Ora | Track: Agentic AI

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Monorepo Structure](#3-monorepo-structure)
4. [Network & IP Contract](#4-network--ip-contract)
5. [API Contract — Every Endpoint](#5-api-contract--every-endpoint)
6. [Folder 1: detector/ — GiGi (Mac M1)](#6-folder-1-detector--gigi-mac-m1)
7. [Folder 2: backend/ — Varchas (Arch Linux)](#7-folder-2-backend--varchas-arch-linux)
8. [Folder 3: frontend/ — Surakshan (Windows 11)](#8-folder-3-frontend--surakshan-windows-11)
9. [Integration Points — How Everything Links](#9-integration-points--how-everything-links)
10. [Environment Variables — Shared .env Contract](#10-environment-variables--shared-env-contract)
11. [Demo Run Instructions](#11-demo-run-instructions)
12. [Vibe Coding Rules — Avoiding Mistakes](#12-vibe-coding-rules--avoiding-mistakes)
13. [Camera Registry — Hardcoded for Demo](#13-camera-registry--hardcoded-for-demo)
14. [Deliverables Checklist Per Person](#14-deliverables-checklist-per-person)

---

## 1. Project Overview

**Ankurah** converts existing public CCTV infrastructure into a proactive women's safety network.

**The flow in one sentence:**
> A victim performs the internationally-recognized Signal for Help gesture in front of any CCTV camera → AI detects it silently → Police control room dashboard lights up → Nearest officer gets SMS + Discord alert with exact GPS location → Officer dispatches immediately.

**Who touches what during a real distress event:**
- Victim — nothing. Just the gesture.
- CCTV camera — already running, sees the gesture.
- GiGi's detector — running silently on Mac, sees the gesture in the frame.
- Varchas's backend — receives the confirmed alert, fires notifications.
- Surakshan's dashboard — lights up red in the police control room.
- Officer's phone — receives Discord ping + Google Maps link.

---

## 2. System Architecture

```
[CCTV / Webcam]
      |
      | RTSP stream / cv2.VideoCapture(0)
      |
[GiGi's Mac M1 — detector/]
      |  OpenCV reads frames at 10 FPS
      |  MediaPipe extracts 21 hand keypoints
      |  State Machine: IDLE → STEP1 → STEP2 → ALERT
      |
      | HTTP POST /alert  (JSON payload)
      |
[Varchas's Mac M1 — backend/]  ← backend also runs on Mac for demo
      |  FastAPI receives alert
      |  Fires Discord webhook
      |  Pushes SSE event to all connected dashboard clients
      |
      |— SSE stream ——→ [Surakshan's Windows — frontend/dashboard]
      |                   React Police Control Room Dashboard
      |                   Live map (Google Maps), alert log,
      |                   camera status, confidence scores
      |
      |— Discord ——→ [Officer's Phone]
                      Ping with camera name, location, Maps link
```

**During demo, all three run on the SAME Mac M1 (GiGi's laptop):**
- detector/ runs as one terminal process
- backend/ runs as another terminal process
- frontend/ runs in browser at localhost:5173
- All communicate via localhost

Surakshan's Windows laptop opens the dashboard in browser, connected to Mac's IP over WiFi.
Officer phone (any team member's phone) is added to Discord server to receive alerts.

---

## 3. Monorepo Structure

```
Ankurah/                        ← root of the GitHub monorepo
│
├── README.md                     ← brief project description + how to run
├── .env.example                  ← template for all env variables (no secrets)
├── MASTER_DOC.md                 ← this file
│
├── detector/                     ← GiGi's folder (Mac M1, Python)
│   ├── requirements.txt
│   ├── .env                      ← local copy, never committed
│   ├── main.py                   ← entry point, starts camera loop
│   ├── gesture_detector.py       ← MediaPipe + state machine logic
│   ├── camera_manager.py         ← OpenCV capture, frame sampling
│   ├── alert_sender.py           ← HTTP POST to backend /alert
│   └── config.py                 ← loads env vars, camera registry
│
├── backend/                      ← Varchas's folder (runs on Mac for demo)
│   ├── requirements.txt
│   ├── .env                      ← local copy, never committed
│   ├── main.py                   ← FastAPI app entry point
│   ├── routes/
│   │   ├── alert.py              ← POST /alert endpoint
│   │   ├── stream.py             ← GET /stream SSE endpoint
│   │   ├── cameras.py            ← GET /cameras endpoint
│   │   └── health.py             ← GET /health endpoint
│   ├── services/
│   │   ├── discord_service.py    ← Discord webhook logic
│   │   └── sse_manager.py        ← SSE broadcast manager
│   └── models.py                 ← Pydantic request/response models
│
└── frontend/                     ← Surakshan's folder (React, Vite)
    ├── package.json
    ├── vite.config.js
    ├── .env                      ← VITE_BACKEND_URL, VITE_GMAPS_KEY
    ├── public/
    │   └── manifest.json         ← PWA manifest
    ├── src/
    │   ├── main.jsx
    │   ├── App.jsx               ← root, sets up routes
    │   ├── components/
    │   │   ├── Dashboard.jsx     ← main police control room view
    │   │   ├── AlertLog.jsx      ← scrollable alert history table
    │   │   ├── CameraGrid.jsx    ← live status cards per camera
    │   │   ├── AlertMap.jsx      ← Google Maps with red pins
    │   │   ├── ThreatBanner.jsx  ← full-width red alert banner
    │   │   └── ConfidenceBadge.jsx
    │   ├── hooks/
    │   │   └── useSSE.js         ← connects to backend /stream SSE
    │   └── constants/
    │       └── cameras.js        ← camera registry (mirrors backend)
```

---

## 4. Network & IP Contract

**During demo, all processes run on GiGi's Mac M1.**

| Service | Host | Port | URL |
|---------|------|------|-----|
| FastAPI backend | Mac M1 | 8000 | http://localhost:8000 |
| React dashboard (dev) | Mac M1 | 5173 | http://localhost:5173 |
| Detector | Mac M1 | — | runs as background process, no port |

**For Surakshan's Windows to see the dashboard over WiFi:**
1. GiGi runs `vite --host` instead of just `vite`
2. Mac's WiFi IP (e.g. `192.168.1.10`) is shared in group chat
3. Surakshan opens `http://192.168.1.10:5173` on Windows browser
4. Officer phone opens same URL — this is the PWA mobile experience

**To find Mac's IP:**
```bash
ipconfig getifaddr en0
```

**CORS:** Backend must allow all origins during hackathon. Varchas sets this in FastAPI.

---

## 5. API Contract — Every Endpoint

This section is the CONTRACT. GiGi and Surakshan read this to know exactly what Varchas builds. Varchas reads this to know exactly what shape of data he must accept and return. Nobody deviates from these shapes.

---

### POST /alert
**Called by:** GiGi's detector when gesture is confirmed.
**Purpose:** Receive distress alert, fire Discord, broadcast SSE to all dashboard clients.

**Request body (JSON):**
```json
{
  "camera_id": "CAM-01",
  "confidence": 0.95,
  "timestamp": "2024-01-15T14:32:07.123Z",
  "lat": 12.9747,
  "lng": 77.6094,
  "location_name": "MG Road Junction"
}
```

**Response (JSON):**
```json
{
  "status": "ok",
  "alert_id": "alert_1705329127"
}
```

**What Varchas does inside this endpoint:**
1. Validate payload with Pydantic
2. Fire Discord webhook (async, non-blocking)
3. Push SSE event to all connected dashboard clients
4. Return response immediately (do not wait for Discord to confirm)

---

### GET /stream
**Called by:** Surakshan's React dashboard (useSSE hook).
**Purpose:** Server-Sent Events stream. Pushes real-time alert events to the dashboard.

**Headers required:**
```
Accept: text/event-stream
Cache-Control: no-cache
```

**Event format pushed by server:**
```
data: {"type":"alert","camera_id":"CAM-01","confidence":0.95,"timestamp":"2024-01-15T14:32:07Z","lat":12.9747,"lng":77.6094,"location_name":"MG Road Junction"}

data: {"type":"heartbeat","ts":"2024-01-15T14:32:10Z"}
```

**Rules:**
- Heartbeat event every 5 seconds so browser knows connection is alive
- Alert event fires every time POST /alert is received
- Connection stays open indefinitely — never closes from server side

---

### GET /cameras
**Called by:** Surakshan's dashboard on page load.
**Purpose:** Get list of all registered cameras with their status and location.

**Response (JSON):**
```json
{
  "cameras": [
    {
      "camera_id": "CAM-01",
      "location_name": "MG Road Junction",
      "lat": 12.9747,
      "lng": 77.6094,
      "status": "active",
      "last_seen": "2024-01-15T14:32:07Z"
    },
    {
      "camera_id": "CAM-02",
      "location_name": "Koramangala Market",
      "lat": 12.9352,
      "lng": 77.6245,
      "status": "active",
      "last_seen": "2024-01-15T14:31:55Z"
    },
    {
      "camera_id": "CAM-03",
      "location_name": "Indiranagar Metro",
      "lat": 12.9784,
      "lng": 77.6408,
      "status": "active",
      "last_seen": "2024-01-15T14:31:50Z"
    }
  ]
}
```

---

### GET /health
**Called by:** Anyone, for debugging during hackathon.
**Purpose:** Check if backend is alive.

**Response (JSON):**
```json
{
  "status": "ok",
  "uptime_seconds": 3421,
  "alerts_fired": 3
}
```

---

### GET /alerts
**Called by:** Surakshan's dashboard on page load to hydrate alert log.
**Purpose:** Returns last 50 alerts that fired since server started (in-memory, no DB needed).

**Response (JSON):**
```json
{
  "alerts": [
    {
      "alert_id": "alert_1705329127",
      "camera_id": "CAM-01",
      "confidence": 0.95,
      "timestamp": "2024-01-15T14:32:07Z",
      "lat": 12.9747,
      "lng": 77.6094,
      "location_name": "MG Road Junction"
    }
  ]
}
```

---

## 6. Folder 1: detector/ — GiGi (Mac M1)

### Your job
Build the AI detection engine. It runs as a Python script. It watches the webcam. When the Signal for Help gesture is fully confirmed, it calls `alert_sender.py` which POSTs to Varchas's backend. That's it.

### Your deliverables
- [ ] Webcam opens and shows live feed with MediaPipe landmark overlay
- [ ] State machine correctly transitions IDLE → STEP1 → STEP2 → ALERT
- [ ] Each step requires 1.5s hold at confidence > 0.7 to advance
- [ ] Alert fires exactly ONCE per gesture (10s cooldown prevents spam)
- [ ] Terminal prints state changes clearly: `[STATE] IDLE → STEP1` etc.
- [ ] Alert POST reaches backend successfully (test with curl first)

### Python setup (Mac M1 — Apple Silicon specific)

```bash
cd detector/
python3 -m venv venv
source venv/bin/activate

# MediaPipe on M1 requires this specific install order
pip install opencv-python
pip install mediapipe
pip install requests
pip install python-dotenv
```

**M1 gotcha:** If `import mediapipe` crashes, use:
```bash
pip install mediapipe-silicon
```

### requirements.txt
```
opencv-python==4.8.1.78
mediapipe==0.10.7
requests==2.31.0
python-dotenv==1.0.0
```

### config.py
```python
import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
CAMERA_ID = os.getenv("CAMERA_ID", "CAM-01")

CAMERA_REGISTRY = {
    "CAM-01": {
        "location_name": "MG Road Junction",
        "lat": 12.9747,
        "lng": 77.6094
    },
    "CAM-02": {
        "location_name": "Koramangala Market",
        "lat": 12.9352,
        "lng": 77.6245
    },
    "CAM-03": {
        "location_name": "Indiranagar Metro",
        "lat": 12.9784,
        "lng": 77.6408
    }
}
```

### gesture_detector.py
```python
import time

class GestureStateMachine:
    HOLD_SECONDS = 1.5
    COOLDOWN = 10.0

    def __init__(self, on_alert):
        self.state = "IDLE"
        self.step_start = None
        self.last_alert = 0
        self.on_alert = on_alert

    def update(self, landmarks):
        now = time.time()

        # Cooldown guard
        if now - self.last_alert < self.COOLDOWN:
            return self.state

        if self.state == "IDLE":
            if self._palm_open(landmarks):
                self._transition("STEP1", now)

        elif self.state == "STEP1":
            if not self._palm_open(landmarks):
                self._transition("IDLE", now)
            elif (now - self.step_start >= self.HOLD_SECONDS
                  and self._thumb_tucked(landmarks)):
                self._transition("STEP2", now)

        elif self.state == "STEP2":
            if (now - self.step_start >= self.HOLD_SECONDS
                    and self._fist_closed(landmarks)):
                self.last_alert = now
                self._transition("IDLE", now)
                self.on_alert(confidence=0.95)

        return self.state

    def _transition(self, new_state, now):
        print(f"[STATE] {self.state} → {new_state}")
        self.state = new_state
        self.step_start = now

    def _palm_open(self, lm):
        # All four finger tips above their PIP joints (y axis inverted in image)
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        return all(lm[tips[i]].y < lm[pips[i]].y for i in range(4))

    def _thumb_tucked(self, lm):
        # Thumb tip x crosses over to palm side (right hand facing camera)
        return lm[4].x > lm[3].x

    def _fist_closed(self, lm):
        # All four finger tips below their PIP joints
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        return all(lm[tips[i]].y > lm[pips[i]].y for i in range(4))
```

### camera_manager.py
```python
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
            return result.multi_hand_landmarks[0].landmark
        return None

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
```

### alert_sender.py
```python
import requests
from datetime import datetime, timezone
from config import BACKEND_URL, CAMERA_ID, CAMERA_REGISTRY

def send_alert(confidence: float):
    camera = CAMERA_REGISTRY.get(CAMERA_ID, {})
    payload = {
        "camera_id": CAMERA_ID,
        "confidence": confidence,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lat": camera.get("lat", 12.9716),
        "lng": camera.get("lng", 77.5946),
        "location_name": camera.get("location_name", "Unknown Location")
    }
    try:
        r = requests.post(f"{BACKEND_URL}/alert", json=payload, timeout=3)
        print(f"[ALERT SENT] Status: {r.status_code} | {payload['location_name']}")
    except Exception as e:
        print(f"[ALERT FAILED] Could not reach backend: {e}")
```

### main.py
```python
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

        landmarks = cam.get_landmarks(frame)
        state = detector.update(landmarks) if landmarks else "IDLE"

        frame = cam.draw_landmarks(frame, landmarks)
        cv2.putText(frame, f"State: {state}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (0, 255, 0) if state == "IDLE" else (0, 0, 255), 2)
        cv2.imshow("Ankurah — Detector", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.release()

if __name__ == "__main__":
    main()
```

### detector/.env
```
BACKEND_URL=http://localhost:8000
CAMERA_ID=CAM-01
```

### How GiGi links to Varchas
GiGi's `alert_sender.py` calls `POST http://localhost:8000/alert` with the exact JSON shape defined in Section 5. That's the only integration point. GiGi should test this with:
```bash
curl -X POST http://localhost:8000/alert \
  -H "Content-Type: application/json" \
  -d '{"camera_id":"CAM-01","confidence":0.95,"timestamp":"2024-01-15T14:32:07Z","lat":12.9747,"lng":77.6094,"location_name":"MG Road Junction"}'
```
If Varchas's backend isn't ready yet, GiGi mocks it with a simple Flask server returning `{"status":"ok"}`.

---

## 7. Folder 2: backend/ — Varchas (Arch Linux)

### Your job
Build the FastAPI server. It receives alerts from GiGi's detector, fires Discord webhooks, and streams SSE events to Surakshan's dashboard. No database — all in-memory for the hackathon. Runs on the Mac M1 during demo.

### Your deliverables
- [ ] All endpoints in Section 5 return correct JSON shapes
- [ ] CORS allows all origins
- [ ] Discord webhook fires within 50ms of receiving /alert
- [ ] SSE stream sends heartbeat every 5 seconds
- [ ] SSE stream pushes alert event to all connected clients
- [ ] /alerts returns in-memory log of last 50 alerts
- [ ] Server starts cleanly with `uvicorn main:app --reload`

### Python setup (Arch Linux)
```bash
cd backend/
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn python-dotenv httpx
```

### requirements.txt
```
fastapi==0.104.1
uvicorn==0.24.0
python-dotenv==1.0.0
httpx==0.25.2
```

### models.py
```python
from pydantic import BaseModel
from typing import Optional

class AlertPayload(BaseModel):
    camera_id: str
    confidence: float
    timestamp: str
    lat: float
    lng: float
    location_name: str

class AlertResponse(BaseModel):
    status: str
    alert_id: str
```

### services/sse_manager.py
```python
import asyncio
import json
from typing import List

class SSEManager:
    def __init__(self):
        self.connections: List[asyncio.Queue] = []

    def connect(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self.connections.append(q)
        return q

    def disconnect(self, q: asyncio.Queue):
        if q in self.connections:
            self.connections.remove(q)

    async def broadcast(self, data: dict):
        event = f"data: {json.dumps(data)}\n\n"
        dead = []
        for q in self.connections:
            try:
                await q.put(event)
            except Exception:
                dead.append(q)
        for q in dead:
            self.connections.remove(q)

sse_manager = SSEManager()
```

### services/discord_service.py
```python
import httpx
import os

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

async def send_discord_alert(alert: dict):
    if not DISCORD_WEBHOOK_URL:
        print("[DISCORD] No webhook URL set, skipping")
        return

    maps_link = f"https://maps.google.com/?q={alert['lat']},{alert['lng']}"
    message = {
        "content": (
            f"🚨 **DISTRESS SIGNAL DETECTED**\n"
            f"📍 **{alert['location_name']}**\n"
            f"📷 Camera: `{alert['camera_id']}`\n"
            f"🎯 Confidence: `{int(alert['confidence']*100)}%`\n"
            f"🕐 Time: `{alert['timestamp']}`\n"
            f"🗺️ Navigate: {maps_link}"
        )
    }
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(DISCORD_WEBHOOK_URL, json=message, timeout=5)
            print(f"[DISCORD] Fired: {r.status_code}")
    except Exception as e:
        print(f"[DISCORD] Failed: {e}")
```

### routes/alert.py
```python
from fastapi import APIRouter
from models import AlertPayload, AlertResponse
from services.sse_manager import sse_manager
from services.discord_service import send_discord_alert
import asyncio
import time

router = APIRouter()
alert_log = []  # in-memory store

@router.post("/alert", response_model=AlertResponse)
async def receive_alert(payload: AlertPayload):
    alert_data = payload.dict()
    alert_id = f"alert_{int(time.time())}"
    alert_data["alert_id"] = alert_id

    # Store in memory
    alert_log.append(alert_data)
    if len(alert_log) > 50:
        alert_log.pop(0)

    # Fire Discord and SSE concurrently — don't await Discord before SSE
    asyncio.create_task(send_discord_alert(alert_data))
    asyncio.create_task(sse_manager.broadcast({
        "type": "alert",
        **alert_data
    }))

    return AlertResponse(status="ok", alert_id=alert_id)
```

### routes/stream.py
```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from services.sse_manager import sse_manager
import asyncio
import json
from datetime import datetime, timezone

router = APIRouter()

@router.get("/stream")
async def sse_stream():
    q = sse_manager.connect()

    async def event_generator():
        try:
            while True:
                try:
                    # Wait for event, but send heartbeat every 5s
                    event = await asyncio.wait_for(q.get(), timeout=5.0)
                    yield event
                except asyncio.TimeoutError:
                    # Send heartbeat
                    heartbeat = {
                        "type": "heartbeat",
                        "ts": datetime.now(timezone.utc).isoformat()
                    }
                    yield f"data: {json.dumps(heartbeat)}\n\n"
        except Exception:
            pass
        finally:
            sse_manager.disconnect(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )
```

### routes/cameras.py
```python
from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter()

CAMERAS = [
    {"camera_id": "CAM-01", "location_name": "MG Road Junction",
     "lat": 12.9747, "lng": 77.6094, "status": "active"},
    {"camera_id": "CAM-02", "location_name": "Koramangala Market",
     "lat": 12.9352, "lng": 77.6245, "status": "active"},
    {"camera_id": "CAM-03", "location_name": "Indiranagar Metro",
     "lat": 12.9784, "lng": 77.6408, "status": "active"},
]

@router.get("/cameras")
async def get_cameras():
    now = datetime.now(timezone.utc).isoformat()
    cameras = [{**c, "last_seen": now} for c in CAMERAS]
    return {"cameras": cameras}
```

### routes/health.py
```python
from fastapi import APIRouter
import time

router = APIRouter()
START_TIME = time.time()

@router.get("/health")
async def health():
    from routes.alert import alert_log
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME),
        "alerts_fired": len(alert_log)
    }
```

### routes/alerts.py (history)
```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/alerts")
async def get_alerts():
    from routes.alert import alert_log
    return {"alerts": list(reversed(alert_log))}
```

### main.py
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import alert, stream, cameras, health, alerts

app = FastAPI(title="Ankurah Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alert.router)
app.include_router(stream.router)
app.include_router(cameras.router)
app.include_router(health.router)
app.include_router(alerts.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### backend/.env
```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN
```

### How Varchas links to GiGi
Varchas reads the `AlertPayload` model. He never touches `detector/`. He just makes sure `POST /alert` accepts that exact shape and returns `{"status":"ok","alert_id":"..."}`.

### How Varchas links to Surakshan
Varchas makes sure:
1. `GET /stream` sends SSE events in the exact format defined in Section 5
2. CORS is fully open (allow_origins=["*"])
3. Server binds to `0.0.0.0` not `127.0.0.1` so WiFi devices can reach it

### Getting Discord webhook URL
1. Create a Discord server (free)
2. Go to channel settings → Integrations → Webhooks → New Webhook
3. Copy URL → paste in backend/.env
4. Add officer's phone to the Discord server — they get push notifications automatically

---

## 8. Folder 3: frontend/ — Surakshan (Windows 11)

### Your job
Build the React police control room dashboard AND the PWA that works on mobile (officer's phone). Both are the same React app — it's responsive. Dashboard view on desktop, simplified alert view on mobile.

### Your deliverables
- [ ] Dashboard loads at localhost:5173
- [ ] Connects to SSE stream and receives live events
- [ ] Alert log table shows: camera ID, location, confidence, timestamp
- [ ] Google Maps shows red pin when alert fires
- [ ] Full-width red banner appears on alert with camera name
- [ ] Camera status cards show all 3 cameras as "active"
- [ ] PWA installs on phone browser (manifest.json + service worker)
- [ ] Works over WiFi — connects to Mac's IP, not localhost

### Setup (Windows)
```bash
cd frontend/
npm create vite@latest . -- --template react
npm install
npm install react-leaflet leaflet
npm install @react-google-maps/api
npm install react-router-dom
```

Wait — you're using Google Maps. Use `@react-google-maps/api`:
```bash
npm install @react-google-maps/api
```

### frontend/.env
```
VITE_BACKEND_URL=http://localhost:8000
VITE_GMAPS_KEY=YOUR_GOOGLE_MAPS_API_KEY
```

For WiFi demo, change VITE_BACKEND_URL to Mac's IP:
```
VITE_BACKEND_URL=http://192.168.1.10:8000
```

### vite.config.js
```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,  // exposes on network, required for WiFi access
    port: 5173
  }
})
```

### hooks/useSSE.js
```javascript
import { useEffect, useState, useCallback } from 'react'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL

export function useSSE() {
  const [alerts, setAlerts] = useState([])
  const [latestAlert, setLatestAlert] = useState(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    const es = new EventSource(`${BACKEND_URL}/stream`)

    es.onopen = () => setConnected(true)

    es.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.type === 'alert') {
        setLatestAlert(data)
        setAlerts(prev => [data, ...prev].slice(0, 50))
      }
      // heartbeat — do nothing, connection alive
    }

    es.onerror = () => {
      setConnected(false)
      // EventSource auto-reconnects
    }

    return () => es.close()
  }, [])

  return { alerts, latestAlert, connected }
}
```

### components/ThreatBanner.jsx
```jsx
import { useEffect, useState } from 'react'

export function ThreatBanner({ latestAlert }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (latestAlert) {
      setVisible(true)
      const t = setTimeout(() => setVisible(false), 8000)
      return () => clearTimeout(t)
    }
  }, [latestAlert])

  if (!visible || !latestAlert) return null

  return (
    <div style={{
      background: '#DC2626',
      color: 'white',
      padding: '16px 24px',
      fontSize: '18px',
      fontWeight: 'bold',
      textAlign: 'center',
      animation: 'pulse 1s infinite'
    }}>
      🚨 DISTRESS SIGNAL — {latestAlert.location_name} | Camera {latestAlert.camera_id}
    </div>
  )
}
```

### components/AlertMap.jsx
```jsx
import { GoogleMap, useJsApiLoader, Marker } from '@react-google-maps/api'

const GMAPS_KEY = import.meta.env.VITE_GMAPS_KEY
const BENGALURU_CENTER = { lat: 12.9716, lng: 77.5946 }

export function AlertMap({ alerts }) {
  const { isLoaded } = useJsApiLoader({ googleMapsApiKey: GMAPS_KEY })

  if (!isLoaded) return <div>Loading map...</div>

  return (
    <GoogleMap
      mapContainerStyle={{ width: '100%', height: '400px' }}
      center={BENGALURU_CENTER}
      zoom={12}
    >
      {alerts.map((a, i) => (
        <Marker
          key={i}
          position={{ lat: a.lat, lng: a.lng }}
          title={`${a.location_name} — ${a.timestamp}`}
          icon={{
            url: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png'
          }}
        />
      ))}
    </GoogleMap>
  )
}
```

### components/AlertLog.jsx
```jsx
export function AlertLog({ alerts }) {
  if (alerts.length === 0) {
    return <p style={{ color: '#6B7280' }}>No alerts yet. Monitoring active.</p>
  }

  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
      <thead>
        <tr style={{ background: '#1F2937', color: 'white' }}>
          <th style={{ padding: '10px', textAlign: 'left' }}>Time</th>
          <th style={{ padding: '10px', textAlign: 'left' }}>Camera</th>
          <th style={{ padding: '10px', textAlign: 'left' }}>Location</th>
          <th style={{ padding: '10px', textAlign: 'left' }}>Confidence</th>
        </tr>
      </thead>
      <tbody>
        {alerts.map((a, i) => (
          <tr key={i} style={{
            background: i === 0 ? '#FEF2F2' : i % 2 === 0 ? '#F9FAFB' : 'white',
            borderBottom: '1px solid #E5E7EB'
          }}>
            <td style={{ padding: '10px' }}>{new Date(a.timestamp).toLocaleTimeString()}</td>
            <td style={{ padding: '10px', fontFamily: 'monospace' }}>{a.camera_id}</td>
            <td style={{ padding: '10px' }}>{a.location_name}</td>
            <td style={{ padding: '10px', color: '#DC2626', fontWeight: 'bold' }}>
              {Math.round(a.confidence * 100)}%
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
```

### components/CameraGrid.jsx
```jsx
export function CameraGrid({ cameras, latestAlert }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
      {cameras.map(cam => {
        const isAlerting = latestAlert?.camera_id === cam.camera_id
        return (
          <div key={cam.camera_id} style={{
            border: `2px solid ${isAlerting ? '#DC2626' : '#10B981'}`,
            borderRadius: '8px',
            padding: '16px',
            background: isAlerting ? '#FEF2F2' : 'white'
          }}>
            <div style={{ fontWeight: 'bold', fontSize: '16px' }}>{cam.camera_id}</div>
            <div style={{ fontSize: '13px', color: '#6B7280' }}>{cam.location_name}</div>
            <div style={{
              marginTop: '8px',
              color: isAlerting ? '#DC2626' : '#10B981',
              fontWeight: 'bold',
              fontSize: '13px'
            }}>
              {isAlerting ? '🚨 ALERT' : '● Active'}
            </div>
          </div>
        )
      })}
    </div>
  )
}
```

### App.jsx
```jsx
import { useEffect, useState } from 'react'
import { useSSE } from './hooks/useSSE'
import { ThreatBanner } from './components/ThreatBanner'
import { AlertMap } from './components/AlertMap'
import { AlertLog } from './components/AlertLog'
import { CameraGrid } from './components/CameraGrid'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL

export default function App() {
  const { alerts, latestAlert, connected } = useSSE()
  const [cameras, setCameras] = useState([])

  useEffect(() => {
    fetch(`${BACKEND_URL}/cameras`)
      .then(r => r.json())
      .then(d => setCameras(d.cameras))
  }, [])

  return (
    <div style={{ fontFamily: 'sans-serif', minHeight: '100vh', background: '#F3F4F6' }}>

      {/* Header */}
      <div style={{ background: '#111827', color: 'white', padding: '16px 24px',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: '20px', fontWeight: 'bold' }}>
          🛡️ Ankurah — Police Control Room
        </div>
        <div style={{ fontSize: '13px', color: connected ? '#10B981' : '#EF4444' }}>
          {connected ? '● Live' : '○ Reconnecting...'}
        </div>
      </div>

      {/* Alert banner */}
      <ThreatBanner latestAlert={latestAlert} />

      <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>

        {/* Camera grid */}
        <section>
          <h2 style={{ marginBottom: '12px' }}>Camera Status</h2>
          <CameraGrid cameras={cameras} latestAlert={latestAlert} />
        </section>

        {/* Map */}
        <section>
          <h2 style={{ marginBottom: '12px' }}>Live Incident Map</h2>
          <AlertMap alerts={alerts} />
        </section>

        {/* Alert log */}
        <section>
          <h2 style={{ marginBottom: '12px' }}>Alert Log</h2>
          <AlertLog alerts={alerts} />
        </section>

      </div>
    </div>
  )
}
```

### PWA manifest — public/manifest.json
```json
{
  "name": "Ankurah Police",
  "short_name": "Ankurah",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#111827",
  "theme_color": "#111827",
  "icons": [
    { "src": "/icon.png", "sizes": "192x192", "type": "image/png" }
  ]
}
```

Add to `index.html` `<head>`:
```html
<link rel="manifest" href="/manifest.json" />
<meta name="theme-color" content="#111827" />
```

### How Surakshan links to Varchas
Surakshan's `useSSE.js` connects to `GET /stream` on Varchas's backend. The `VITE_BACKEND_URL` env variable controls which IP/port. During dev Surakshan can test by pointing to `http://localhost:8000` if backend is running locally, or the Mac's IP over WiFi. Surakshan never modifies backend code.

---

## 9. Integration Points — How Everything Links

Three integration points. That's it. Know these by heart.

```
INTEGRATION 1:
GiGi (detector) ──POST /alert──► Varchas (backend)
Shape: AlertPayload model (Section 5)
Test: GiGi curls /alert, Varchas checks terminal logs

INTEGRATION 2:
Varchas (backend) ──SSE /stream──► Surakshan (frontend)
Shape: SSE event format (Section 5)
Test: Surakshan opens browser console, sees events arriving

INTEGRATION 3:
Varchas (backend) ──Discord webhook──► Officer phone
Shape: Discord message JSON (in discord_service.py)
Test: Varchas posts manually to /alert, checks Discord
```

**The golden test (run this before demo):**
```bash
# Terminal 1 (Mac) — start backend
cd backend && uvicorn main:app --reload

# Terminal 2 (Mac) — start detector
cd detector && python main.py

# Browser — open dashboard
http://localhost:5173

# Manual trigger test
curl -X POST http://localhost:8000/alert \
  -H "Content-Type: application/json" \
  -d '{"camera_id":"CAM-01","confidence":0.95,"timestamp":"2024-01-15T14:32:07Z","lat":12.9747,"lng":77.6094,"location_name":"MG Road Junction"}'

# Expected result:
# ✅ Backend terminal: "Alert received: CAM-01"
# ✅ Discord: message appears in channel
# ✅ Dashboard: red banner, map pin, alert log row
```

---

## 10. Environment Variables — Shared .env Contract

This is the single source of truth for all env vars. Never commit actual `.env` files. Commit `.env.example` only.

### .env.example (root level — commit this)
```
# detector/.env
BACKEND_URL=http://localhost:8000
CAMERA_ID=CAM-01

# backend/.env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/REPLACE_ME/REPLACE_ME

# frontend/.env
VITE_BACKEND_URL=http://localhost:8000
VITE_GMAPS_KEY=REPLACE_WITH_GOOGLE_MAPS_API_KEY
```

### Who owns what
| Variable | Owner | Where |
|----------|-------|--------|
| BACKEND_URL | GiGi sets, Varchas provides value | detector/.env |
| CAMERA_ID | GiGi sets | detector/.env |
| DISCORD_WEBHOOK_URL | Varchas creates webhook, stores it | backend/.env |
| VITE_BACKEND_URL | Surakshan sets (Mac's IP during demo) | frontend/.env |
| VITE_GMAPS_KEY | Surakshan gets from Google Console | frontend/.env |

### Getting the Google Maps API key (Surakshan's task)
1. Go to console.cloud.google.com
2. Create project → Enable "Maps JavaScript API"
3. Credentials → Create API Key
4. Restrict to your IP for safety
5. Paste into `frontend/.env`

---

## 11. Demo Run Instructions

### 30 minutes before demo — checklist

**On GiGi's Mac M1:**
```bash
# Find Mac's WiFi IP — share this in group chat
ipconfig getifaddr en0
# e.g. 192.168.1.10

# Terminal 1 — backend
cd Ankurah/backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2 — detector
cd Ankurah/detector
source venv/bin/activate
python main.py
# Should open webcam window — you'll see "State: IDLE"

# Terminal 3 — frontend
cd Ankurah/frontend
npm run dev -- --host
# Note the network URL: http://192.168.1.10:5173
```

**On Surakshan's Windows:**
```bash
# Open browser
http://192.168.1.10:5173
# Dashboard should load and show "● Live" in top right
```

**On officer phone (any team member's phone):**
1. Open `http://192.168.1.10:5173` in Chrome
2. Tap "Add to Home Screen" → PWA installed
3. Also ensure Discord is installed and notifications are ON

**Final check — trigger a test alert:**
```bash
curl -X POST http://192.168.1.10:8000/alert \
  -H "Content-Type: application/json" \
  -d '{"camera_id":"CAM-01","confidence":0.95,"timestamp":"2024-01-15T14:32:07Z","lat":12.9747,"lng":77.6094,"location_name":"MG Road Junction"}'
```
All three should respond simultaneously — dashboard, Discord, phone.

### During demo — who does what

| Person | Role during demo |
|--------|-----------------|
| GiGi | Operates the laptop with detector running. Faces webcam and performs the gesture. |
| Varchas | Stands near the judge with phone showing Discord. Narrates the technical flow. |
| Surakshan | Presents the dashboard on the projected screen. Points to map, alert log, banner. |

### Demo script (90 seconds)

> "Every 3 minutes, a woman in India faces violence. Most can't call for help — they're being watched. Ankurah solves this using cameras that already exist."

[GiGi opens palm toward webcam — gesture state on Mac shows STEP1]

> "When a victim sees any city camera, she performs the Signal for Help — open palm, thumb tuck, close fist. Watch."

[GiGi holds for 1.5s each step. 4.5 seconds total silence. Let it happen.]

[Dashboard banner turns red. Map pin appears. Alert log row populates.]

> "Our AI confirmed that in real time. No phone. No words. Nothing the abuser could notice."

[Varchas holds up phone showing Discord notification]

> "Simultaneously — the nearest officer gets a Discord alert with the exact camera location and a Google Maps link. One tap, they're navigating there."

[Surakshan points to the dashboard]

> "This is the police control room — all cameras, all alerts, live. Deployable on any existing CCTV network as a pure software plugin. Zero new hardware."

> "We built this in 24 hours. City-wide scale: ₹4,000 per server per month."

---

## 12. Vibe Coding Rules — Avoiding Mistakes

These rules exist because you're building three systems in parallel in an IDE with AI assistance. Breaking these rules causes integration failures that cost hours to debug at 3am.

### Rule 1 — Never change the API contract
Section 5 is frozen. If GiGi or Surakshan need a new field in the alert payload, they ask Varchas first. Varchas adds it and announces in group chat. Nobody changes field names silently.

### Rule 2 — Test integration points with curl before writing UI
Before Surakshan builds the AlertLog component, Varchas must have a working `/alerts` endpoint that curl returns correct JSON from. Don't build on assumed behavior.

### Rule 3 — Environment variables only. No hardcoded IPs.
Never write `http://192.168.1.10:8000` inside source code. Always `import.meta.env.VITE_BACKEND_URL` or `os.getenv("BACKEND_URL")`. IPs change when you switch WiFi networks.

### Rule 4 — Each person runs their own mock when the other isn't ready
- GiGi: If backend isn't up, run `python -m http.server` and mock the /alert response manually
- Surakshan: If backend isn't up, use this mock SSE in `useSSE.js`:
```javascript
// MOCK — remove before integration
useEffect(() => {
  const interval = setInterval(() => {
    const mockAlert = {
      type: 'alert', camera_id: 'CAM-01', confidence: 0.95,
      timestamp: new Date().toISOString(),
      lat: 12.9747, lng: 77.6094,
      location_name: 'MG Road Junction'
    }
    setLatestAlert(mockAlert)
    setAlerts(prev => [mockAlert, ...prev])
  }, 10000)
  return () => clearInterval(interval)
}, [])
```

### Rule 5 — CORS errors mean Varchas needs to fix backend, not Surakshan
If Surakshan sees CORS errors in browser console, Varchas checks that `allow_origins=["*"]` is set and server is bound to `0.0.0.0`.

### Rule 6 — M1 Python packages — use venv always
GiGi never installs packages globally on M1. Always activate venv first. MediaPipe on M1 is sensitive — don't upgrade it mid-hackathon.

### Rule 7 — Git commits every hour
All three push to their respective folders every hour with message `[HOUR X] what I built`. If someone's laptop dies, the work survives.

### Rule 8 — The demo machine is GiGi's Mac. Backend and detector both run there.
Surakshan and Varchas's laptops are for development only. On demo day, everything runs on the Mac. Surakshan's Windows opens the dashboard in browser over WiFi — nothing more.

---

## 13. Camera Registry — Hardcoded for Demo

This is the same in both `detector/config.py` and `backend/routes/cameras.py`. Keep them in sync manually — no API for this.

| Camera ID | Location Name | Lat | Lng |
|-----------|--------------|-----|-----|
| CAM-01 | MG Road Junction | 12.9747 | 77.6094 |
| CAM-02 | Koramangala Market | 12.9352 | 77.6245 |
| CAM-03 | Indiranagar Metro | 12.9784 | 77.6408 |

For the demo, only CAM-01 is live (GiGi's webcam). CAM-02 and CAM-03 appear on the dashboard map as active cameras but won't fire alerts. This shows scale without requiring 3 cameras.

---

## 14. Deliverables Checklist Per Person

### GiGi — done when:
- [ ] `python main.py` opens webcam with landmark overlay
- [ ] Terminal shows state transitions as gesture is performed
- [ ] On completing gesture: `[ALERT SENT] Status: 200 | MG Road Junction`
- [ ] 10 second cooldown works — no spam
- [ ] Works on M1 without GPU

### Varchas — done when:
- [ ] `uvicorn main:app` starts without errors
- [ ] `GET /health` returns 200
- [ ] `GET /cameras` returns 3 cameras
- [ ] `POST /alert` with sample payload returns `{"status":"ok","alert_id":"..."}`
- [ ] Discord message appears in channel within 1 second
- [ ] `GET /stream` keeps connection open and sends heartbeat every 5s
- [ ] SSE event arrives in stream within 1s of POST /alert

### Surakshan — done when:
- [ ] Dashboard loads at localhost:5173 without errors
- [ ] "● Live" indicator shows green in header
- [ ] 3 camera cards visible
- [ ] Manual curl to /alert causes red banner to appear within 1s
- [ ] Map shows red pin at correct location
- [ ] Alert log table row appears with correct data
- [ ] App accessible from phone browser over WiFi
- [ ] PWA "Add to Home Screen" works on phone

### Team — done when:
- [ ] Full end-to-end test passes: gesture → dashboard → Discord
- [ ] Demo rehearsed 3 times
- [ ] One team member's phone has Discord notification
- [ ] Pre-recorded backup video exists in case live demo fails

---

*Last updated: Hackathon day. This document is the single source of truth. When in doubt, check Section 5.*
