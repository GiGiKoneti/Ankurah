import asyncio
import time
from fastapi import APIRouter
from models import AlertPayload, AlertResponse
from services.notification_service import notify_all
from services.sse_manager import sse_manager

router = APIRouter()

# In-memory alert log — max 50 entries
alert_log: list = []


@router.post("/alert", response_model=AlertResponse)
async def post_alert(payload: AlertPayload):
    # 1. Validate — done by Pydantic above
    # 2. Generate alert_id
    alert_id = f"alert_{int(time.time())}"

    # 3. Build alert dict and append (cap at 50)
    alert = {
        "alert_id": alert_id,
        "camera_id": payload.camera_id,
        "confidence": payload.confidence,
        "timestamp": payload.timestamp,
        "lat": payload.lat,
        "lng": payload.lng,
        "location_name": payload.location_name,
    }
    alert_log.append(alert)
    if len(alert_log) > 50:
        alert_log.pop(0)

    # 4. Fire Notifications (SMS + Twitter) — non-blocking
    asyncio.create_task(notify_all(alert))

    # 5. Broadcast SSE — non-blocking
    sse_event = {"type": "alert", **alert}
    asyncio.create_task(sse_manager.broadcast(sse_event))

    # 6. Return immediately
    return AlertResponse(status="ok", alert_id=alert_id)
