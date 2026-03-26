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
