import requests
import cv2
import os
from datetime import datetime, timezone
from config import BACKEND_URL, CAMERA_ID, CAMERA_REGISTRY

def send_live_snapshot(frame):
    """Sends a frequent snapshot to keep the 'CCTV' grid updated without an alert."""
    if frame is not None:
        try:
            _, img_encoded = cv2.imencode('.jpg', frame)
            files = {'file': ('snapshot.jpg', img_encoded.tobytes(), 'image/jpeg')}
            data = {'camera_id': CAMERA_ID}
            # lower timeout for heartbeats
            requests.post(f"{BACKEND_URL}/upload_snapshot", files=files, data=data, timeout=1)
        except Exception:
            pass

def send_alert(confidence: float, frame=None):
    """Sends a high-priority alert metadata and an optional incident snapshot."""
    camera = CAMERA_REGISTRY.get(CAMERA_ID, {})
    payload = {
        "camera_id": CAMERA_ID,
        "confidence": confidence,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lat": camera.get("lat", 12.9716),
        "lng": camera.get("lng", 77.5946),
        "location_name": camera.get("location_name", "Unknown Location")
    }
    
    # 1. Send metadata
    try:
        r = requests.post(f"{BACKEND_URL}/alert", json=payload, timeout=3)
        print(f"[ALERT SENT] Status: {r.status_code} | {payload['location_name']}")
    except Exception as e:
        print(f"[ALERT FAILED] {e}")

    # 2. Send the high-priority snapshot
    if frame is not None:
        try:
            _, img_encoded = cv2.imencode('.jpg', frame)
            files = {'file': ('snapshot.jpg', img_encoded.tobytes(), 'image/jpeg')}
            data = {'camera_id': CAMERA_ID}
            requests.post(f"{BACKEND_URL}/upload_snapshot", files=files, data=data, timeout=5)
            print(f"[SNAPSHOT UPLOADED] for {CAMERA_ID}")
        except Exception as e:
            print(f"[SNAPSHOT FAILED] {e}")
