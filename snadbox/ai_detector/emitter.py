"""
emitter.py — Output via FastAPI service (REST and WebSocket) and atomic JSON file writes.

This replaces the old WebSocket-only broadcaster with a full HTTP/WS API, 
running in a daemon thread via uvicorn. It exposes various layer-specific analysis 
endpoints alongside the streaming /stream/system endpoint.
"""

import asyncio
import json
import os
import tempfile
import threading
import time
from typing import Any, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

from config import API_HOST, API_PORT, OUTPUT_FILE
from aggregator import SESSION_ID

# ─── Shared state ─────────────────────────────────────────────────────────────
_latest_payload: Optional[Dict[str, Any]] = None
_payload_lock = threading.Lock()
_start_time = time.time()
_server_ready = threading.Event()

app = FastAPI(title="AuraGuard/Varchas Analysis Service")

# ─── Channel 1 — Atomic file write ────────────────────────────────────────────

def _write_file(payload: Dict[str, Any]) -> None:
    """Atomically write payload JSON to OUTPUT_FILE using a temp-file swap."""
    try:
        dir_name  = os.path.dirname(os.path.abspath(OUTPUT_FILE)) or "."
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp_path, OUTPUT_FILE)
        except Exception:
            # Make sure we don't leave a dangling temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except Exception as e:
        print(f"[EMITTER] file write error: {e}")


def emit(payload: Dict[str, Any]) -> None:
    """Write payload to file and update the latest cached payload for WS/HTTP clients."""
    try:
        with _payload_lock:
            global _latest_payload
            _latest_payload = payload
    except Exception as e:
        print(f"[EMITTER] payload update error: {e}")
        
    _write_file(payload)


# ─── FastAPI Endpoints ────────────────────────────────────────────────────────

@app.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "session_id": SESSION_ID,
        "uptime_sec": time.time() - _start_time
    }

@app.post("/analyze/process")
async def analyze_process() -> dict:
    from layers.process import run_process_scan
    from layers.stealth_windows import run_stealth_window_scan
    
    proc_res = await asyncio.to_thread(run_process_scan)
    stealth_res = await asyncio.to_thread(run_stealth_window_scan)
    
    return {
        "process": proc_res,
        "stealth_windows": stealth_res,
        "timestamp": time.time()
    }

@app.post("/analyze/network")
async def analyze_network() -> dict:
    from layers.browser import run_browser_scan
    from layers.network import run_network_scan
    
    browser_res = await asyncio.to_thread(run_browser_scan)
    network_res = await asyncio.to_thread(run_network_scan)
    
    return {
        "browser": browser_res,
        "network": network_res,
        "timestamp": time.time()
    }

@app.get("/analyze/hardware")
async def analyze_hardware() -> dict:
    from layers.hardware import run_hardware_scan
    
    hw_res = await asyncio.to_thread(run_hardware_scan)
    hw_res["timestamp"] = time.time()
    return hw_res

@app.get("/analyze/full")
async def analyze_full() -> dict:
    from layers.browser import run_browser_scan
    from layers.process import run_process_scan
    from layers.hardware import run_hardware_scan
    from layers.behavioral import run_behavioral_scan
    from layers.network import run_network_scan
    from layers.stealth_windows import run_stealth_window_scan
    from aggregator import add_snapshot, compute_score
    
    # Run all scans in threadpool
    browser_res  = await asyncio.to_thread(run_browser_scan)
    process_res  = await asyncio.to_thread(run_process_scan)
    hw_res       = await asyncio.to_thread(run_hardware_scan)
    behav_res    = await asyncio.to_thread(run_behavioral_scan)
    network_res  = await asyncio.to_thread(run_network_scan)
    stealth_res  = await asyncio.to_thread(run_stealth_window_scan)
    
    snapshot = [
        browser_res,
        process_res,
        hw_res,
        behav_res,
        network_res,
        stealth_res
    ]
    
    add_snapshot(snapshot)
    final_payload = compute_score()
    
    # ensure it gets written and cached for any WebSocket clients
    emit(final_payload)
    
    return final_payload

@app.websocket("/stream/system")
async def stream_system(websocket: WebSocket):
    await websocket.accept()
    
    # Send the latest known payload immediately on connect
    with _payload_lock:
        current = _latest_payload
    if current is None:
        current = {"status": "waiting_for_first_tick"}
        
    try:
        await websocket.send_json(current)
    except Exception as e:
        print(f"[EMITTER] WS initial send error: {e}")
        return
        
    # Poll and send whenever the payload updates
    try:
        while True:
            await asyncio.sleep(1.0)
            with _payload_lock:
                current = _latest_payload
            if current:
                await websocket.send_json(current)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[EMITTER] WS streaming error: {e}")


# ─── Server Startup ───────────────────────────────────────────────────────────

def _wait_and_signal() -> None:
    time.sleep(1.0)
    _server_ready.set()

@app.on_event("startup")
async def startup_event():
    print(f"[EMITTER] FastAPI service starting on port {API_PORT}")

def start_fastapi_server() -> None:
    """Start the FastAPI uvicorn server in a daemon thread."""
    config = uvicorn.Config(app, host=API_HOST, port=API_PORT, log_level="warning")
    server = uvicorn.Server(config)
    
    t = threading.Thread(target=server.run, name="fastapi-server", daemon=True)
    t.start()
    
    # Uvicorn doesn't have a reliable post-bind block, so wait briefly
    sig_t = threading.Thread(target=_wait_and_signal, daemon=True)
    sig_t.start()
    
    _server_ready.wait(timeout=5.0)
    print(f"[EMITTER] FastAPI ready on http://{API_HOST}:{API_PORT}")
