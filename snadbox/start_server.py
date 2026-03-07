import subprocess
import sys
import os
import time
import threading
import signal as signal_module

# ══════════════════════════════════════════════════════════════════════════════
# AUTO INSTALL
# ══════════════════════════════════════════════════════════════════════════════
def bootstrap():
    subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    packages = ['fastapi', 'uvicorn[standard]', 'requests', 'psutil']
    for pkg in packages:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', pkg,
             '--quiet', '--disable-pip-version-check'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

bootstrap()

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
import hashlib, json, socket, logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger("TruthLens")

# ══════════════════════════════════════════════════════════════════════════════
# IP + AGENT SETUP
# ══════════════════════════════════════════════════════════════════════════════
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'

LOCAL_IP = get_local_ip()

# Patch agent file with correct server URL
agent_source = "agent.py" if os.path.exists("agent.py") else "agent_ready.py"
try:
    with open(agent_source, "rb") as f:
        agent_code = f.read()
    patched = agent_code.decode('utf-8')
    # Replace any existing SERVER_URL line
    import re as _re
    # Fix: match ANY value for SERVER_URL including PLACEHOLDER and REPLACE_WITH_YOUR_IP
    patched = _re.sub(
        r'SERVER_URL\s*=\s*"[^"]*"',
        f'SERVER_URL = "http://{LOCAL_IP}:8000"',
        patched
    )
    with open("agent_ready.py", "w", encoding='utf-8') as f:
        f.write(patched)
    print(f"✅ Agent configured -> agent_ready.py (URL: http://{LOCAL_IP}:8000)")
except Exception as e:
    print(f"❌ Failed to configure agent: {e}")

# Firewall
if sys.platform == 'win32':
    subprocess.run([
        'netsh', 'advfirewall', 'firewall', 'add', 'rule',
        'name=TruthLens', 'dir=in', 'action=allow',
        'protocol=TCP', 'localport=8000'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print(f"""
╔══════════════════════════════════════════════════╗
║        TRUTHLENS SERVER READY                    ║
╠══════════════════════════════════════════════════╣
║  Local IP:   {LOCAL_IP:<36}║
║  Port:       8000                                ║
║  Health:     http://{LOCAL_IP}:8000/health{" "*(23-len(LOCAL_IP))}║
╠══════════════════════════════════════════════════╣
║  ✅ Packages installed                           ║
║  ✅ Agent configured → agent_ready.py            ║
║  ✅ Firewall opened                              ║
╠══════════════════════════════════════════════════╣
║  SEND agent_ready.py TO FRIEND                   ║
║  They just run: python agent_ready.py            ║
╠══════════════════════════════════════════════════╣
║  Waiting for connections...                      ║
╚══════════════════════════════════════════════════╝
""")

# ══════════════════════════════════════════════════════════════════════════════
# FASTAPI APP
# ══════════════════════════════════════════════════════════════════════════════
app = FastAPI(title='TruthLens Server', docs_url=None, redoc_url=None)

active_sessions = {}
SHUTTING_DOWN = False
REPORTS_RECEIVED = {}

@app.get('/health')
def get_health():
    return {'status': 'ok'}

@app.post("/register")
async def register_agent(request: Request):
    try:
        data = await request.json()
        session_id = data.get('session_id')
        agent_hash = data.get('agent_hash')
        if session_id not in active_sessions:
            active_sessions[session_id] = {
                'connected_at': time.time(),
                'last_seen':    time.time(),
                'agent_hash':   agent_hash,
                'terminate':    False,
                'events':       []
            }
        print(f"[{time.strftime('%H:%M:%S')}] ✅ Agent connected — {session_id[:8]}")
        print(f"[{time.strftime('%H:%M:%S')}] 🔑 Agent hash: {agent_hash[:16]}...")
        return {"status": "ok", "authorized": True}
    except Exception as e:
        logger.error(f"Register failed: {e}")
        return {"status": "error"}

@app.post("/event")
async def receive_event(request: Request):
    try:
        data = await request.json()
        event_type = data.get('event', 'UNKNOWN')
        ts = time.strftime('%H:%M:%S')
        emoji_map = {
            'THREAT_PROCESS': '💀',
            'AI_DOMAIN':      '🔴',
            'AI_PORT':        '⚠️ ',
            'LARGE_PASTE':    '📋',
            'AI_WINDOW':      '👁️ ',
            'CAUSALITY':      '⚡',
            'TAMPER':         '🚨',
            'HARDWARE':       '🖥️ ',
        }
        emoji = emoji_map.get(event_type, '📡')
        d = data.get('data', {})
        if not isinstance(d, dict):
            d = {}
        if event_type == 'THREAT_PROCESS':
            desc = f"{d.get('name','?')} detected"
        elif event_type == 'AI_DOMAIN':
            desc = f"{d.get('domain','?')} ({d.get('ip','?')})"
        elif event_type == 'LARGE_PASTE':
            desc = f"{d.get('chars',0)} chars"
        elif event_type == 'AI_WINDOW':
            desc = f"'{d.get('title','?')}' [{d.get('keyword','?')}]"
        else:
            desc = str(d)[:60]
        print(f"[{ts}] {emoji} {event_type}: {desc}")
        sid = data.get('session_id')
        if sid and sid in active_sessions:
            active_sessions[sid]['last_seen'] = time.time()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Event failed: {e}")
        return {"status": "error"}

@app.post('/heartbeat')
async def post_heartbeat(request: Request):
    try:
        body = await request.json()
        sid = body.get('session_id', 'unknown')
        if sid in active_sessions:
            active_sessions[sid]['last_seen'] = time.time()
        logger.debug(f"💓 Heartbeat from {sid[:8]}")
        return {'status': 'ok'}
    except Exception as e:
        logger.error(f"Heartbeat failed: {e}")
        return {"status": "error"}

@app.post("/terminate/{session_id}")
async def terminate_session(session_id: str):
    if session_id in active_sessions:
        active_sessions[session_id]['terminate'] = True
        print(f"[{time.strftime('%H:%M:%S')}] 🛑 Terminating {session_id[:8]}")
        return {"status": "ok"}
    return {"status": "not_found"}

@app.get("/should_terminate/{session_id}")
async def should_terminate(session_id: str):
    if session_id in active_sessions:
        return {"terminate": active_sessions[session_id].get('terminate', False)}
    return {"terminate": False}

@app.post("/terminate_all")
async def terminate_all():
    for sid in active_sessions:
        active_sessions[sid]['terminate'] = True
    count = len(active_sessions)
    print(f"[{time.strftime('%H:%M:%S')}] 🛑 Terminating all {count} sessions")
    return {"status": "ok", "sessions_terminated": count}

@app.post("/report")
async def receive_report(request: Request):
    try:
        report = await request.json()
        session_id = report.get('session_id', 'unknown')
        REPORTS_RECEIVED[session_id] = report
        print(f"[{time.strftime('%H:%M:%S')}] 📊 Report received from {session_id[:8]}")
        if SHUTTING_DOWN:
            print_report(report)
        return {"status": "ok"}
    except Exception as e:
        print(f"[ERROR] Report failed: {e}")
        return {"status": "error"}

@app.get('/download/agent')
def download_agent():
    return FileResponse('agent_ready.py', filename='agent_ready.py')


@app.get('/download/launcher')
def download_launcher():
    """
    Webapp button calls this.
    Returns monitor.bat — candidate double clicks, everything runs.
    """
    bat_content = f"""@echo off
:: TruthLens Monitor Launcher
:: Double click to start interview monitoring

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing Python, please wait...
    curl -s -o "%TEMP%\\pysetup.exe" https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe
    "%TEMP%\\pysetup.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    del "%TEMP%\\pysetup.exe"
)

:: Download agent from server
curl -s -o "%TEMP%\\monitor_agent.py" http://{LOCAL_IP}:8000/download/agent

:: Install packages silently
pip install psutil pyperclip requests cryptography pynvml -q >nul 2>&1

:: Run silently (no window)
start /b pythonw "%TEMP%\\monitor_agent.py"

:: Self delete
del "%~f0"
"""
    from fastapi.responses import Response
    return Response(
        content=bat_content,
        media_type='application/octet-stream',
        headers={'Content-Disposition': 'attachment; filename=monitor.bat'}
    )


def print_report(report):
    score    = report.get('risk_score', 0)
    duration = report.get('duration_sec', 0)
    minutes  = duration // 60
    seconds  = duration % 60
    sid      = report.get('session_id', 'unknown')[:8]
    summary  = report.get('threat_summary', {})
    events   = report.get('events', [])
    integrity = report.get('integrity', {})

    if score >= 86:   risk = '💀 CRITICAL RISK'
    elif score >= 61: risk = '🔴 HIGH RISK'
    elif score >= 31: risk = '🟡 MEDIUM RISK'
    else:             risk = '✅ LOW RISK'

    processes = summary.get('processes', []) or ['None']
    domains   = summary.get('domains',   []) or ['None']
    windows   = summary.get('windows',   []) or ['None']

    timeline = ''
    for e in events:
        desc = str(e.get('data', ''))[:35]
        timeline += f"\n║  {e.get('ts','??:??:??')}  {e.get('event','?'):<20} {desc:<35}║"

    print(f"""
╔══════════════════════════════════════════════════════╗
║              TRUTHLENS SESSION REPORT                ║
╠══════════════════════════════════════════════════════╣
║  Session:    {sid:<42}║
║  Duration:   {minutes}m {seconds}s{' '*39}║
║  Risk Score: {score}/100  {risk:<35}║
╠══════════════════════════════════════════════════════╣
║  THREATS DETECTED                                    ║
║  Processes:  {str(processes)[:45]:<45}║
║  AI Domains: {str(domains)[:45]:<45}║
║  AI Windows: {str(windows)[:45]:<45}║
║  Pastes:     {str(summary.get('paste_count',0)):<45}║
║  Causality:  {str(summary.get('causality_count',0)):<45}║
╠══════════════════════════════════════════════════════╣
║  INTEGRITY                                           ║
║  Tamper:     {str(integrity.get('tamper_detected','No')):<45}║
╠══════════════════════════════════════════════════════╣
║  TIMELINE{' '*45}║{timeline}
╠══════════════════════════════════════════════════════╣
║  Generated:  {time.strftime('%Y-%m-%d %H:%M:%S'):<42}║
╚══════════════════════════════════════════════════════╝
""")


# ══════════════════════════════════════════════════════════════════════════════
# WATCHDOG
# ══════════════════════════════════════════════════════════════════════════════
def heartbeat_watchdog():
    while True:
        try:
            time.sleep(10)
            now = time.time()
            for sid, sess in list(active_sessions.items()):
                if now - sess['last_seen'] > 65.0 and not sess.get('terminate'):
                    logger.warning(f"❌ AGENT SILENT > 60s (session {sid[:8]})")
                    sess['last_seen'] = now
        except:
            pass

threading.Thread(target=heartbeat_watchdog, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# GRACEFUL SHUTDOWN — Ctrl+C waits for reports
# ══════════════════════════════════════════════════════════════════════════════
def graceful_shutdown():
    global SHUTTING_DOWN
    SHUTTING_DOWN = True

    print("\n[SHUTDOWN] Sending terminate to all agents...")
    for sid in list(active_sessions.keys()):
        active_sessions[sid]['terminate'] = True

    active_count = len(active_sessions)
    if active_count == 0:
        print("[SHUTDOWN] No active sessions.")
        os._exit(0)

    print(f"[SHUTDOWN] Waiting 15s for {active_count} reports...")
    deadline = time.time() + 15
    while time.time() < deadline:
        received = len(REPORTS_RECEIVED)
        if received >= active_count:
            break
        print(f"[SHUTDOWN] Reports: {received}/{active_count}...")
        time.sleep(1)

    for sid, report in REPORTS_RECEIVED.items():
        print_report(report)

    if not REPORTS_RECEIVED:
        print("[SHUTDOWN] No reports received — agents may not have responded")

    print("[SHUTDOWN] Done. Goodbye.")
    os._exit(0)


# ══════════════════════════════════════════════════════════════════════════════
# RUN UVICORN IN THREAD — so Ctrl+C goes to OUR handler not uvicorn
# ══════════════════════════════════════════════════════════════════════════════
_uvicorn_server = None

def run_uvicorn():
    global _uvicorn_server
    config = uvicorn.Config(
        app,
        host='0.0.0.0',
        port=8000,
        log_level='info'
    )
    _uvicorn_server = uvicorn.Server(config)
    _uvicorn_server.run()

uvicorn_thread = threading.Thread(target=run_uvicorn, daemon=True)
uvicorn_thread.start()

# Wait for uvicorn to actually start
time.sleep(2)

# Main thread handles Ctrl+C
try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    graceful_shutdown()
