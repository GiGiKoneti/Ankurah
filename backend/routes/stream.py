import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from services.sse_manager import sse_manager

router = APIRouter()

HEARTBEAT_INTERVAL = 5  # seconds


async def event_generator(q: asyncio.Queue):
    """Yield SSE events from the queue, sending heartbeats when idle."""
    try:
        while True:
            try:
                # Wait up to HEARTBEAT_INTERVAL seconds for a real event
                message = await asyncio.wait_for(q.get(), timeout=HEARTBEAT_INTERVAL)
                yield message
            except asyncio.TimeoutError:
                # Send heartbeat
                heartbeat = {
                    "type": "heartbeat",
                    "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
                yield f"data: {json.dumps(heartbeat)}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        sse_manager.disconnect(q)


@router.get("/stream")
async def stream():
    q = sse_manager.connect()
    return StreamingResponse(
        event_generator(q),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
