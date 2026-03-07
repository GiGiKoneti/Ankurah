import subprocess
import sys
import os

def bootstrap():
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    packages = ['fastapi', 'uvicorn[standard]', 'requests', 'psutil']
    for pkg in packages:
        subprocess.run([sys.executable, '-m', 'pip', 'install', pkg, '--quiet', '--disable-pip-version-check'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

bootstrap()

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
import time, socket, threading
import signal as signal_module

def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

LOCAL_IP = get_local_ip()

print(f"""
╔══════════════════════════════════════════════════╗
║        TRUTHLENS SERVER READY                    ║
╠══════════════════════════════════════════════════╣
║  Local IP:   {LOCAL_IP:<36}║
║  Port:       8000                                ║
║  Health:     http://{LOCAL_IP}:8000/health{" "*(23-len(LOCAL_IP))}║
╠══════════════════════════════════════════════════╣
║  ✅ Packages installed                           ║
╠══════════════════════════════════════════════════╣
║  SEND agent_ready.py TO FRIEND                   ║
║  Command: python agent_ready.py                  ║
╠══════════════════════════════════════════════════╣
║  Waiting for connections...                      ║
╚══════════════════════════════════════════════════╝
""")

app = FastAPI(title='TruthLens Server', docs_url=None, redoc_url=None)
active_sessions = {}
SHUTTING_DOWN = False
REPORTS_RECEIVED = {}

class Colors:
    RED_BOLD = '\033[1;31m'
    RED = '\033[0;31m'
    YELLOW = '\033[0;33m'
    CYAN = '\033[0;36m'
    RESET = '\033[0m'

@app.get('/health')
def get_health():
    return {'status': 'ok', 'ts': time.time()}

@app.post("/register")
async def register_agent(request: Request):
    try:
        data = await request.json()
        session_id = data.get('session_id')
        agent_hash = data.get('agent_hash', '')
        
        active_sessions[session_id] = {
            'connected_at': time.time(),
            'last_seen': time.time(),
            'agent_hash': agent_hash,
            'terminate': False,
            'events': []
        }
        print(f"[{time.strftime('%H:%M:%S')}] ✅ Agent connected — {session_id[:8]}")
        return {"status": "ok", "authorized": True}
    except Exception as e:
        print(f"Failed to register agent: {e}")
        return {"status": "error", "detail": str(e)}

@app.post("/event")
async def receive_event(request: Request):
    try:
        data = await request.json()
        event_type = data.get('event', 'UNKNOWN')
        ts = time.strftime('%H:%M:%S')
        
        desc = ""
        if 'data' in data and isinstance(data['data'], dict):
            d = data['data']
            if event_type == 'THREAT_PROCESS': desc = f"{d.get('name', '')} detected"
            elif event_type == 'AI_DOMAIN': desc = f"{d.get('domain', '')} ({d.get('hostname','')})"
            elif event_type == 'AI_PORT': desc = f"port {d.get('port', '')} ({d.get('service', '')})"
            elif event_type == 'LARGE_PASTE': desc = f"{d.get('chars', 0)} chars"
            elif event_type == 'AI_WINDOW': desc = f"'{d.get('title', '')}' ({d.get('keyword', '')})"
            else: desc = str(d)
        else:
            desc = data.get('description', str(data.get('data', '')))

        color = Colors.RESET
        prefix = ""
        if event_type == 'THREAT_PROCESS':
            color = Colors.RED_BOLD
            prefix = "CRITICAL: "
        elif event_type == 'AI_WINDOW':
            color = Colors.RED
            prefix = "HIGH: "
        elif event_type == 'AI_DOMAIN':
            color = Colors.RED
            prefix = "HIGH: "
        elif event_type == 'AI_PORT':
            color = Colors.YELLOW
            prefix = "MEDIUM: "
        elif event_type == 'LARGE_PASTE':
            color = Colors.CYAN
            prefix = "MEDIUM: "
        elif event_type == 'CAUSALITY':
            color = Colors.RED_BOLD
            prefix = "⚡ CAUSALITY: "
        elif event_type == 'HARDWARE':
            color = Colors.CYAN
            prefix = "🖥️ HARDWARE: "
            
        print(f"{color}[{ts}] {prefix}{event_type}: {desc}{Colors.RESET}")
        
        if data.get('session_id') in active_sessions:
            active_sessions[data.get('session_id')]['last_seen'] = time.time()
            
        return {"status": "ok"}
    except Exception as e:
        print(f"Failed to parse event: {e}")
        return {"status": "error", "detail": str(e)}

@app.post('/heartbeat')
async def post_heartbeat(request: Request):
    try:
        body = await request.json()
        sid = body.get('session_id', 'unknown')
        if sid in active_sessions:
            active_sessions[sid]['last_seen'] = time.time()
        return {'status': 'ok'}
    except Exception as e:
        return {"status": "error"}

@app.post("/terminate/{session_id}")
async def terminate_session(session_id: str):
    if session_id in active_sessions:
        active_sessions[session_id]['terminate'] = True
        return {"status": "ok"}
    return {"status": "not_found"}

@app.get("/should_terminate/{session_id}")  
async def should_terminate(session_id: str):
    if session_id in active_sessions:
        return {"terminate": active_sessions[session_id].get('terminate', False)}
    return {"terminate": False}

def print_report(report):
    score = report.get('risk_score', 0)
    sid = report.get('session_id', 'unknown')[:8]
    summary = report.get('threat_summary', {})
    events = report.get('events', [])
    
    if score >= 86:   risk = '💀 CRITICAL RISK'
    elif score >= 61: risk = '🔴 HIGH RISK'
    elif score >= 31: risk = '🟡 MEDIUM RISK'
    else:             risk = '✅ LOW RISK'
    
    processes = summary.get('processes', []) or ['None']
    domains   = summary.get('domains', []) or ['None']
    windows   = summary.get('windows', []) or ['None']
    
    timeline = '\n'.join([f"║  {e.get('ts','')}  {e.get('type',''):<20} {str(e.get('data',''))[:35]:<35}║" for e in events])
    
    print(f"""
╔══════════════════════════════════════════════════════╗
║              TRUTHLENS SESSION REPORT                ║
╠══════════════════════════════════════════════════════╣
║  Session:    {sid:<42}║
║  Risk Score: {score}/100  {risk:<35}║
╠══════════════════════════════════════════════════════╣
║  THREATS DETECTED                                    ║
║  Processes:  {str(processes)[:45]:<45}║
║  AI Domains: {str(domains)[:45]:<45}║
║  AI Windows: {str(windows)[:45]:<45}║
║  Pastes:     {summary.get('paste_count',0):<45}║
╠══════════════════════════════════════════════════════╣
║  TIMELINE{' '*45}║
{timeline}
╚══════════════════════════════════════════════════════╝
""")

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

def graceful_shutdown(sig, frame):
    global SHUTTING_DOWN
    print("\n[SHUTDOWN] Terminating all agents...")
    SHUTTING_DOWN = True
    for sid in list(active_sessions.keys()):
        active_sessions[sid]['terminate'] = True
    active_count = len(active_sessions)
    print(f"[SHUTDOWN] Waiting for {active_count} reports (max 15s)...")
    
    deadline = time.time() + 15
    while time.time() < deadline:
        if len(REPORTS_RECEIVED) >= active_count and active_count > 0:
            break
        time.sleep(1)
        
    for sid, report in REPORTS_RECEIVED.items():
        print_report(report)
    print("[SHUTDOWN] Done. Goodbye.")
    os._exit(0)

signal_module.signal(signal_module.SIGINT, graceful_shutdown)
signal_module.signal(signal_module.SIGTERM, graceful_shutdown)

def heartbeat_watchdog():
    while True:
        try:
            time.sleep(10)
            now = time.time()
            for sid, sess in list(active_sessions.items()):
                if now - sess['last_seen'] > 65.0 and not sess.get('terminate'):
                    print(f"❌ AGENT SILENT > 60s (session {sid[:8]})")
                    sess['last_seen'] = now
        except Exception: pass

threading.Thread(target=heartbeat_watchdog, daemon=True).start()

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000, log_level='warning')
