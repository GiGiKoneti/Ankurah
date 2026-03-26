import time

from fastapi import APIRouter

from routes.alert import alert_log

router = APIRouter()

# Recorded at module import time — used for uptime calculation
START_TIME: float = time.time()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME),
        "alerts_fired": len(alert_log),
    }
