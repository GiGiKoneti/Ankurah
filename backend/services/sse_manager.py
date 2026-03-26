import asyncio
import json
from typing import List


class SSEManager:
    """Manages Server-Sent Events queues for all connected clients."""

    def __init__(self):
        self._queues: List[asyncio.Queue] = []

    def connect(self) -> asyncio.Queue:
        """Create a new queue for a client and register it."""
        q: asyncio.Queue = asyncio.Queue()
        self._queues.append(q)
        return q

    def disconnect(self, q: asyncio.Queue) -> None:
        """Remove the client queue on disconnect."""
        try:
            self._queues.remove(q)
        except ValueError:
            pass

    async def broadcast(self, data: dict) -> None:
        """Push a payload to every connected client queue."""
        message = f"data: {json.dumps(data)}\n\n"
        dead: List[asyncio.Queue] = []
        for q in self._queues:
            try:
                await q.put(message)
            except Exception:
                dead.append(q)
        for q in dead:
            self.disconnect(q)


# Module-level singleton used by all routes
sse_manager = SSEManager()
