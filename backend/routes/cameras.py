from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()

# Static camera registry — last_seen is generated fresh per request
_CAMERAS = [
    {
        "camera_id": "CAM-01",
        "location_name": "MG Road Junction",
        "lat": 12.9747,
        "lng": 77.6094,
        "status": "active",
    },
    {
        "camera_id": "CAM-02",
        "location_name": "Koramangala Market",
        "lat": 12.9352,
        "lng": 77.6245,
        "status": "active",
    },
    {
        "camera_id": "CAM-03",
        "location_name": "Indiranagar Metro",
        "lat": 12.9784,
        "lng": 77.6408,
        "status": "active",
    },
]


@router.get("/cameras")
async def get_cameras():
    now = datetime.now(timezone.utc).isoformat()
    cameras = [{**cam, "last_seen": now} for cam in _CAMERAS]
    return {"cameras": cameras}
