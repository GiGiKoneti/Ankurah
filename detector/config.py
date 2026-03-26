import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://10.80.10.12:8000")
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
