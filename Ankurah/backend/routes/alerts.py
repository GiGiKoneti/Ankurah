from fastapi import APIRouter

from routes.alert import alert_log

router = APIRouter()


@router.get("/alerts")
async def get_alerts():
    return {"alerts": list(reversed(alert_log))}
