from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import shutil
import os
import time
from .stream import router
from services.sse_manager import sse_manager

router = APIRouter()

# Directory for snapshots
SNAPSHOT_DIR = "static/snapshots"
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

@router.post("/upload_snapshot")
async def upload_snapshot(
    file: UploadFile = File(...),
    camera_id: str = Form(...)
):
    """Stores a snapshot from the detector and broadcasts it."""
    timestamp = int(time.time())
    filename = f"{camera_id}_{timestamp}.jpg"
    filepath = os.path.join(SNAPSHOT_DIR, filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    snapshot_url = f"/static/snapshots/{filename}"
    
    # Broadcast to all connected clients (Dashboard & Officer)
    await sse_manager.broadcast({
        "type": "snapshot_fired",
        "camera_id": camera_id,
        "snapshot_url": snapshot_url,
        "timestamp": timestamp
    })
    
    return {"status": "success", "url": snapshot_url}

@router.post("/responder/status")
async def update_responder_status(
    status: str = Form(...), # "started" or "reached"
    incident_id: str = Form(None)
):
    """Updates the officer lifecycle status and broadcasts it."""
    # In a real app, we'd update a DB. Here we just broadcast.
    await sse_manager.broadcast({
        "type": "responder_update",
        "status": status,
        "timestamp": int(time.time()),
        "incident_id": incident_id
    })
    return {"status": "success"}
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
import asyncio
from datetime import datetime, timezone

# Helper for simulation
async def run_demo_simulation():
    # 1. Alert
    await sse_manager.broadcast({
        "type": "alert",
        "camera_id": "CAM-01",
        "confidence": 0.92,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lat": 12.9716,
        "lng": 77.5946,
        "location_name": "MG Road Junction"
    })
    await asyncio.sleep(2)
    
    # 2. Snapshot
    await sse_manager.broadcast({
        "type": "snapshot_fired",
        "camera_id": "CAM-01",
        "snapshot_url": "/static/snapshots/CAM-01_demo.jpg",
        "timestamp": int(time.time())
    })
    await asyncio.sleep(3)

    # 3. Started
    await sse_manager.broadcast({
        "type": "responder_update",
        "status": "started",
        "timestamp": int(time.time())
    })
    await asyncio.sleep(4)

    # 4. Reached
    await sse_manager.broadcast({
        "type": "responder_update",
        "status": "reached",
        "timestamp": int(time.time())
    })

@router.get("/demo_replay")
async def demo_replay(background_tasks: BackgroundTasks):
    """Triggers an automated lifecycle simulation for demos."""
    background_tasks.add_task(run_demo_simulation)
    return {"status": "simulation_started"}
