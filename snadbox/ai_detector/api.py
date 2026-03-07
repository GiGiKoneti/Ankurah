"""
api.py — Spec-compliant FastAPI service for Varchas.

Provides:
  - push_event(event)      → non-blocking add to the ForensicEvent queue
  - /health                → service health + active monitors list
  - /analyze/process       → process + stealth layer scan
  - /analyze/network       → network + browser layer scan  
  - /analyze/hardware      → hardware layer scan
  - /analyze/peripheral    → peripheral layer scan
  - /analyze/full          → all layers + aggregated score + emit
  - /stream/system         → WebSocket streaming at 100ms tick rate
  - start_api_server()     → run uvicorn in a daemon thread
"""

import asyncio
import json
import os
import queue
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

from config import API_HOST, API_PORT, OUTPUT_FILE
from aggregator import SESSION_ID

# ─── ForensicEvent queue ──────────────────────────────────────────────────────
_event_queue: queue.Queue = queue.Queue(maxsize=1000)

# ─── Latest payload cache ─────────────────────────────────────────────────────
_latest_payload: Optional[Dict[str, Any]] = None
_payload_lock    = threading.Lock()
_start_time      = time.time()
_server_ready    = threading.Event()

# ─── Active monitor tracking ──────────────────────────────────────────────────
_monitors_active: List[str] = []

app = FastAPI(title="Varchas — Systems Intelligence Layer")


# ─── ForensicEvent push (non-blocking) ────────────────────────────────────────

def push_event(event) -> None:
    """Add a ForensicEvent to the queue non-blocking; silently drop on overflow."""
    try:
        _event_queue.put_nowait(event)
    except queue.Full:
        pass  # Drop oldest — best-effort delivery
    except Exception as e:
        print(f"[API] push_event error: {e}")


# ─── Atomic file write ────────────────────────────────────────────────────────

def _write_file(payload: Dict[str, Any]) -> None:
    """Atomically write payload JSON to OUTPUT_FILE using a temp-file swap."""
    try:
        dir_name = os.path.dirname(os.path.abspath(OUTPUT_FILE)) or "."
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp_path, OUTPUT_FILE)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except Exception as e:
        print(f"[API] file write error: {e}")


def emit(payload: Dict[str, Any]) -> None:
    """Update the latest cached payload and write to file."""
    try:
        with _payload_lock:
            global _latest_payload
            _latest_payload = payload
    except Exception as e:
        print(f"[API] emit update error: {e}")
    _write_file(payload)


# ─── Endpoint helpers ─────────────────────────────────────────────────────────

def _register_monitor(name: str) -> None:
    """Register a monitor as active."""
    if name not in _monitors_active:
        _monitors_active.append(name)


# ─── FastAPI Endpoints ────────────────────────────────────────────────────────

@app.get("/health")
def health_check() -> dict:
    """Return service health, monitors active, and uptime."""
    return {
        "status":          "ok",
        "service":         "varchas",
        "session_id":      SESSION_ID,
        "uptime_sec":      round(time.time() - _start_time, 2),
        "monitors_active": _monitors_active,
        "port":            API_PORT,
    }


@app.post("/analyze/process")
async def analyze_process() -> dict:
    """Run process + stealth window scan."""
    from layers.process import run_process_scan
    from layers.stealth_windows import run_stealth_window_scan

    proc_res   = await asyncio.to_thread(run_process_scan)
    stealth_res = await asyncio.to_thread(run_stealth_window_scan)

    return {
        "process":         proc_res,
        "stealth_windows": stealth_res,
        "timestamp":       time.time(),
    }


@app.post("/analyze/network")
async def analyze_network() -> dict:
    """Run network + browser scan."""
    from layers.browser import run_browser_scan
    from layers.network import run_network_scan

    browser_res = await asyncio.to_thread(run_browser_scan)
    network_res = await asyncio.to_thread(run_network_scan)

    return {
        "browser":    browser_res,
        "network":    network_res,
        "timestamp":  time.time(),
    }


@app.get("/analyze/hardware")
async def analyze_hardware() -> dict:
    """Run hardware scan."""
    from layers.hardware import run_hardware_scan

    hw_res = await asyncio.to_thread(run_hardware_scan)
    hw_res["timestamp"] = time.time()
    return hw_res


@app.post("/analyze/peripheral")
async def analyze_peripheral() -> dict:
    """Run peripheral (USB/BT/display/VM) scan."""
    from layers.peripheral import run_peripheral_scan

    periph_res = await asyncio.to_thread(run_peripheral_scan)
    periph_res["timestamp"] = time.time()
    return periph_res


@app.get("/analyze/full")
async def analyze_full() -> dict:
    """Run all layers, compute aggregated score, emit result."""
    from layers.browser import run_browser_scan
    from layers.process import run_process_scan
    from layers.hardware import run_hardware_scan
    from layers.behavioral import run_behavioral_scan
    from layers.network import run_network_scan
    from layers.stealth_windows import run_stealth_window_scan
    from layers.peripheral import run_peripheral_scan
    from aggregator import add_snapshot, compute_score

    # Run all scans in threadpool (blocking I/O)
    browser_res  = await asyncio.to_thread(run_browser_scan)
    process_res  = await asyncio.to_thread(run_process_scan)
    hw_res       = await asyncio.to_thread(run_hardware_scan)
    behav_res    = await asyncio.to_thread(run_behavioral_scan)
    network_res  = await asyncio.to_thread(run_network_scan)
    stealth_res  = await asyncio.to_thread(run_stealth_window_scan)
    periph_res   = await asyncio.to_thread(run_peripheral_scan)

    snapshot = [
        browser_res, process_res, hw_res,
        behav_res,   network_res, stealth_res, periph_res,
    ]

    add_snapshot(snapshot)
    final_payload = compute_score()

    emit(final_payload)
    return final_payload


# ─── WebSocket /stream/system — 100ms tick ────────────────────────────────────

@app.websocket("/stream/system")
async def stream_system(websocket: WebSocket):
    """Stream ForensicEvents and score at 100ms tick rate."""
    await websocket.accept()

    # Send current payload immediately on connect
    with _payload_lock:
        current = _latest_payload
    initial = current if current is not None else {"status": "waiting_for_first_tick"}
    try:
        await websocket.send_json(initial)
    except Exception as e:
        print(f"[API] WS initial send error: {e}")
        return

    try:
        while True:
            # Drain all queued ForensicEvents first (non-blocking)
            events_sent = 0
            while events_sent < 20:  # cap per tick to avoid flooding
                try:
                    event = _event_queue.get_nowait()
                    # Convert Pydantic model to dict for JSON serialisation
                    try:
                        event_dict = event.model_dump()
                    except AttributeError:
                        event_dict = event.dict()
                    await websocket.send_json({"type": "forensic_event", "data": event_dict})
                    events_sent += 1
                except queue.Empty:
                    break
                except Exception as e:
                    print(f"[API] WS event send error: {e}")
                    break

            # Send latest aggregated payload
            with _payload_lock:
                current = _latest_payload
            if current:
                try:
                    await websocket.send_json({"type": "score_update", "data": current})
                except Exception as e:
                    print(f"[API] WS score send error: {e}")
                    break

            await asyncio.sleep(0.1)  # 100ms tick

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[API] WS streaming error: {e}")


# ─── Startup event ────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Register all monitors on startup."""
    _register_monitor("clipboard")
    _register_monitor("hardware_sampler")
    _register_monitor("model_file_watcher")
    _register_monitor("network")
    _register_monitor("browser")
    _register_monitor("peripheral")
    print(f"[API] Varchas FastAPI service starting on port {API_PORT}")


# ─── Wait-and-signal helper ───────────────────────────────────────────────────

def _wait_and_signal() -> None:
    time.sleep(2.0)
    _server_ready.set()


def start_api_server() -> None:
    """Start the Varchas FastAPI/uvicorn server in a daemon thread."""
    config = uvicorn.Config(
        app,
        host=API_HOST,
        port=API_PORT,
        log_level="warning",
    )
    server = uvicorn.Server(config)

    t = threading.Thread(target=server.run, name="varchas-api", daemon=True)
    t.start()

    # Signal that the server is ready
    sig_t = threading.Thread(target=_wait_and_signal, daemon=True)
    sig_t.start()

    _server_ready.wait(timeout=6.0)
    print(f"[API] Varchas ready on http://{API_HOST}:{API_PORT}")
