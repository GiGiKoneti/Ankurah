from pydantic import BaseModel


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
